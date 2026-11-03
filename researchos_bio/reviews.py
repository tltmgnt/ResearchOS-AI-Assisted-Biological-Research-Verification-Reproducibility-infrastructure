"""Phase 3: auditable independent-review declarations.

Reviewer identities, independence and reproduction are *self-attested*.
This module does not authenticate people or cryptographically verify signatures.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .core import RecordError, sha256_data, validate_record

_DECISIONS = frozenset({"confirm", "challenge", "inconclusive"})


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{field} must be a nonempty string")
    return value


def _time(value: Any) -> str:
    _string(value, "reviewed_at")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecordError("reviewed_at must be ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise RecordError("reviewed_at requires timezone")
    return value


def evaluate_reviews(record: dict[str, Any], review_bundle: dict[str, Any]) -> dict[str, Any]:
    """Evaluate declarations without promoting claims to reproduced or validated."""
    claims, evidence = validate_record(record)
    if not isinstance(review_bundle, dict) or review_bundle.get("schema_version") != "1.0":
        raise RecordError("review bundle schema_version must be 1.0")
    if review_bundle.get("record_sha256") != sha256_data(record):
        raise RecordError("review bundle is not bound to this exact claim/evidence record")
    reviews = review_bundle.get("reviews")
    if not isinstance(reviews, list):
        raise RecordError("reviews must be an array")
    claims_by_id = {c.claim_id: c for c in claims}
    evidence_by_id = {e.evidence_id: e for e in evidence}
    seen = set()
    result = []
    for item in reviews:
        if not isinstance(item, dict):
            raise RecordError("each review must be an object")
        rid = _string(item.get("review_id"), "review_id")
        if rid in seen:
            raise RecordError("duplicate review_id")
        seen.add(rid)
        cid = _string(item.get("claim_id"), "claim_id")
        reviewer = _string(item.get("reviewer_id"), "reviewer_id")
        organization = _string(item.get("organization_id"), "organization_id")
        method = _string(item.get("reproduction_method"), "reproduction_method")
        protocol = _string(item.get("protocol_id"), "protocol_id")
        timestamp = _time(item.get("reviewed_at"))
        decision = item.get("decision")
        if decision not in _DECISIONS:
            raise RecordError("review decision must be confirm, challenge, or inconclusive")
        if cid not in claims_by_id or protocol != claims_by_id[cid].protocol_id:
            raise RecordError("review references unknown claim or incorrect protocol")
        refs = item.get("evidence_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x for x in refs):
            raise RecordError("review evidence_ids must be a nonempty list of IDs")
        if len(set(refs)) != len(refs):
            raise RecordError("duplicate review evidence IDs")
        if any(x not in evidence_by_id or evidence_by_id[x].claim_id != cid for x in refs):
            raise RecordError("review references unknown or foreign evidence")
        for field in ("independent_of_original_team", "raw_data_available", "protocol_followed"):
            if type(item.get(field)) is not bool:
                raise RecordError(f"{field} must be a boolean")
        conflicts = item.get("conflicts_of_interest")
        if not isinstance(conflicts, list) or any(not isinstance(x, str) or not x.strip() for x in conflicts):
            raise RecordError("conflicts_of_interest must be a list of strings")
        if not isinstance(item.get("notes", ""), str):
            raise RecordError("notes must be a string")
        # A reviewer statement is a declaration, not proof of independence.
        eligible = (
            decision == "confirm"
            and item["independent_of_original_team"]
            and item["raw_data_available"]
            and item["protocol_followed"]
            and not conflicts
            and all(evidence_by_id[eid].verdict == "pass" for eid in refs)
        )
        result.append({
            "review_id": rid, "claim_id": cid, "reviewer_id": reviewer,
            "organization_id": organization, "reviewed_at": timestamp,
            "decision": decision, "reproduction_method": method,
            "self_declared_eligible": eligible,
            "independence_verified": False, "identity_authenticated": False,
            "external_replication_verified": False,
            "manual_verification_required": True,
            "conflict_disclosed": bool(conflicts),
        })
    by_claim = []
    for claim in claims:
        related = [x for x in result if x["claim_id"] == claim.claim_id]
        eligible = [x for x in related if x["self_declared_eligible"]]
        challenges = [x for x in related if x["decision"] == "challenge"]
        by_claim.append({
            "claim_id": claim.claim_id,
            "review_count": len(related),
            "self_declared_eligible_count": len(eligible),
            "challenge_count": len(challenges),
            "requires_adjudication": bool(challenges),
            "independent_replication_verified": False,
            "recommended_action": "resolve_challenge" if challenges else (
                "external_identity_and_method_audit" if eligible else "collect_independent_review"),
        })
    payload = {
        "report_version": "1.0",
        "record_sha256": sha256_data(record),
        "review_bundle_sha256": sha256_data(review_bundle),
        "reviews": result, "claims": by_claim,
        "disclaimer": "Declarations only. No cryptographic signature, reviewer authentication, verified independence, or scientific replication.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}


def verify_review_report(record: dict[str, Any], bundle: dict[str, Any], report: dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    try:
        return evaluate_reviews(record, bundle) == report
    except RecordError:
        return False
