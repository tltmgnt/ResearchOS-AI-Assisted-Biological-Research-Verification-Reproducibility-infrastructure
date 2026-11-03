"""Dependency-free, bounded research claim/evidence assurance core.

This package tracks documented evidence and computes deterministic status checks.
It does not establish biological truth, independent replication, or clinical validity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

_HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
STATUSES = frozenset({"generated", "unverified", "supported", "contested", "reproduced", "validated"})
VERDICTS = frozenset({"pass", "fail", "uncertain"})


class RecordError(ValueError):
    """Malformed, internally inconsistent or unverifiable record."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RecordError("Record is not canonically serializable") from exc


def sha256_data(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{name} must be a nonempty string")
    return value


def _id_sequence(items: Any, label: str) -> tuple[str, ...]:
    if not isinstance(items, list) or not all(isinstance(x, str) and x.strip() for x in items):
        raise RecordError(f"{label} must be a list of nonempty strings")
    if len(set(items)) != len(items):
        raise RecordError(f"{label} must not contain duplicates")
    return tuple(items)


def _iso_time(value: Any, name: str) -> str:
    _nonempty(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecordError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RecordError(f"{name} must include a timezone offset")
    return value


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    claim_id: str
    source_uri: str
    artifact_sha256: str
    method: str
    observed_at: str
    verdict: str
    operator_id: str
    independent_of: tuple[str, ...] = ()
    notes: str = ""

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Evidence":
        if not isinstance(data, dict):
            raise RecordError("evidence item must be an object")
        for field in ("evidence_id", "claim_id", "source_uri", "method", "operator_id"):
            _nonempty(data.get(field), field)
        digest = data.get("artifact_sha256")
        if not isinstance(digest, str) or not _HEX_SHA256.fullmatch(digest):
            raise RecordError("artifact_sha256 must be a lowercase SHA-256 hex digest")
        verdict = data.get("verdict")
        if verdict not in VERDICTS:
            raise RecordError("evidence verdict must be pass, fail or uncertain")
        _iso_time(data.get("observed_at"), "observed_at")
        independent = _id_sequence(data.get("independent_of", []), "independent_of")
        if data.get("evidence_id") in independent:
            raise RecordError("evidence cannot claim independence from itself")
        notes = data.get("notes", "")
        if not isinstance(notes, str):
            raise RecordError("notes must be a string")
        return cls(**{field: data[field] for field in (
            "evidence_id", "claim_id", "source_uri", "artifact_sha256", "method",
            "observed_at", "verdict", "operator_id")}, independent_of=independent, notes=notes)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    statement: str
    protocol_id: str
    status: str
    evidence_ids: tuple[str, ...]

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Claim":
        if not isinstance(data, dict):
            raise RecordError("claim item must be an object")
        for field in ("claim_id", "statement", "protocol_id"):
            _nonempty(data.get(field), field)
        if data.get("status") not in STATUSES:
            raise RecordError("unknown claim status")
        return cls(data["claim_id"], data["statement"], data["protocol_id"],
                   data["status"], _id_sequence(data.get("evidence_ids", []), "evidence_ids"))


def validate_record(record: dict[str, Any]) -> tuple[list[Claim], list[Evidence]]:
    if not isinstance(record, dict):
        raise RecordError("record must be an object")
    if record.get("schema_version") != "1.0":
        raise RecordError("schema_version must be 1.0")
    _nonempty(record.get("dataset_id"), "dataset_id")
    _nonempty(record.get("protocol_version"), "protocol_version")
    _nonempty(record.get("software_version"), "software_version")
    if not isinstance(record.get("claims"), list) or not isinstance(record.get("evidence"), list):
        raise RecordError("claims and evidence must be arrays")
    claims = [Claim.parse(x) for x in record["claims"]]
    evidence = [Evidence.parse(x) for x in record["evidence"]]
    cids, eids = [x.claim_id for x in claims], [x.evidence_id for x in evidence]
    if len(set(cids)) != len(cids) or len(set(eids)) != len(eids):
        raise RecordError("claim/evidence IDs must be unique")
    by_eid = {x.evidence_id: x for x in evidence}
    by_cid = {x.claim_id: x for x in claims}
    for item in claims:
        for eid in item.evidence_ids:
            if eid not in by_eid or by_eid[eid].claim_id != item.claim_id:
                raise RecordError(f"claim {item.claim_id} references unknown or foreign evidence {eid}")
    for item in evidence:
        if item.claim_id not in by_cid or item.evidence_id not in by_cid[item.claim_id].evidence_ids:
            raise RecordError(f"unlinked evidence {item.evidence_id}")
        for other in item.independent_of:
            if other not in by_eid or by_eid[other].claim_id != item.claim_id:
                raise RecordError(f"invalid independence reference {other}")
    return claims, evidence


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Describe documented checks; never infer scientific truth from metadata alone.

    `independent_of` is a self-reported relationship, never proof of independence.
    No status is promoted automatically: reviewers must assess ground truth and protocols.
    """
    claims, evidence = validate_record(record)
    by_eid = {x.evidence_id: x for x in evidence}
    decisions = []
    for claim in claims:
        items = [by_eid[eid] for eid in claim.evidence_ids]
        failing = [x.evidence_id for x in items if x.verdict == "fail"]
        passing = [x.evidence_id for x in items if x.verdict == "pass"]
        uncertain = [x.evidence_id for x in items if x.verdict == "uncertain"]
        same_operator = len(set(x.operator_id for x in items if x.verdict == "pass")) < 2
        if failing:
            recommendation, reason = "contested", "at least one recorded failure"
        elif passing and uncertain:
            recommendation, reason = "unverified", "unresolved uncertainty remains"
        elif passing:
            recommendation, reason = "supported", "recorded passing checks; external validation not established"
        else:
            recommendation, reason = "unverified", "no passing checks"
        decisions.append({
            "claim_id": claim.claim_id, "current_status": claim.status,
            "recommended_status": recommendation, "reason": reason,
            "passing_evidence_ids": passing, "failing_evidence_ids": failing,
            "uncertain_evidence_ids": uncertain,
            "independent_replication_verified": False,
            "independence_review_required": bool(passing),
            "shared_operator_warning": len(passing) > 1 and same_operator,
        })
    payload = {
        "report_version": "1.0", "record_sha256": sha256_data(record),
        "dataset_id": record["dataset_id"], "protocol_version": record["protocol_version"],
        "software_version": record["software_version"], "decisions": decisions,
        "disclaimer": "Metadata checks only; external biological validity and independence are not established.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}


def verify_report(record: dict[str, Any], report: dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    try:
        return evaluate_record(record) == report
    except RecordError:
        return False
