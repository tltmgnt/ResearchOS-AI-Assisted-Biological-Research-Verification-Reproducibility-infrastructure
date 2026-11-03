"""Phase 12: paired pilot comparison and honest, descriptive performance metrics.

These are administrative software-workflow metrics, not biological replication.
No causal improvement or statistical significance is inferred.
"""
from __future__ import annotations

from statistics import median
from typing import Any

from .core import RecordError, sha256_data


def evaluate_pilot_comparison(plan: dict[str, Any], observations: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise RecordError("pilot plan schema_version must be 1.0")
    if not isinstance(observations, dict) or observations.get("schema_version") != "1.0":
        raise RecordError("pilot observations schema_version must be 1.0")
    if observations.get("plan_sha256") != sha256_data(plan):
        raise RecordError("observations must bind to the exact preregistered plan")
    min_pairs = plan.get("minimum_pairs")
    if type(min_pairs) is not int or min_pairs < 2:
        raise RecordError("minimum_pairs must be integer >= 2")
    if plan.get("metric") != "audit_reconstruction_minutes":
        raise RecordError("metric must be audit_reconstruction_minutes")
    if plan.get("comparison_design") != "paired":
        raise RecordError("comparison_design must be paired")
    if not isinstance(plan.get("registered_at"), str) or not plan["registered_at"].strip():
        raise RecordError("registered_at must be nonempty")
    if not isinstance(plan.get("protocol_id"), str) or not plan["protocol_id"].strip():
        raise RecordError("protocol_id must be nonempty")
    rows = observations.get("pairs")
    if not isinstance(rows, list):
        raise RecordError("pairs must be an array")
    seen = set()
    normalized = []
    for item in rows:
        if not isinstance(item, dict):
            raise RecordError("each pair must be an object")
        cid = item.get("case_id")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise RecordError("case_id must be nonempty and unique")
        seen.add(cid)
        baseline = item.get("baseline_minutes")
        researchos = item.get("researchos_minutes")
        for name, value in (("baseline_minutes", baseline), ("researchos_minutes", researchos)):
            if type(value) not in (int, float) or not 0 < value < float("inf"):
                raise RecordError(f"{name} must be positive and finite")
        if not isinstance(item.get("evaluator_id"), str) or not item["evaluator_id"].strip():
            raise RecordError("evaluator_id must be nonempty")
        normalized.append({"case_id": cid, "baseline_minutes": baseline,
                           "researchos_minutes": researchos,
                           "difference_minutes": baseline - researchos,
                           "evaluator_id": item["evaluator_id"]})
    baseline_total = sum(x["baseline_minutes"] for x in normalized)
    researchos_total = sum(x["researchos_minutes"] for x in normalized)
    complete = len(normalized) >= min_pairs
    reduction = (baseline_total - researchos_total) / baseline_total if baseline_total else None
    payload = {
        "report_version": "1.0",
        "plan_sha256": sha256_data(plan),
        "observations_sha256": sha256_data(observations),
        "paired_cases": len(normalized),
        "minimum_pairs": min_pairs,
        "minimum_sample_size_met": complete,
        "baseline_total_minutes": baseline_total,
        "researchos_total_minutes": researchos_total,
        "observed_time_reduction_fraction": reduction,
        "median_paired_difference_minutes": median(
            x["difference_minutes"] for x in normalized) if normalized else None,
        "pairs": normalized,
        "independent_evaluation_verified": False,
        "causal_effect_established": False,
        "scientific_replication_verified": False,
        "disclaimer": "Descriptive paired audit timing only; evaluator independence, randomization, confounding, causality and biological validity require external study.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
