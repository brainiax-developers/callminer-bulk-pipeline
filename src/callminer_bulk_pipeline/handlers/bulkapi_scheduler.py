import copy
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

from callminer_bulk_pipeline.handlers.bulkapi_common import ApiError, DuplicateJobMatchError, ValidationError
from callminer_bulk_pipeline.handlers.bulkapi_reruns import (
    ALLOWED_DURATION_KEYS,
    ALLOWED_MODES,
    ALLOWED_RERUN_KEYS,
    build_period_token,
    build_rerun_job_name,
    format_iso8601_utc,
    is_likely_duplicate_error,
    merge_duration,
    normalize_duration_override,
    normalize_event,
    parse_iso8601_datetime_utc,
    sanitize_token,
    select_request_token,
    validate_duration_payload,
)

LOGGER = logging.getLogger(__name__)

ALLOWED_NOTIFICATION_METHODS = {"Email", "Webhook"}
EMAIL_RECIPIENT_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_template_notification_settings(template_payload: Dict[str, Any]) -> None:
    method = template_payload.get("NotificationMethod")
    if method not in ALLOWED_NOTIFICATION_METHODS:
        raise ValidationError(
            "BULK_JOB_TEMPLATE_JSON.NotificationMethod must be one of "
            f"{sorted(ALLOWED_NOTIFICATION_METHODS)}."
        )

    if method == "Email":
        email_recipients = template_payload.get("EmailRecipients")
        if not isinstance(email_recipients, list) or not email_recipients:
            raise ValidationError(
                "BULK_JOB_TEMPLATE_JSON.EmailRecipients must contain at least one recipient when "
                "NotificationMethod is 'Email'."
            )

        for recipient in email_recipients:
            if not isinstance(recipient, str) or not EMAIL_RECIPIENT_PATTERN.match(recipient.strip()):
                raise ValidationError(
                    "BULK_JOB_TEMPLATE_JSON.EmailRecipients must only contain valid email addresses "
                    "when NotificationMethod is 'Email'."
                )

        webhook_id = template_payload.get("WebhookId")
        if webhook_id not in (None, ""):
            raise ValidationError(
                "BULK_JOB_TEMPLATE_JSON.WebhookId must be null/empty when NotificationMethod is 'Email'."
            )
        return

    webhook_id = template_payload.get("WebhookId")
    if not isinstance(webhook_id, str) or not webhook_id.strip():
        raise ValidationError(
            "BULK_JOB_TEMPLATE_JSON.WebhookId must be set when NotificationMethod is 'Webhook'."
        )

    email_recipients = template_payload.get("EmailRecipients")
    if email_recipients not in (None, []):
        raise ValidationError(
            "BULK_JOB_TEMPLATE_JSON.EmailRecipients must be empty/null when NotificationMethod is 'Webhook'."
        )


@dataclass(frozen=True)
class SchedulerConfig:
    bulk_api_base_url: str
    idp_base_url: str
    scope: str
    auth_secret_name: str
    job_name: str
    previous_job_name: Optional[str]
    template_payload: Dict[str, Any]

    @staticmethod
    def from_env(env: Dict[str, str]) -> "SchedulerConfig":
        raw_template = env.get("BULK_JOB_TEMPLATE_JSON", "").strip()
        if not raw_template:
            raise ValidationError("BULK_JOB_TEMPLATE_JSON must be set.")

        try:
            template_payload = json.loads(raw_template)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"BULK_JOB_TEMPLATE_JSON is invalid JSON: {exc}") from exc

        if not isinstance(template_payload, dict):
            raise ValidationError("BULK_JOB_TEMPLATE_JSON must be a JSON object.")
        if not isinstance(template_payload.get("Duration"), dict):
            raise ValidationError("BULK_JOB_TEMPLATE_JSON must include a JSON object at key 'Duration'.")
        validate_template_notification_settings(template_payload)

        job_name = env.get("BULK_JOB_NAME", "").strip()
        if not job_name:
            raise ValidationError("BULK_JOB_NAME must be set.")

        auth_secret_name = env.get("CALLMINER_AUTH_SECRET_NAME", "").strip()
        if not auth_secret_name:
            raise ValidationError("CALLMINER_AUTH_SECRET_NAME must be set.")

        bulk_api_base_url = env.get("CALLMINER_BULK_API_BASE_URL", "https://apiuk.callminer.net/bulkexport").strip()
        idp_base_url = env.get("CALLMINER_IDP_BASE_URL", "https://idpuk.callminer.net").strip()
        scope = env.get("CALLMINER_BULK_SCOPE", "https://callminer.net/auth/platform-bulkexport").strip()
        previous_job_name = env.get("BULK_JOB_PREVIOUS_NAME", "").strip() or None

        return SchedulerConfig(
            bulk_api_base_url=bulk_api_base_url,
            idp_base_url=idp_base_url,
            scope=scope,
            auth_secret_name=auth_secret_name,
            job_name=job_name,
            previous_job_name=previous_job_name,
            template_payload=template_payload,
        )


class SecretsManagerReader:
    def __init__(self, client: Any = None):
        if client is not None:
            self._client = client
            return

        if boto3 is None:
            raise RuntimeError("boto3 is required to read secrets in runtime.")

        self._client = boto3.client("secretsmanager")

    def read_json(self, secret_name: str) -> Dict[str, Any]:
        response = self._client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString")

        if not secret_string:
            raise ValidationError(f"Secret '{secret_name}' has no SecretString.")

        try:
            payload = json.loads(secret_string)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Secret '{secret_name}' must contain valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValidationError(f"Secret '{secret_name}' must contain a JSON object.")
        return payload


class UrlLibSender:
    def send(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, str]:
        request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.getcode(), response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            return exc.code, error_body


class CallMinerBulkApiClient:
    def __init__(
        self,
        config: SchedulerConfig,
        secrets_reader: SecretsManagerReader,
        sender: Optional[UrlLibSender] = None,
    ):
        self._config = config
        self._secrets_reader = secrets_reader
        self._sender = sender or UrlLibSender()

    def get_access_token(self) -> str:
        credentials = self._secrets_reader.read_json(self._config.auth_secret_name)

        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        if not client_id or not client_secret:
            raise ValidationError("Secret must contain 'client_id' and 'client_secret'.")

        payload = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": self._config.scope,
            }
        ).encode("utf-8")

        token_url = f"{self._config.idp_base_url.rstrip('/')}/connect/token"
        status_code, response_body = self._sender.send(
            "POST",
            token_url,
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            payload,
        )

        if status_code != 200:
            raise ApiError("CallMiner token request failed.", status_code=status_code, response_body=response_body)

        try:
            token_payload = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ApiError("CallMiner token response is not valid JSON.") from exc

        access_token = token_payload.get("access_token")
        if not access_token:
            raise ApiError("CallMiner token response did not include 'access_token'.")

        return access_token

    def list_jobs(self, access_token: str) -> List[Dict[str, Any]]:
        status_code, response_body = self._request("GET", "/api/export/job", access_token, payload=None)
        if status_code != 200:
            raise ApiError("Failed to list CallMiner export jobs.", status_code=status_code, response_body=response_body)

        payload = self._load_json_response(response_body)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("Items", "items", "Results", "results", "Jobs", "jobs", "Data", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value

        raise ApiError("Unsupported response shape for GET /api/export/job.")

    def create_job(self, access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        status_code, response_body = self._request("POST", "/api/export/job", access_token, payload=payload)
        if status_code not in (200, 201):
            raise ApiError("Failed to create CallMiner export job.", status_code=status_code, response_body=response_body)

        if not response_body.strip():
            return {}

        parsed = self._load_json_response(response_body)
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def update_job(self, access_token: str, job_id: str, payload: Dict[str, Any]) -> None:
        path = f"/api/export/job/{job_id}"
        status_code, response_body = self._request("PUT", path, access_token, payload=payload)
        if status_code not in (200, 204):
            raise ApiError("Failed to update CallMiner export job.", status_code=status_code, response_body=response_body)

    def _request(
        self,
        method: str,
        path: str,
        access_token: str,
        payload: Optional[Dict[str, Any]],
    ) -> Tuple[int, str]:
        url = f"{self._config.bulk_api_base_url.rstrip('/')}{path}"
        body: Optional[bytes] = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        return self._sender.send(
            method,
            url,
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body,
        )

    @staticmethod
    def _load_json_response(response_body: str) -> Any:
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ApiError("API response is not valid JSON.") from exc


class CallMinerBulkScheduler:
    def __init__(self, config: SchedulerConfig, api_client: CallMinerBulkApiClient):
        self._config = config
        self._api_client = api_client

    def handle(self, event: Dict[str, Any]) -> Dict[str, Any]:
        normalized = normalize_event(event)
        access_token = self._api_client.get_access_token()

        if normalized["mode"] == "sync":
            return self._handle_sync(access_token, normalized)

        return self._handle_rerun(access_token, normalized)

    def _handle_sync(self, access_token: str, normalized_event: Dict[str, Any]) -> Dict[str, Any]:
        jobs = self._api_client.list_jobs(access_token)
        matching_job = find_job_by_names(jobs, [self._config.job_name, self._config.previous_job_name])

        payload = copy.deepcopy(self._config.template_payload)
        payload["Name"] = self._config.job_name

        dry_run = normalized_event["dry_run"]
        if matching_job:
            job_id = extract_job_id(matching_job)
            if dry_run:
                return {
                    "mode": "sync",
                    "action": "would_update",
                    "job_id": job_id,
                    "job_name": self._config.job_name,
                    "dry_run": True,
                }

            self._api_client.update_job(access_token, job_id, payload)
            return {
                "mode": "sync",
                "action": "updated",
                "job_id": job_id,
                "job_name": self._config.job_name,
                "dry_run": False,
            }

        if dry_run:
            return {
                "mode": "sync",
                "action": "would_create",
                "job_name": self._config.job_name,
                "dry_run": True,
            }

        create_response = self._api_client.create_job(access_token, payload)
        return {
            "mode": "sync",
            "action": "created",
            "job_id": extract_job_id(create_response),
            "job_name": self._config.job_name,
            "dry_run": False,
        }

    def _handle_rerun(self, access_token: str, normalized_event: Dict[str, Any]) -> Dict[str, Any]:
        rerun_payload = normalized_event["rerun"]
        duration_override = rerun_payload["duration"]

        rerun_name = build_rerun_job_name(
            base_job_name=self._config.job_name,
            duration=duration_override,
            idempotency_key=rerun_payload.get("idempotency_key"),
            request_id=normalized_event.get("request_id"),
            name_suffix=rerun_payload.get("name_suffix"),
        )

        jobs = self._api_client.list_jobs(access_token)
        existing = find_job_by_names(jobs, [rerun_name])
        if existing:
            return {
                "mode": "rerun",
                "action": "already_exists",
                "job_name": rerun_name,
                "job_id": extract_job_id(existing),
                "idempotent": True,
            }

        payload = copy.deepcopy(self._config.template_payload)
        payload["Name"] = rerun_name
        payload.pop("Schedule", None)
        payload["Duration"] = merge_duration(payload.get("Duration", {}), duration_override)

        try:
            create_response = self._api_client.create_job(access_token, payload)
            return {
                "mode": "rerun",
                "action": "created",
                "job_name": rerun_name,
                "job_id": extract_job_id(create_response),
                "idempotent": False,
            }
        except ApiError as exc:
            if is_likely_duplicate_error(exc):
                jobs_after_conflict = self._api_client.list_jobs(access_token)
                existing_after_conflict = find_job_by_names(jobs_after_conflict, [rerun_name])
                if existing_after_conflict:
                    return {
                        "mode": "rerun",
                        "action": "already_exists",
                        "job_name": rerun_name,
                        "job_id": extract_job_id(existing_after_conflict),
                        "idempotent": True,
                    }
            raise


def find_job_by_names(jobs: List[Dict[str, Any]], names: List[Optional[str]]) -> Optional[Dict[str, Any]]:
    candidate_names = [name for name in names if isinstance(name, str) and name.strip()]
    if not candidate_names:
        return None

    for candidate_name in candidate_names:
        matched_jobs = [job for job in jobs if str(job.get("Name", "")).strip() == candidate_name]
        if len(matched_jobs) > 1:
            raise DuplicateJobMatchError(
                f"Multiple CallMiner export jobs found for configured name '{candidate_name}'."
            )
        if len(matched_jobs) == 1:
            return matched_jobs[0]

    return None


def extract_job_id(job_payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(job_payload, dict):
        return None

    for key in ("Id", "ID", "id", "JobId", "jobId"):
        value = job_payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    configure_logging()

    config = SchedulerConfig.from_env(os.environ)
    api_client = CallMinerBulkApiClient(config=config, secrets_reader=SecretsManagerReader())
    scheduler = CallMinerBulkScheduler(config=config, api_client=api_client)

    LOGGER.info("CallMiner bulk scheduler invocation started")
    result = scheduler.handle(event or {})
    LOGGER.info("CallMiner bulk scheduler invocation completed with action=%s", result.get("action"))

    return {
        "status": "ok",
        **result,
    }
