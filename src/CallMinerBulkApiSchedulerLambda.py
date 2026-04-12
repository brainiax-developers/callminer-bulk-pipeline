import copy
import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None

LOGGER = logging.getLogger(__name__)

ALLOWED_MODES = {"sync", "rerun"}
ALLOWED_RERUN_KEYS = {"duration", "name_suffix", "idempotency_key"}
ALLOWED_DURATION_OVERRIDE_KEYS = {
    "LastNDays",
    "LastNHours",
    "TimeFrame",
    "StartDate",
    "EndDate",
}
ALL_DURATION_KEYS = {
    "SearchMode",
    "LastNDays",
    "LastNHours",
    "TimeFrame",
    "StartDate",
    "EndDate",
}


class ValidationError(ValueError):
    pass


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class DuplicateJobMatchError(RuntimeError):
    pass


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
        payload["Schedule"] = None
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


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if event is None:
        event = {}

    if not isinstance(event, dict):
        raise ValidationError("Event must be a JSON object.")

    mode = (event.get("mode") or "sync").strip().lower() if isinstance(event.get("mode"), str) else "sync"
    if mode not in ALLOWED_MODES:
        raise ValidationError(f"Unsupported mode '{mode}'. Allowed: {sorted(ALLOWED_MODES)}")

    request_id = event.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ValidationError("request_id must be a string when provided.")

    if mode == "sync":
        if "rerun" in event:
            raise ValidationError("'rerun' payload is not allowed in sync mode.")

        dry_run = event.get("dry_run", False)
        if not isinstance(dry_run, bool):
            raise ValidationError("dry_run must be a boolean.")

        return {
            "mode": "sync",
            "request_id": request_id,
            "dry_run": dry_run,
        }

    rerun = event.get("rerun")
    if not isinstance(rerun, dict):
        raise ValidationError("rerun mode requires a 'rerun' JSON object.")

    unexpected_rerun_keys = sorted(set(rerun.keys()) - ALLOWED_RERUN_KEYS)
    if unexpected_rerun_keys:
        raise ValidationError(f"Unexpected rerun keys: {unexpected_rerun_keys}")

    duration = rerun.get("duration")
    if not isinstance(duration, dict):
        raise ValidationError("rerun.duration must be a JSON object.")

    unexpected_duration_keys = sorted(set(duration.keys()) - ALLOWED_DURATION_OVERRIDE_KEYS)
    if unexpected_duration_keys:
        raise ValidationError(f"Unexpected duration keys: {unexpected_duration_keys}")

    if not duration:
        raise ValidationError("rerun.duration must include at least one allowed field.")

    validate_duration_payload(duration)

    for optional_key in ("name_suffix", "idempotency_key"):
        if optional_key in rerun and rerun[optional_key] is not None and not isinstance(rerun[optional_key], str):
            raise ValidationError(f"rerun.{optional_key} must be a string when provided.")

    return {
        "mode": "rerun",
        "request_id": request_id,
        "rerun": {
            "duration": duration,
            "name_suffix": rerun.get("name_suffix"),
            "idempotency_key": rerun.get("idempotency_key"),
        },
    }


def validate_duration_payload(duration: Dict[str, Any]) -> None:
    has_start = duration.get("StartDate") not in (None, "")
    has_end = duration.get("EndDate") not in (None, "")
    has_days = duration.get("LastNDays") not in (None, "")
    has_hours = duration.get("LastNHours") not in (None, "")
    has_timeframe = duration.get("TimeFrame") not in (None, "")

    if has_start != has_end:
        raise ValidationError("StartDate and EndDate must be provided together.")

    explicit_strategies = [
        has_timeframe,
        has_start and has_end,
        has_days,
        has_hours,
    ]
    if sum(1 for strategy in explicit_strategies if strategy) > 1:
        raise ValidationError(
            "Duration override must use exactly one strategy: TimeFrame, StartDate/EndDate, LastNDays, or LastNHours."
        )

    if not any([has_start and has_end, has_days, has_hours, has_timeframe]):
        raise ValidationError(
            "Duration must include either StartDate+EndDate, LastNDays, LastNHours, or TimeFrame."
        )


def merge_duration(template_duration: Dict[str, Any], duration_override: Dict[str, Any]) -> Dict[str, Any]:
    merged = {key: None for key in ALL_DURATION_KEYS}

    if isinstance(template_duration, dict):
        for key in ALL_DURATION_KEYS:
            if key in template_duration:
                merged[key] = template_duration[key]

    for key, value in duration_override.items():
        merged[key] = value

    has_start = duration_override.get("StartDate") not in (None, "")
    has_end = duration_override.get("EndDate") not in (None, "")
    has_timeframe = duration_override.get("TimeFrame") not in (None, "")
    has_days = duration_override.get("LastNDays") not in (None, "")
    has_hours = duration_override.get("LastNHours") not in (None, "")

    if has_start or has_end:
        merged["LastNDays"] = None
        merged["LastNHours"] = None
        merged["TimeFrame"] = None
    elif has_timeframe:
        merged["StartDate"] = None
        merged["EndDate"] = None
        merged["LastNDays"] = None
        merged["LastNHours"] = None
    elif has_hours:
        merged["LastNDays"] = None
        merged["TimeFrame"] = None
        merged["StartDate"] = None
        merged["EndDate"] = None
    elif has_days:
        merged["LastNHours"] = None
        merged["TimeFrame"] = None
        merged["StartDate"] = None
        merged["EndDate"] = None

    return merged


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


def build_rerun_job_name(
    base_job_name: str,
    duration: Dict[str, Any],
    idempotency_key: Optional[str],
    request_id: Optional[str],
    name_suffix: Optional[str],
) -> str:
    period_token = build_period_token(duration)
    suffix = sanitize_token(name_suffix, max_length=24)
    if suffix:
        period_token = f"{period_token}_{suffix}"

    request_token = select_request_token(duration, idempotency_key, request_id)
    return f"{base_job_name}__rerun__{period_token}__{request_token}"


def build_period_token(duration: Dict[str, Any]) -> str:
    start = duration.get("StartDate")
    end = duration.get("EndDate")
    if start not in (None, "") and end not in (None, ""):
        return f"from_{format_datetime_token(str(start))}_to_{format_datetime_token(str(end))}"

    if duration.get("LastNHours") not in (None, ""):
        return f"last_{duration.get('LastNHours')}h"

    if duration.get("LastNDays") not in (None, ""):
        return f"last_{duration.get('LastNDays')}d"

    if duration.get("TimeFrame") not in (None, ""):
        return f"timeframe_{sanitize_token(str(duration.get('TimeFrame')), max_length=24)}"

    digest = hashlib.sha256(
        json.dumps(duration, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:10]
    return f"duration_{digest}"


def select_request_token(duration: Dict[str, Any], idempotency_key: Optional[str], request_id: Optional[str]) -> str:
    for value in (idempotency_key, request_id):
        token = sanitize_token(value, max_length=32)
        if token:
            return token

    digest = hashlib.sha256(
        json.dumps(duration, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return digest[:10]


def sanitize_token(value: Optional[str], max_length: int = 32) -> str:
    if not value:
        return ""

    token = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    token = token.strip("-")
    if not token:
        return ""

    return token[:max_length]


def format_datetime_token(value: str) -> str:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
        return parsed.strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        sanitized = re.sub(r"[^0-9TZ]", "", value)
        return sanitized[:16] or "invaliddt"


def is_likely_duplicate_error(error: ApiError) -> bool:
    if error.status_code in {409, 422}:
        return True

    if error.response_body:
        lower_body = error.response_body.lower()
        if "already exists" in lower_body or "duplicate" in lower_body:
            return True

    return False


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
