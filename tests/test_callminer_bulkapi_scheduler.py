import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.CallMinerBulkApiSchedulerLambda import (
    ApiError,
    CallMinerBulkApiClient,
    CallMinerBulkScheduler,
    DuplicateJobMatchError,
    SchedulerConfig,
    ValidationError,
    build_rerun_job_name,
    lambda_handler,
    merge_duration,
    normalize_event,
)


class FakeSecretsReader:
    def __init__(self, payload):
        self.payload = payload

    def read_json(self, secret_name):
        return self.payload


class FakeSender:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def send(self, method, url, headers, body):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
            }
        )
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


class FakeApiClient:
    def __init__(self, jobs=None, create_response=None, create_error=None):
        self.jobs = jobs or []
        self.create_response = create_response or {}
        self.create_error = create_error
        self.updated = []
        self.created = []

    def get_access_token(self):
        return "fake-token"

    def list_jobs(self, access_token):
        return list(self.jobs)

    def create_job(self, access_token, payload):
        self.created.append(payload)
        if self.create_error:
            raise self.create_error
        return self.create_response

    def update_job(self, access_token, job_id, payload):
        self.updated.append((job_id, payload))


class EventContractTests(unittest.TestCase):
    def test_sync_mode_defaults(self):
        normalized = normalize_event({})
        self.assertEqual(normalized["mode"], "sync")
        self.assertFalse(normalized["dry_run"])

    def test_rerun_rejects_extra_duration_fields(self):
        with self.assertRaises(ValidationError):
            normalize_event(
                {
                    "mode": "rerun",
                    "rerun": {
                        "duration": {
                            "StartDate": "2026-03-01T00:00:00Z",
                            "EndDate": "2026-03-01T01:00:00Z",
                            "StorageTargetName": "forbidden",
                        }
                    },
                }
            )

    def test_rerun_rejects_multiple_duration_strategies(self):
        with self.assertRaises(ValidationError):
            normalize_event(
                {
                    "mode": "rerun",
                    "rerun": {
                        "duration": {
                            "TimeFrame": "LastDay",
                            "LastNDays": 1,
                        }
                    },
                }
            )

    def test_rerun_rejects_search_mode_override(self):
        with self.assertRaises(ValidationError):
            normalize_event(
                {
                    "mode": "rerun",
                    "rerun": {
                        "duration": {
                            "SearchMode": "AgentTalkDate",
                            "LastNDays": 1,
                        }
                    },
                }
            )


class ConfigValidationTests(unittest.TestCase):
    def _base_env(self):
        return {
            "BULK_JOB_TEMPLATE_JSON": '{"Duration":{"SearchMode":"ClientCaptureDate","LastNDays":1}}',
            "BULK_JOB_NAME": "MyScheduledJob",
            "CALLMINER_AUTH_SECRET_NAME": "my-secret",
        }

    def test_config_rejects_missing_job_name(self):
        env = self._base_env()
        env["BULK_JOB_NAME"] = ""
        with self.assertRaises(ValidationError):
            SchedulerConfig.from_env(env)

    def test_config_rejects_template_without_duration(self):
        env = self._base_env()
        env["BULK_JOB_TEMPLATE_JSON"] = '{"Name":"BadTemplate"}'
        with self.assertRaises(ValidationError):
            SchedulerConfig.from_env(env)


class NamingTests(unittest.TestCase):
    def test_rerun_name_uses_idempotency_key_over_request_id(self):
        name = build_rerun_job_name(
            base_job_name="BaseJob",
            duration={"LastNHours": 24},
            idempotency_key="abc123",
            request_id="req999",
            name_suffix=None,
        )
        self.assertEqual(name, "BaseJob__rerun__last_24h__abc123")


class SchedulerFlowTests(unittest.TestCase):
    def _config(self):
        return SchedulerConfig(
            bulk_api_base_url="https://apiuk.callminer.net/bulkexport",
            idp_base_url="https://idpuk.callminer.net",
            scope="https://callminer.net/auth/platform-bulkexport",
            auth_secret_name="test-secret",
            job_name="ScheduledJob",
            previous_job_name="OldScheduledJob",
            template_payload={
                "Duration": {
                    "SearchMode": "ClientCaptureDate",
                    "LastNDays": 1,
                    "LastNHours": None,
                    "TimeFrame": None,
                    "StartDate": None,
                    "EndDate": None,
                },
                "StorageTargetName": "StorageTarget",
                "Schedule": "0 30 8 ? * 4#1",
            },
        )

    def test_sync_updates_existing_previous_name_job(self):
        api = FakeApiClient(jobs=[{"Id": "44", "Name": "OldScheduledJob"}])
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        result = scheduler.handle({"mode": "sync"})

        self.assertEqual(result["action"], "updated")
        self.assertEqual(api.updated[0][0], "44")
        self.assertEqual(api.updated[0][1]["Name"], "ScheduledJob")

    def test_sync_fails_on_duplicate_matching_name(self):
        api = FakeApiClient(
            jobs=[
                {"Id": "44", "Name": "ScheduledJob"},
                {"Id": "45", "Name": "ScheduledJob"},
            ]
        )
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        with self.assertRaises(DuplicateJobMatchError):
            scheduler.handle({"mode": "sync"})

    def test_sync_creates_job_when_absent(self):
        api = FakeApiClient(jobs=[], create_response={"Id": "1001", "Name": "ScheduledJob"})
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        result = scheduler.handle({"mode": "sync"})

        self.assertEqual(result["action"], "created")
        self.assertEqual(result["job_id"], "1001")
        self.assertEqual(api.created[0]["Name"], "ScheduledJob")

    def test_rerun_is_idempotent_when_same_name_exists(self):
        existing_name = "ScheduledJob__rerun__last_24h__idem-1"
        api = FakeApiClient(jobs=[{"Id": "901", "Name": existing_name}])
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        result = scheduler.handle(
            {
                "mode": "rerun",
                "request_id": "request-abc",
                "rerun": {
                    "idempotency_key": "idem-1",
                    "duration": {"LastNHours": 24},
                },
            }
        )

        self.assertEqual(result["action"], "already_exists")
        self.assertTrue(result["idempotent"])
        self.assertEqual(result["job_id"], "901")

    def test_rerun_handles_duplicate_error_by_requerying(self):
        duplicate_error = ApiError("duplicate", status_code=409, response_body="already exists")
        expected_name = "ScheduledJob__rerun__last_24h__idem-2"
        api = FakeApiClient(
            jobs=[],
            create_error=duplicate_error,
        )

        def list_jobs(access_token):
            if not api.created:
                return []
            return [{"Id": "502", "Name": expected_name}]

        api.list_jobs = list_jobs  # noqa: PLW2901
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        result = scheduler.handle(
            {
                "mode": "rerun",
                "rerun": {
                    "idempotency_key": "idem-2",
                    "duration": {"LastNHours": 24},
                },
            }
        )

        self.assertEqual(result["action"], "already_exists")
        self.assertEqual(result["job_id"], "502")

    def test_rerun_forces_schedule_null_and_preserves_protected_fields(self):
        api = FakeApiClient(jobs=[], create_response={"Id": "777"})
        scheduler = CallMinerBulkScheduler(config=self._config(), api_client=api)

        result = scheduler.handle(
            {
                "mode": "rerun",
                "request_id": "run-1",
                "rerun": {
                    "duration": {
                        "StartDate": "2026-03-01T00:00:00Z",
                        "EndDate": "2026-03-01T23:59:59Z",
                    },
                },
            }
        )

        self.assertEqual(result["action"], "created")
        created_payload = api.created[0]
        self.assertIsNone(created_payload["Schedule"])
        self.assertEqual(created_payload["StorageTargetName"], "StorageTarget")
        self.assertEqual(
            created_payload["Duration"]["StartDate"],
            "2026-03-01T00:00:00Z",
        )
        self.assertEqual(
            created_payload["Duration"]["EndDate"],
            "2026-03-01T23:59:59Z",
        )


class ApiClientTests(unittest.TestCase):
    def test_token_request_and_bearer_header(self):
        config = SchedulerConfig(
            bulk_api_base_url="https://apiuk.callminer.net/bulkexport",
            idp_base_url="https://idpuk.callminer.net",
            scope="https://callminer.net/auth/platform-bulkexport",
            auth_secret_name="bulk-secret",
            job_name="Job",
            previous_job_name=None,
            template_payload={"Duration": {}},
        )

        sender = FakeSender(
            responses=[
                (200, '{"access_token":"token-123"}'),
                (200, '[]'),
            ]
        )

        client = CallMinerBulkApiClient(
            config=config,
            secrets_reader=FakeSecretsReader({"client_id": "cid", "client_secret": "csecret"}),
            sender=sender,
        )

        token = client.get_access_token()
        client.list_jobs(token)

        token_call = sender.calls[0]
        jobs_call = sender.calls[1]

        self.assertEqual(token, "token-123")
        self.assertEqual(token_call["method"], "POST")
        self.assertEqual(token_call["url"], "https://idpuk.callminer.net/connect/token")
        self.assertIn("grant_type=client_credentials", token_call["body"].decode("utf-8"))
        self.assertEqual(jobs_call["headers"]["Authorization"], "Bearer token-123")

    def test_token_request_requires_access_token_field(self):
        config = SchedulerConfig(
            bulk_api_base_url="https://apiuk.callminer.net/bulkexport",
            idp_base_url="https://idpuk.callminer.net",
            scope="https://callminer.net/auth/platform-bulkexport",
            auth_secret_name="bulk-secret",
            job_name="Job",
            previous_job_name=None,
            template_payload={"Duration": {}},
        )
        sender = FakeSender(responses=[(200, '{"token_type":"Bearer"}')])
        client = CallMinerBulkApiClient(
            config=config,
            secrets_reader=FakeSecretsReader({"client_id": "cid", "client_secret": "csecret"}),
            sender=sender,
        )

        with self.assertRaises(ApiError):
            client.get_access_token()

    def test_list_jobs_supports_items_wrapper_shape(self):
        config = SchedulerConfig(
            bulk_api_base_url="https://apiuk.callminer.net/bulkexport",
            idp_base_url="https://idpuk.callminer.net",
            scope="https://callminer.net/auth/platform-bulkexport",
            auth_secret_name="bulk-secret",
            job_name="Job",
            previous_job_name=None,
            template_payload={"Duration": {}},
        )
        sender = FakeSender(responses=[(200, '{"Items":[{"Id":"1","Name":"Job"}]}')])
        client = CallMinerBulkApiClient(
            config=config,
            secrets_reader=FakeSecretsReader({"client_id": "cid", "client_secret": "csecret"}),
            sender=sender,
        )

        jobs = client.list_jobs("token-123")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["Name"], "Job")

    def test_list_jobs_rejects_unexpected_response_shape(self):
        config = SchedulerConfig(
            bulk_api_base_url="https://apiuk.callminer.net/bulkexport",
            idp_base_url="https://idpuk.callminer.net",
            scope="https://callminer.net/auth/platform-bulkexport",
            auth_secret_name="bulk-secret",
            job_name="Job",
            previous_job_name=None,
            template_payload={"Duration": {}},
        )
        sender = FakeSender(responses=[(200, '{"count":1}')])
        client = CallMinerBulkApiClient(
            config=config,
            secrets_reader=FakeSecretsReader({"client_id": "cid", "client_secret": "csecret"}),
            sender=sender,
        )

        with self.assertRaises(ApiError):
            client.list_jobs("token-123")


class DurationMergeTests(unittest.TestCase):
    def test_timeframe_override_clears_last_n_days(self):
        merged = merge_duration(
            template_duration={
                "SearchMode": "ClientCaptureDate",
                "LastNDays": 1,
                "LastNHours": None,
                "TimeFrame": None,
                "StartDate": None,
                "EndDate": None,
            },
            duration_override={"TimeFrame": "LastWeek"},
        )

        self.assertEqual(merged["TimeFrame"], "LastWeek")
        self.assertIsNone(merged["LastNDays"])
        self.assertIsNone(merged["LastNHours"])
        self.assertIsNone(merged["StartDate"])
        self.assertIsNone(merged["EndDate"])

    def test_start_end_override_clears_relative_windows(self):
        merged = merge_duration(
            template_duration={
                "SearchMode": "ClientCaptureDate",
                "LastNDays": 7,
                "LastNHours": None,
                "TimeFrame": None,
                "StartDate": None,
                "EndDate": None,
            },
            duration_override={
                "StartDate": "2026-03-01T00:00:00Z",
                "EndDate": "2026-03-01T23:59:59Z",
            },
        )

        self.assertEqual(merged["StartDate"], "2026-03-01T00:00:00Z")
        self.assertEqual(merged["EndDate"], "2026-03-01T23:59:59Z")
        self.assertIsNone(merged["LastNDays"])
        self.assertIsNone(merged["LastNHours"])
        self.assertIsNone(merged["TimeFrame"])

    def test_last_n_days_override_clears_timeframe_and_dates(self):
        merged = merge_duration(
            template_duration={
                "SearchMode": "ClientCaptureDate",
                "LastNDays": None,
                "LastNHours": None,
                "TimeFrame": "Yesterday",
                "StartDate": None,
                "EndDate": None,
            },
            duration_override={"LastNDays": 3},
        )

        self.assertEqual(merged["LastNDays"], 3)
        self.assertIsNone(merged["TimeFrame"])
        self.assertIsNone(merged["StartDate"])
        self.assertIsNone(merged["EndDate"])


class HandlerWiringTests(unittest.TestCase):
    def test_lambda_handler_returns_scheduler_result_with_ok_status(self):
        env = {
            "BULK_JOB_TEMPLATE_JSON": '{"Duration":{"SearchMode":"ClientCaptureDate","LastNDays":1}}',
            "BULK_JOB_NAME": "ScheduledJob",
            "CALLMINER_AUTH_SECRET_NAME": "bulk-secret",
        }

        with patch.dict(os.environ, env, clear=True):
            with patch("src.CallMinerBulkApiSchedulerLambda.SecretsManagerReader"):
                with patch("src.CallMinerBulkApiSchedulerLambda.CallMinerBulkApiClient"):
                    with patch("src.CallMinerBulkApiSchedulerLambda.CallMinerBulkScheduler") as scheduler_cls:
                        scheduler_instance = scheduler_cls.return_value
                        scheduler_instance.handle.return_value = {
                            "mode": "sync",
                            "action": "would_create",
                            "job_name": "ScheduledJob",
                            "dry_run": True,
                        }

                        result = lambda_handler({"mode": "sync", "dry_run": True}, None)

                        self.assertEqual(result["status"], "ok")
                        self.assertEqual(result["action"], "would_create")
                        self.assertTrue(result["dry_run"])
                        scheduler_instance.handle.assert_called_once_with({"mode": "sync", "dry_run": True})


if __name__ == "__main__":
    unittest.main()
