"""Preregistered numeric reproduction comparisons, with explicit scientific limits.

This module evaluates supplied numeric results against fixed preregistered
thresholds. It does not authenticate datasets, rerun experiments, or certify
scientific reproducibility.
"""
from __future__ import annotations

from datetime import datetime
import math
from typing import Any

from .core import RecordError, sha256_data, validate_record


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{label} must be nonempty text")
    return value


def _time(value: Any, label: str) -> str:
    _text(value, label)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecordError(f"{label} must be ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise RecordError(f"{label} must be timezone-aware")
    return value


def _number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise RecordError(f"{label} must be a finite number")
    return float(value)


def evaluate_benchmark(record: dict[str, Any], plan: dict[str, Any],
                       outcomes: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one result per planned claim, no post-hoc threshold changes.

    The plan is externally supplied and must be frozen before measurements.
    A timestamp check is informational/structural only; timestamps are not
    cryptographic proof of preregistration.
    """
    claims, _ = validate_record(record)
    known = {c.claim_id: c for c in claims}
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise RecordError("plan schema_version must be 1.0")
    if not isinstance(outcomes, dict) or outcomes.get("schema_version") != "1.0":
        raise RecordError("outcomes schema_version must be 1.0")
    if plan.get("record_sha256") != sha256_data(record):
        raise RecordError("plan not bound to exact source record")
    if outcomes.get("plan_sha256") != sha256_data(plan):
        raise RecordError("outcomes not bound to exact preregistered plan")
    registered = _time(plan.get("registered_at"), "registered_at")
    specs = plan.get("comparisons")
    observations = outcomes.get("results")
    if not isinstance(specs, list) or not specs:
        raise RecordError("comparisons must be a nonempty list")
    if not isinstance(observations, list):
        raise RecordError("results must be a list")
    defined = {}
    for spec in specs:
        if not isinstance(spec, dict):
            raise RecordError("comparison must be an object")
        cid = _text(spec.get("claim_id"), "claim_id")
        if cid in defined or cid not in known:
            raise RecordError("duplicate or unknown planned claim")
        if spec.get("protocol_id") != known[cid].protocol_id:
            raise RecordError("planned protocol differs from claim protocol")
        _text(spec.get("metric"), "metric")
        _text(spec.get("unit"), "unit")
        _text(spec.get("analysis_method"), "analysis_method")
        reference = _number(spec.get("reference_value"), "reference_value")
        tolerance = _number(spec.get("absolute_tolerance"), "absolute_tolerance")
        if tolerance < 0:
            raise RecordError("absolute_tolerance cannot be negative")
        defined[cid] = (spec, reference, tolerance)
    seen = set()
    reported = {}
    for obs in observations:
        if not isinstance(obs, dict):
            raise RecordError("result must be an object")
        cid = _text(obs.get("claim_id"), "claim_id")
        if cid in seen or cid not in defined:
            raise RecordError("duplicate or unplanned result")
        seen.add(cid)
        _text(obs.get("run_id"), "run_id")
        _text(obs.get("operator_id"), "operator_id")
        _text(obs.get("organization_id"), "organization_id")
        _text(obs.get("artifact_evidence_id"), "artifact_evidence_id")
        observed = _time(obs.get("observed_at"), "observed_at")
        if datetime.fromisoformat(observed.replace("Z", "+00:00")) < datetime.fromisoformat(registered.replace("Z", "+00:00")):
            raise RecordError("result timestamp predates plan registration")
        val = _number(obs.get("observed_value"), "observed_value")
        evidence = {e["evidence_id"]: e for e in record["evidence"]}
        if obs["artifact_evidence_id"] not in evidence or evidence[obs["artifact_evidence_id"]]["claim_id"] != cid:
            raise RecordError("result artifact evidence is unknown or belongs to another claim")
        reported[cid] = (obs, val)
    results = []
    for cid, (spec, reference, tolerance) in sorted(defined.items()):
        if cid not in reported:
            results.append({"claim_id": cid, "status": "missing", "within_tolerance": False})
            continue
        obs, value = reported[cid]
        deviation = abs(value - reference)
        within = deviation <= tolerance
        results.append({
            "claim_id": cid, "run_id": obs["run_id"],
            "metric": spec["metric"], "unit": spec["unit"],
            "reference_value": reference, "observed_value": value,
            "absolute_tolerance": tolerance, "absolute_deviation": deviation,
            "within_tolerance": within, "status": "within_tolerance" if within else "outside_tolerance",
            "external_replication_verified": False,
        })
    payload = {
        "report_version": "1.0", "record_sha256": sha256_data(record),
        "plan_sha256": sha256_data(plan), "outcomes_sha256": sha256_data(outcomes),
        "comparisons": results,
        "all_reported_results_within_tolerance": bool(results) and all(x["within_tolerance"] for x in results),
        "scientific_reproduction_verified": False,
        "disclaimer": "Numeric comparison only; source artifacts, registration timing, operator independence and scientific validity require external audit.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
