"""Phase 14: cross-report evaluation dossier with strict hash-based traceability.

All input reports are untrusted. Hash linkage establishes consistency of
supplied documents, not authenticity of raw evidence or independent evaluation.
"""
from __future__ import annotations

from typing import Any

from .core import RecordError, sha256_data


def _report(obj: Any, name: str) -> dict[str, Any]:
    if not isinstance(obj, dict) or obj.get("report_version") != "1.0":
        raise RecordError(f"{name} must be a version 1.0 report")
    expected = sha256_data({k: v for k, v in obj.items() if k != "report_sha256"})
    if obj.get("report_sha256") != expected:
        raise RecordError(f"{name} report fingerprint mismatch")
    return obj


def assemble_evaluation_dossier(
    pilot_report: dict[str, Any],
    comparison_report: dict[str, Any],
    statistics_report: dict[str, Any],
    audit_report: dict[str, Any],
    source_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check report chain and produce a reviewable evidence inventory."""
    pilot = _report(pilot_report, "pilot")
    comparison = _report(comparison_report, "comparison")
    stats = _report(statistics_report, "statistics")
    audit = _report(audit_report, "audit")
    if stats.get("descriptive_report_sha256") != comparison["report_sha256"]:
        raise RecordError("statistics report not bound to supplied comparison")
    if stats.get("plan_sha256") != comparison.get("plan_sha256"):
        raise RecordError("comparison and statistics use different plans")
    if stats.get("observations_sha256") != comparison.get("observations_sha256"):
        raise RecordError("comparison and statistics use different observations")
    if audit.get("pilot_report_sha256") != sha256_data(pilot):
        raise RecordError("audit report not bound to supplied pilot report")
    if type(pilot.get("software_pilot_gate_passed")) is not bool:
        raise RecordError("pilot gate must be boolean")
    if type(audit.get("administrative_external_audit_accepted")) is not bool:
        raise RecordError("audit acceptance must be boolean")
    if type(stats.get("minimum_sample_size_met")) is not bool:
        raise RecordError("sample-size gate must be boolean")
    if type(stats.get("planned_cases")) is not int or stats["planned_cases"] < 1:
        raise RecordError("planned case count must be positive")
    if type(stats.get("completed_cases")) is not int or not 0 <= stats["completed_cases"] <= stats["planned_cases"]:
        raise RecordError("completed case count is invalid")
    if not isinstance(source_evidence, list):
        raise RecordError("source_evidence must be an array")
    seen = set()
    inventory = []
    for item in source_evidence:
        if not isinstance(item, dict):
            raise RecordError("source evidence entry must be an object")
        evidence_id = item.get("evidence_id")
        digest = item.get("sha256")
        role = item.get("role")
        if not isinstance(evidence_id, str) or not evidence_id.strip() or evidence_id in seen:
            raise RecordError("source evidence IDs must be nonempty and unique")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RecordError("source evidence sha256 must be lowercase hexadecimal SHA-256")
        if role not in ("raw_timing", "preregistration", "case_accounting",
                        "reviewer_identity", "protocol_deviation", "audit_log"):
            raise RecordError("unknown source evidence role")
        seen.add(evidence_id)
        inventory.append({"evidence_id": evidence_id, "sha256": digest, "role": role})
    missing = stats.get("missing_cases")
    excluded = stats.get("excluded_cases")
    if not isinstance(missing, list) or not isinstance(excluded, list):
        raise RecordError("statistics report must include missing and excluded cases")
    if stats["completed_cases"] + len(missing) + len(excluded) != stats["planned_cases"]:
        raise RecordError("case accounting totals do not reconcile")
    links = {
        "pilot_report_sha256": pilot["report_sha256"],
        "comparison_report_sha256": comparison["report_sha256"],
        "statistics_report_sha256": stats["report_sha256"],
        "audit_report_sha256": audit["report_sha256"],
    }
    ready = (pilot["software_pilot_gate_passed"]
             and audit["administrative_external_audit_accepted"]
             and stats["minimum_sample_size_met"]
             and len(missing) == 0 and len(excluded) == 0
             and bool(inventory))
    payload = {
        "report_version": "1.0",
        "report_links": links,
        "source_evidence": inventory,
        "planned_cases": stats["planned_cases"],
        "completed_cases": stats["completed_cases"],
        "missing_cases": missing,
        "excluded_cases": excluded,
        "observed_time_reduction_fraction": comparison.get("observed_time_reduction_fraction"),
        "normal_approximation_95pct_interval_minutes": stats.get("normal_approximation_95pct_interval_minutes"),
        "administrative_dossier_complete": ready,
        "source_artifact_bytes_verified": False,
        "external_evaluator_identity_verified": False,
        "independent_scientific_replication_verified": False,
        "disclaimer": "Cross-report hashes and declared evidence digests do not verify source bytes, identity, causality, independence, or biological validity.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
