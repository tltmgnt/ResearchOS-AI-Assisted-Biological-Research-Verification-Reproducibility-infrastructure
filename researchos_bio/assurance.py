"""Phase 7: deterministic, non-certifying multi-layer assurance records.

A green administrative or numerical check is never proof of biological truth.
"""
from __future__ import annotations

from typing import Any

from .artifacts import verify_artifacts
from .attestations import verify_attestations
from .benchmarks import evaluate_benchmark
from .core import RecordError, sha256_data
from .governance import evaluate_governance
from .reviews import evaluate_reviews


def assemble_assurance(
    record: dict[str, Any],
    manifest: dict[str, Any],
    artifact_root: str,
    review_bundle: dict[str, Any],
    trust_registry: dict[str, Any],
    signatures: dict[str, Any],
    policy: dict[str, Any],
    benchmark_plan: dict[str, Any],
    benchmark_outcomes: dict[str, Any],
) -> dict[str, Any]:
    """Recompute each verification layer rather than trusting supplied reports."""
    artifact = verify_artifacts(record, manifest, artifact_root)
    reviews = evaluate_reviews(record, review_bundle)
    signed = verify_attestations(record, review_bundle, trust_registry, signatures)
    governance = evaluate_governance(record, review_bundle, trust_registry, signatures, policy)
    benchmark = evaluate_benchmark(record, benchmark_plan, benchmark_outcomes)
    claim_ids = {item["claim_id"] for item in governance["claims"]}
    benchmark_ids = {item["claim_id"] for item in benchmark["comparisons"]}
    if claim_ids != benchmark_ids:
        raise RecordError("assurance requires a benchmark comparison for every claim")
    signed_by_id = {item["review_id"]: item for item in signed["reviews"]}
    reviews_by_id = {item["review_id"]: item for item in reviews["reviews"]}
    artifacts_by_evidence = {item["evidence_id"]: item for item in artifact["artifacts"]}
    outcomes_by_claim = {item["claim_id"]: item for item in benchmark["comparisons"]}
    combined = []
    for item in governance["claims"]:
        cid = item["claim_id"]
        # Every accepted review must be signed, and every cited evidence file must match.
        accepted = set(item["accepted_reviewer_ids"])
        qualifying = [
            review for review in reviews_by_id.values()
            if review["claim_id"] == cid and review["reviewer_id"] in accepted
            and review["self_declared_eligible"]
            and signed_by_id[review["review_id"]]["cryptographically_attested"]
        ]
        linked_evidence = [
            evidence for evidence in record["evidence"] if evidence["claim_id"] == cid
        ]
        evidence_verified = bool(linked_evidence) and all(
            artifacts_by_evidence[evidence["evidence_id"]]["status"] == "match"
            for evidence in linked_evidence
        )
        benchmark_ok = outcomes_by_claim[cid]["within_tolerance"]
        ready = (
            artifact["all_artifacts_verified"]
            and evidence_verified
            and item["administrative_review_ready"]
            and benchmark_ok
            and bool(qualifying)
        )
        combined.append({
            "claim_id": cid,
            "artifact_integrity_verified": evidence_verified,
            "administrative_review_ready": item["administrative_review_ready"],
            "benchmark_within_tolerance": benchmark_ok,
            "signed_qualifying_review_count": len(qualifying),
            "assurance_packet_complete": ready,
            "independent_replication_verified": False,
            "scientific_claim_validated": False,
            "recommended_action": "external_scientific_audit" if ready else "resolve_failed_checks",
        })
    payload: dict[str, Any] = {
        "report_version": "1.0",
        "record_sha256": sha256_data(record),
        "artifact_report_sha256": artifact["report_sha256"],
        "review_report_sha256": reviews["report_sha256"],
        "signature_report_sha256": signed["report_sha256"],
        "governance_report_sha256": governance["report_sha256"],
        "benchmark_report_sha256": benchmark["report_sha256"],
        "claims": combined,
        "all_assurance_packets_complete": bool(combined) and all(
            item["assurance_packet_complete"] for item in combined
        ),
        "scientific_validation_performed": False,
        "disclaimer": "Assurance packet completeness is not biological validation, verified independence, or experimental reproduction. External scientific audit required.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
