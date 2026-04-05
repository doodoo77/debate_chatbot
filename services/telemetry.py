from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, Iterable, List, Optional

MODEL_PRICING_PER_1M = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.00},
    "text-embedding-3-large": {"input": 0.13, "output": 0.00},
}

_RESPONSE_USAGE_KEYS = ("token_usage", "usage", "usage_metadata")


def now() -> float:
    return time.perf_counter()


def elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _to_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def payload_to_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8", errors="ignore")
        except Exception:
            return str(payload)
    if isinstance(payload, dict):
        try:
            return json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(payload)
    if isinstance(payload, (list, tuple, set)):
        parts = []
        for item in payload:
            if hasattr(item, "content"):
                item_type = getattr(item, "type", item.__class__.__name__)
                parts.append(f"[{item_type}] {payload_to_text(getattr(item, 'content', ''))}")
            else:
                parts.append(payload_to_text(item))
        return "\n".join(part for part in parts if part)
    if hasattr(payload, "model_dump"):
        try:
            return json.dumps(payload.model_dump(), ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(payload)
    return str(payload)


def estimate_tokens(payload: Any) -> int:
    text = payload_to_text(payload)
    if not text:
        return 0
    char_len = len(text)
    byte_len = len(text.encode("utf-8"))
    word_len = len(text.split())
    estimate = max(char_len / 2.8, byte_len / 5.0, word_len * 1.3)
    return max(1, int(math.ceil(estimate)))


def _extract_response_metadata(payload: Any) -> Optional[Dict[str, Any]]:
    if payload is None:
        return None
    if isinstance(payload, dict):
        if any(key in payload for key in _RESPONSE_USAGE_KEYS):
            return payload
        raw = payload.get("raw")
        if raw is not None:
            return _extract_response_metadata(raw)
        nested = payload.get("response_metadata")
        if isinstance(nested, dict):
            return nested
        return None

    response_metadata = getattr(payload, "response_metadata", None)
    if isinstance(response_metadata, dict):
        return response_metadata
    return None


def _extract_usage_record(payload: Any) -> Optional[Dict[str, Any]]:
    metadata = _extract_response_metadata(payload)
    if not metadata:
        return None

    model_name = metadata.get("model_name") or metadata.get("model")

    token_usage = _safe_dict(metadata.get("token_usage"))
    if token_usage:
        completion_details = _safe_dict(token_usage.get("completion_tokens_details"))
        prompt_details = _safe_dict(token_usage.get("prompt_tokens_details"))
        prompt_tokens = _to_int(token_usage.get("prompt_tokens"))
        completion_tokens = _to_int(token_usage.get("completion_tokens"))
        total_tokens = _to_int(token_usage.get("total_tokens")) or (prompt_tokens + completion_tokens)
        return {
            "provider": "openai",
            "model_name": model_name,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached_input_tokens": _to_int(prompt_details.get("cached_tokens")),
            "reasoning_tokens": _to_int(completion_details.get("reasoning_tokens")),
        }

    usage = _safe_dict(metadata.get("usage"))
    if usage:
        input_tokens = _to_int(usage.get("input_tokens"))
        output_tokens = _to_int(usage.get("output_tokens"))
        return {
            "provider": "anthropic",
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": _to_int(usage.get("total_tokens")) or (input_tokens + output_tokens),
            "cached_input_tokens": _to_int(usage.get("cache_read_input_tokens")),
            "cache_creation_input_tokens": _to_int(usage.get("cache_creation_input_tokens")),
            "reasoning_tokens": 0,
        }

    usage_metadata = _safe_dict(metadata.get("usage_metadata"))
    if usage_metadata:
        prompt_tokens = _to_int(usage_metadata.get("prompt_token_count"))
        candidate_tokens = _to_int(usage_metadata.get("candidates_token_count"))
        return {
            "provider": "google",
            "model_name": model_name,
            "input_tokens": prompt_tokens,
            "output_tokens": candidate_tokens,
            "total_tokens": _to_int(usage_metadata.get("total_token_count")) or (prompt_tokens + candidate_tokens),
            "cached_input_tokens": _to_int(usage_metadata.get("cached_content_token_count")),
            "reasoning_tokens": 0,
        }

    return None


def aggregate_usage_records(response_metadata: Any) -> Optional[Dict[str, Any]]:
    if response_metadata is None:
        return None

    items: List[Any]
    if isinstance(response_metadata, (list, tuple)):
        items = list(response_metadata)
    else:
        items = [response_metadata]

    records = [record for record in (_extract_usage_record(item) for item in items) if record]
    if not records:
        return None

    first = records[0]
    aggregated = {
        "provider": first.get("provider", "unknown"),
        "model_name": first.get("model_name"),
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "reasoning_tokens": 0,
        "llm_call_count": len(records),
    }
    for record in records:
        aggregated["input_tokens"] += _to_int(record.get("input_tokens"))
        aggregated["output_tokens"] += _to_int(record.get("output_tokens"))
        aggregated["total_tokens"] += _to_int(record.get("total_tokens"))
        aggregated["cached_input_tokens"] += _to_int(record.get("cached_input_tokens"))
        aggregated["cache_creation_input_tokens"] += _to_int(record.get("cache_creation_input_tokens"))
        aggregated["reasoning_tokens"] += _to_int(record.get("reasoning_tokens"))
    return aggregated


def resolve_pricing(model_name: str | None) -> Dict[str, float] | None:
    if not model_name:
        return None
    exact = MODEL_PRICING_PER_1M.get(model_name)
    if exact is not None:
        return exact

    for base_name, pricing in sorted(MODEL_PRICING_PER_1M.items(), key=lambda item: len(item[0]), reverse=True):
        if model_name == base_name or model_name.startswith(f"{base_name}-") or model_name.startswith(base_name):
            return pricing
    return None


def estimate_cost_usd(model_name: str | None, input_tokens: int, output_tokens: int) -> float | None:
    pricing = resolve_pricing(model_name)
    if pricing is None:
        return None
    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0.0)
    return round(input_cost + output_cost, 8)


def build_metric(
    *,
    step: str,
    started_at: float,
    model_name: str | None = None,
    input_payload: Any = None,
    output_payload: Any = None,
    response_metadata: Any = None,
    status: str = "ok",
    notes: str = "",
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    usage = aggregate_usage_records(response_metadata)
    metric: Dict[str, Any] = {
        "step": step,
        "model_name": model_name or (usage.get("model_name") if usage else None) or "-",
        "duration_ms": elapsed_ms(started_at),
        "status": status,
    }

    if usage:
        resolved_model_name = metric["model_name"]
        cost_usd = estimate_cost_usd(resolved_model_name, usage["input_tokens"], usage["output_tokens"])
        metric.update(
            {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "cached_input_tokens": usage.get("cached_input_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                "reasoning_tokens": usage.get("reasoning_tokens", 0),
                "llm_call_count": usage.get("llm_call_count", 1),
                "provider": usage.get("provider", "unknown"),
                "cost_source": "response_metadata",
                "cost_usd": cost_usd,
                "estimated_input_tokens": usage["input_tokens"],
                "estimated_output_tokens": usage["output_tokens"],
                "estimated_cost_usd": cost_usd,
            }
        )
    else:
        input_tokens = estimate_tokens(input_payload)
        output_tokens = estimate_tokens(output_payload)
        cost_usd = estimate_cost_usd(metric["model_name"], input_tokens, output_tokens)
        metric.update(
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "llm_call_count": 1,
                "provider": "heuristic",
                "cost_source": "estimated_text_heuristic",
                "cost_usd": cost_usd,
                "estimated_input_tokens": input_tokens,
                "estimated_output_tokens": output_tokens,
                "estimated_cost_usd": cost_usd,
            }
        )

    if notes:
        metric["notes"] = notes
    if extra:
        metric.update(extra)
    return metric


def sum_metric_cost(metrics: Iterable[Dict[str, Any]]) -> float:
    total = 0.0
    for metric in metrics:
        value = metric.get("cost_usd")
        if value is None:
            value = metric.get("estimated_cost_usd")
        if isinstance(value, (int, float)):
            total += float(value)
    return round(total, 8)


def sum_metric_duration(metrics: Iterable[Dict[str, Any]]) -> int:
    total = 0
    for metric in metrics:
        value = metric.get("duration_ms")
        if isinstance(value, (int, float)):
            total += int(value)
    return total
