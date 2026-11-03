"""Phase 10: externally signed audit decisions over exact pilot report bytes.

Signatures establish possession of enrolled keys, not real-world evaluator identity.
The trust registry and evaluator enrollment must be authenticated out-of-band.
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import RecordError, canonical_bytes, sha256_data


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{name} must be nonempty text")
    return value


def _decode(value: Any, length: int, name: str) -> bytes:
    if not isinstance(value, str):
        raise RecordError(f"{name} must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RecordError(f"{name} must be valid base64") from exc
    if len(raw) != length:
        raise RecordError(f"{name} must decode to {length} bytes")
    return raw


def audit_payload(pilot_report: dict[str, Any], decision: dict[str, Any]) -> bytes:
    """Domain-separated signature payload bound to the exact pilot report."""
    if not isinstance(pilot_report, dict) or not isinstance(decision, dict):
        raise RecordError("pilot report and decision must be objects")
    return canonical_bytes({
        "domain": "researchos.external-audit.v1",
        "pilot_report_sha256": sha256_data(pilot_report),
        "decision": decision,
    })


def verify_external_audit(pilot_report: dict[str, Any],
                          trust_registry: dict[str, Any],
                          audit_bundle: dict[str, Any],
                          minimum_organizations: int = 2) -> dict[str, Any]:
    """Verify enrolled evaluator signatures and cross-organization consensus.

    No external identity provider, tamper-proof timestamp or scientific ground
    truth is assumed. A negative decision vetoes administrative acceptance.
    """
    if not isinstance(pilot_report, dict) or pilot_report.get("report_version") != "1.0":
        raise RecordError("pilot report must be version 1.0")
    expected = sha256_data({k: v for k, v in pilot_report.items() if k != "report_sha256"})
    if pilot_report.get("report_sha256") != expected:
        raise RecordError("pilot report fingerprint mismatch")
    if not isinstance(trust_registry, dict) or trust_registry.get("schema_version") != "1.0":
        raise RecordError("audit trust registry schema_version must be 1.0")
    if not isinstance(audit_bundle, dict) or audit_bundle.get("schema_version") != "1.0":
        raise RecordError("audit bundle schema_version must be 1.0")
    if audit_bundle.get("pilot_report_sha256") != sha256_data(pilot_report):
        raise RecordError("audit bundle is not bound to exact pilot report")
    if type(minimum_organizations) is not int or minimum_organizations < 2:
        raise RecordError("minimum_organizations must be an integer >= 2")
    keys = trust_registry.get("keys")
    decisions = audit_bundle.get("decisions")
    if not isinstance(keys, list) or not isinstance(decisions, list):
        raise RecordError("audit keys and decisions must be arrays")
    trusted = {}
    for key in keys:
        if not isinstance(key, dict):
            raise RecordError("audit key must be an object")
        kid = _nonempty(key.get("key_id"), "key_id")
        evaluator = _nonempty(key.get("evaluator_id"), "evaluator_id")
        org = _nonempty(key.get("organization_id"), "organization_id")
        if type(key.get("approved")) is not bool or type(key.get("revoked")) is not bool:
            raise RecordError("approved and revoked must be booleans")
        if kid in trusted:
            raise RecordError("duplicate audit key ID")
        public = Ed25519PublicKey.from_public_bytes(
            _decode(key.get("public_key_b64"), 32, "public_key_b64"))
        trusted[kid] = (evaluator, org, key["approved"], key["revoked"], public)
    seen_decisions, seen_evaluators = set(), set()
    results, approving_orgs = [], set()
    veto = False
    for item in decisions:
        if not isinstance(item, dict):
            raise RecordError("audit decision must be an object")
        decision = item.get("decision")
        if not isinstance(decision, dict):
            raise RecordError("decision must be an object")
        did = _nonempty(decision.get("decision_id"), "decision_id")
        evaluator = _nonempty(decision.get("evaluator_id"), "evaluator_id")
        org = _nonempty(decision.get("organization_id"), "organization_id")
        verdict = decision.get("verdict")
        if verdict not in ("approve", "reject", "needs_work"):
            raise RecordError("verdict must be approve, reject or needs_work")
        _nonempty(decision.get("reason"), "reason")
        kid = _nonempty(item.get("key_id"), "key_id")
        if did in seen_decisions or evaluator in seen_evaluators:
            raise RecordError("duplicate audit decision or evaluator")
        seen_decisions.add(did)
        seen_evaluators.add(evaluator)
        status = "untrusted_key"
        if kid in trusted:
            owner, key_org, approved, revoked, public = trusted[kid]
            if owner != evaluator or key_org != org:
                status = "identity_mismatch"
            elif revoked:
                status = "revoked_key"
            elif not approved:
                status = "unapproved_key"
            else:
                signature = _decode(item.get("signature_b64"), 64, "signature_b64")
                try:
                    public.verify(signature, audit_payload(pilot_report, decision))
                    status = "valid"
                except InvalidSignature:
                    status = "invalid_signature"
        if status == "valid":
            if verdict == "approve":
                approving_orgs.add(org)
            else:
                veto = True
        results.append({"decision_id": did, "evaluator_id": evaluator,
                        "organization_id": org, "verdict": verdict,
                        "signature_status": status})
    ready = (pilot_report.get("software_pilot_gate_passed") is True
             and len(approving_orgs) >= minimum_organizations and not veto
             and bool(results) and all(x["signature_status"] == "valid" for x in results))
    payload = {
        "report_version": "1.0",
        "pilot_report_sha256": sha256_data(pilot_report),
        "audit_trust_registry_sha256": sha256_data(trust_registry),
        "audit_bundle_sha256": sha256_data(audit_bundle),
        "minimum_organizations": minimum_organizations,
        "valid_approving_organizations": len(approving_orgs),
        "negative_decision_veto": veto,
        "administrative_external_audit_accepted": ready,
        "scientific_validation_performed": False,
        "real_world_evaluator_identity_verified": False,
        "decisions": results,
        "disclaimer": "External key signatures authenticate configured keys, not real-world identities or scientific validity. Registry authenticity and independence require out-of-band audit.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
