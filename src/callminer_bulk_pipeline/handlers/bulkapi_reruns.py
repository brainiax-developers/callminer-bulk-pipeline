import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from callminer_bulk_pipeline.handlers.bulkapi_common import ApiError, ValidationError

ALLOWED_MODES = {"sync", "rerun"}
ALLOWED_RERUN_KEYS = {"duration", "name_suffix", "idempotency_key"}
ALLOWED_DURATION_KEYS = {
    "SearchMode",
    "LastNDays",
    "LastNHours",
    "TimeFrame",
    "StartDate",
    "EndDate",
}


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

    unexpected_duration_keys = sorted(set(duration.keys()) - ALLOWED_DURATION_KEYS)
    if unexpected_duration_keys:
        raise ValidationError(f"Unexpected duration keys: {unexpected_duration_keys}")

    if not duration:
        raise ValidationError("rerun.duration must include at least one allowed field.")

    validate_duration_payload(duration)
    duration = normalize_duration_override(duration)

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
    timeframe_value = duration.get("TimeFrame")
    has_timeframe = timeframe_value not in (None, "")
    has_custom_timeframe = isinstance(timeframe_value, str) and timeframe_value.strip().lower() == "custom"
    has_explicit_dates = has_start and has_end

    if has_start != has_end:
        raise ValidationError("StartDate and EndDate must be provided together.")

    if has_custom_timeframe and not has_explicit_dates:
        raise ValidationError("TimeFrame='Custom' requires both StartDate and EndDate.")

    if has_explicit_dates and has_timeframe and not has_custom_timeframe:
        raise ValidationError("When StartDate and EndDate are set, TimeFrame must be omitted or set to 'Custom'.")

    explicit_strategies = [
        has_timeframe and not has_custom_timeframe,
        has_explicit_dates,
        has_days,
        has_hours,
    ]
    if sum(1 for strategy in explicit_strategies if strategy) > 1:
        raise ValidationError(
            "Duration override must use exactly one strategy: TimeFrame, StartDate/EndDate, LastNDays, or LastNHours."
        )

    if not any([has_explicit_dates, has_days, has_hours, has_timeframe]):
        raise ValidationError(
            "Duration must include either StartDate+EndDate, LastNDays, LastNHours, or TimeFrame."
        )

    if has_explicit_dates:
        start_datetime = parse_iso8601_datetime_utc(duration.get("StartDate"), field_name="StartDate")
        end_datetime = parse_iso8601_datetime_utc(duration.get("EndDate"), field_name="EndDate")
        if end_datetime <= start_datetime:
            raise ValidationError("EndDate must be greater than StartDate.")

        range_delta = end_datetime - start_datetime
        if range_delta % timedelta(days=1) != timedelta(0):
            raise ValidationError(
                "StartDate and EndDate custom ranges must use whole-day (24-hour) increments in UTC."
            )


def normalize_duration_override(duration_override: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(duration_override)
    has_start = normalized.get("StartDate") not in (None, "")
    has_end = normalized.get("EndDate") not in (None, "")

    if has_start and has_end:
        start_datetime = parse_iso8601_datetime_utc(normalized.get("StartDate"), field_name="StartDate")
        end_datetime = parse_iso8601_datetime_utc(normalized.get("EndDate"), field_name="EndDate")
        normalized["StartDate"] = format_iso8601_utc(start_datetime)
        normalized["EndDate"] = format_iso8601_utc(end_datetime)
        normalized["TimeFrame"] = "Custom"

    return normalized


def parse_iso8601_datetime_utc(raw_value: Any, field_name: str) -> datetime:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValidationError(f"{field_name} must be a non-empty ISO8601 datetime string.")

    normalized = raw_value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid ISO8601 datetime string.") from exc

    if parsed.tzinfo is None:
        raise ValidationError(f"{field_name} must include a UTC offset (for example, a trailing 'Z').")

    return parsed.astimezone(timezone.utc)


def format_iso8601_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def merge_duration(template_duration: Dict[str, Any], duration_override: Dict[str, Any]) -> Dict[str, Any]:
    merged = {key: None for key in ALLOWED_DURATION_KEYS}

    if isinstance(template_duration, dict):
        for key in ALLOWED_DURATION_KEYS:
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
        merged["TimeFrame"] = "Custom"
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
