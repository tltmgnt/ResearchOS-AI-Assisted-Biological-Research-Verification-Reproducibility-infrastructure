"""Phase 13: deterministic descriptive uncertainty and missing-data accountability.

Intervals are approximate and conditional on the observed sample; they do not
establish independent evaluation, randomization, causality or biological truth.
"""
from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Any

from .core import RecordError, sha256_data
from .pilot_comparison import evaluate_pilot_comparison


def evaluate_pilot_statistics(plan: dict[str, Any],
                              observations: dict[str, Any],
                              accounting: dict[str, Any]) -> dict[str, Any]:
    """Recompute paired metrics and apply a preregistered case accounting frame."""
    descriptive = evaluate_pilot_comparison(plan, observations)
    if not isinstance(accounting, dict) or accounting.get("schema_version") != "1.0":
        raise RecordError("case accounting schema_version must be 1.0")
    if accounting.get("plan_sha256") != sha256_data(plan):
        raise RecordError("case accounting must bind to exact plan")
    cases = accounting.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RecordError("case accounting requires a nonempty cases list")
    seen, enrolled, missing, excluded = set(), set(), [], []
    allowed = {"completed", "missing", "excluded"}
    for case in cases:
        if not isinstance(case, dict):
            raise RecordError("case accounting entry must be an object")
        cid = case.get("case_id")
        status = case.get("status")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise RecordError("accounted case IDs must be unique and nonempty")
        if status not in allowed:
            raise RecordError("case status must be completed, missing or excluded")
        seen.add(cid)
        if status == "completed":
            enrolled.add(cid)
        else:
            reason = case.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise RecordError("missing/excluded cases require an explicit reason")
            (missing if status == "missing" else excluded).append({
                "case_id": cid, "reason": reason})
    observed = {x["case_id"] for x in descriptive["pairs"]}
    if observed != enrolled:
        raise RecordError("completed cases must exactly match paired observations")
    n = len(observed)
    total = len(cases)
    differences = [x["difference_minutes"] for x in descriptive["pairs"]]
    sample_mean = mean(differences) if differences else None
    sample_sd = stdev(differences) if n >= 2 else None
    # Normal-approximation interval for the mean paired difference, not a
    # calibrated small-sample confidence interval. No inference when n < 2.
    standard_error = sample_sd / math.sqrt(n) if n >= 2 else None
    interval = ([sample_mean - 1.96 * standard_error,
                 sample_mean + 1.96 * standard_error] if n >= 2 else None)
    payload = {
        "report_version": "1.0",
        "plan_sha256": sha256_data(plan),
        "observations_sha256": sha256_data(observations),
        "accounting_sha256": sha256_data(accounting),
        "descriptive_report_sha256": descriptive["report_sha256"],
        "planned_cases": total,
        "completed_cases": n,
        "missing_cases": missing,
        "excluded_cases": excluded,
        "completion_fraction": n / total,
        "minimum_sample_size_met": descriptive["minimum_sample_size_met"],
        "mean_paired_difference_minutes": sample_mean,
        "sample_sd_paired_difference_minutes": sample_sd,
        "standard_error_mean_difference_minutes": standard_error,
        "normal_approximation_95pct_interval_minutes": interval,
        "interval_is_confirmatory": False,
        "causal_effect_established": False,
        "independent_evaluation_verified": False,
        "scientific_replication_verified": False,
        "disclaimer": "Approximate descriptive interval only; assumes independent paired differences and may be unreliable for small or selected samples. Missingness, selection, order effects and preregistration authenticity require external review.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
