"""Phase 5 governance: explicit reviewer enrollment, key revocation and review quorum.

All decisions are administrative readiness checks, not biological certification.
The caller must independently authenticate the policy and registry.
"""
from __future__ import annotations

from typing import Any

from .attestations import verify_attestations
from .core import RecordError, sha256_data
from .reviews import evaluate_reviews


def _ids(value: Any, name: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise RecordError(f"{name} must be an array of nonempty strings")
    if len(set(value)) != len(value):
        raise RecordError(f"{name} contains duplicate IDs")
    return set(value)


def evaluate_governance(
    record: dict[str, Any],
    bundle: dict[str, Any],
    registry: dict[str, Any],
    signatures: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate signed review quorum with operator-maintained reviewer enrollment.

    Requires authenticated input distribution out-of-band. Enrollment and
    revocation are operator declarations, not externally verified credentials.
    """
    attested = verify_attestations(record, bundle, registry, signatures)
    reviewed = evaluate_reviews(record, bundle)
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0":
        raise RecordError("policy schema_version must be 1.0")
    threshold = policy.get("minimum_distinct_organizations")
    if type(threshold) is not int or threshold < 2:
        raise RecordError("minimum_distinct_organizations must be an integer >= 2")
    revoked = _ids(policy.get("revoked_key_ids"), "revoked_key_ids")
    enrolled = policy.get("enrolled_reviewers")
    if not isinstance(enrolled, list):
        raise RecordError("enrolled_reviewers must be an array")
    people: dict[str, dict[str, Any]] = {}
    for entry in enrolled:
        if not isinstance(entry, dict):
            raise RecordError("enrolled reviewer must be an object")
        reviewer = entry.get("reviewer_id")
        org = entry.get("organization_id")
        if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(org, str) or not org.strip():
            raise RecordError("reviewer_id and organization_id must be nonempty strings")
        if reviewer in people:
            raise RecordError("duplicate enrolled reviewer")
        if type(entry.get("approved")) is not bool:
            raise RecordError("approved must be a boolean")
        people[reviewer] = entry
    sig_by_review = {s["review_id"]: s for s in signatures["signatures"]}
    att_by_review = {r["review_id"]: r for r in attested["reviews"]}
    check_by_review = {r["review_id"]: r for r in reviewed["reviews"]}
    outcomes = []
    for claim in reviewed["claims"]:
        qualifying: dict[str, str] = {}
        rejected = []
        challenges = claim["challenge_count"]
        for item in bundle["reviews"]:
            if item["claim_id"] != claim["claim_id"]:
                continue
            rid, reviewer, org = item["review_id"], item["reviewer_id"], item["organization_id"]
            enrolled_entry = people.get(reviewer)
            key_id = sig_by_review.get(rid, {}).get("key_id")
            reasons = []
            if not att_by_review[rid]["cryptographically_attested"]:
                reasons.append("invalid_or_missing_signature")
            if key_id in revoked:
                reasons.append("revoked_key")
            if enrolled_entry is None or not enrolled_entry["approved"]:
                reasons.append("reviewer_not_approved")
            elif enrolled_entry["organization_id"] != org:
                reasons.append("organization_mismatch")
            if not check_by_review[rid]["self_declared_eligible"]:
                reasons.append("review_not_eligible")
            if reasons:
                rejected.append({"review_id": rid, "reasons": reasons})
            elif reviewer in qualifying:
                rejected.append({"review_id": rid, "reasons": ["duplicate_reviewer_for_claim"]})
            else:
                qualifying[reviewer] = org
        organizations = sorted(set(qualifying.values()))
        ready = len(organizations) >= threshold and not challenges
        outcomes.append({
            "claim_id": claim["claim_id"],
            "administrative_review_ready": ready,
            "distinct_approved_organizations": len(organizations),
            "minimum_distinct_organizations": threshold,
            "accepted_reviewer_ids": sorted(qualifying),
            "rejected_reviews": rejected,
            "unresolved_challenges": challenges,
            "independent_replication_verified": False,
            "biological_claim_validated": False,
        })
    payload = {
        "report_version": "1.0",
        "record_sha256": sha256_data(record),
        "review_bundle_sha256": sha256_data(bundle),
        "trust_registry_sha256": sha256_data(registry),
        "attestations_sha256": sha256_data(signatures),
        "policy_sha256": sha256_data(policy),
        "claims": outcomes,
        "disclaimer": "Administrative review readiness only. Enrollment and key revocation are local operator assertions; no real-world identity or scientific validity is independently proven.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
