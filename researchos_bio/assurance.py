"""Conservative cross-layer assurance assessment.

This module composes integrity, reviewer-declaration and cryptographic checks.
It NEVER verifies biological truth, real-world identity, reviewer independence,
or actual replication, and cannot promote a claim's authoritative status.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import verify_artifacts
from .attestations import verify_attestations
from .core import RecordError, evaluate_record, sha256_data, validate_record
from .reviews import evaluate_reviews


def assess_assurance(
    record: dict[str, Any],
    manifest: dict[str, Any],
    artifact_root: str | Path,
    review_bundle: dict[str, Any],
    trust_registry: dict[str, Any],
    signatures: dict[str, Any],
) -> dict[str, Any]:
    """Produce an auditable *advisory* gate assessment for a single protocol.

    ``ready_for_manual_adjudication`` is not permission to accept a claim.
    All metadata and reviewer independence declarations may be inaccurate.
    """
    claims, _ = validate_record(record)
    protocol_ids = {claim.protocol_id for claim in claims}
    if len(protocol_ids) != 1 or manifest.get("protocol_id") not in protocol_ids:
        raise RecordError("assurance manifest protocol_id must match the single claim protocol")

    evidence_report = evaluate_record(record)
    artifact_report = verify_artifacts(record, manifest, artifact_root)
    review_report = evaluate_reviews(record, review_bundle)
    signature_report = verify_attestations(record, review_bundle, trust_registry, signatures)

    artifacts = {entry["evidence_id"]: entry for entry in artifact_report["artifacts"]}
    signed = {entry["review_id"]: entry["cryptographically_attested"]
              for entry in signature_report["reviews"]}
    reviews = {entry["review_id"]: entry for entry in review_report["reviews"]}
    review_by_claim: dict[str, list[dict[str, Any]]] = {claim.claim_id: [] for claim in claims}
    for entry in reviews.values():
        review_by_claim[entry["claim_id"]].append(entry)

    decisions = []
    for entry in evidence_report["decisions"]:
        claim_id = entry["claim_id"]
        claim = next(claim for claim in claims if claim.claim_id == claim_id)
        supporting_artifacts_match = bool(claim.evidence_ids) and all(
            artifacts[eid]["status"] == "match" for eid in claim.evidence_ids
        )
        claim_reviews = review_by_claim[claim_id]
        challenges = sorted(x["review_id"] for x in claim_reviews if x["decision"] == "challenge")
        signed_eligible = sorted(
            x["review_id"] for x in claim_reviews
            if x["self_declared_eligible"] and signed.get(x["review_id"], False)
        )
        all_claim_reviews_signed = bool(claim_reviews) and all(
            signed.get(x["review_id"], False) for x in claim_reviews
        )
        # A challenge blocks the path even if its signature is missing; it
        # must be investigated, not silently dropped from the audit trail.
        if entry["failing_evidence_ids"] or challenges:
            gate, reason = "contested", "recorded failure or unresolved reviewer challenge"
        elif (not entry["passing_evidence_ids"] or entry["uncertain_evidence_ids"]
              or not supporting_artifacts_match):
            gate, reason = "needs_evidence", "evidence is absent, uncertain or fails local integrity verification"
        elif not signed_eligible or not all_claim_reviews_signed:
            gate, reason = "needs_review", "missing eligible signed review or unsigned review remains"
        else:
            gate, reason = "ready_for_manual_adjudication", "local integrity and signed reviewer declarations present"
        decisions.append({
            "claim_id": claim_id,
            "current_status": entry["current_status"],
            "advisory_gate": gate,
            "reason": reason,
            "all_claim_artifacts_match": supporting_artifacts_match,
            "signed_self_declared_eligible_review_ids": signed_eligible,
            "challenge_review_ids": challenges,
            "all_claim_reviews_signed": all_claim_reviews_signed,
            "independence_verified": False,
            "biological_validity_verified": False,
            "independent_replication_verified": False,
            "automatic_status_promotion_permitted": False,
        })
    payload = {
        "report_version": "1.0",
        "record_sha256": sha256_data(record),
        "manifest_sha256": sha256_data(manifest),
        "review_bundle_sha256": sha256_data(review_bundle),
        "trust_registry_sha256": sha256_data(trust_registry),
        "signatures_sha256": sha256_data(signatures),
        "evidence_report_sha256": evidence_report["report_sha256"],
        "artifact_report_sha256": artifact_report["report_sha256"],
        "review_report_sha256": review_report["report_sha256"],
        "signature_report_sha256": signature_report["report_sha256"],
        "claims": decisions,
        "disclaimer": (
            "Advisory metadata gate only: file integrity and trusted-key signatures do not "
            "establish reviewer identity, independence, replication or scientific truth."
        ),
    }
    return {**payload, "report_sha256": sha256_data(payload)}
