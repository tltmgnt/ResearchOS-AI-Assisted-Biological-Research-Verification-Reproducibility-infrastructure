"""Phase 17: Ed25519 custody signatures and externally anchored chain heads.

Signatures prove possession of enrolled keys, not physical custody or identity.
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .audit_verify import append_custody_event
from .core import RecordError, canonical_bytes, sha256_data


def _b64(value: Any, length: int, name: str) -> bytes:
    if not isinstance(value, str):
        raise RecordError(f"{name} must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RecordError(f"{name} must be valid base64") from exc
    if len(raw) != length:
        raise RecordError(f"{name} must decode to {length} bytes")
    return raw


def custody_signature_payload(event: dict[str, Any]) -> bytes:
    if not isinstance(event, dict) or not isinstance(event.get("event_sha256"), str):
        raise RecordError("custody event must have event_sha256")
    return canonical_bytes({
        "domain": "researchos.custody-attestation.v1",
        "event_sha256": event["event_sha256"],
        "package_sha256": event.get("package_sha256"),
        "sequence": event.get("sequence"),
    })


def verify_signed_custody(
    events: list[dict[str, Any]],
    signatures: list[dict[str, Any]],
    registry: dict[str, Any],
    package_sha256: str,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    """Validate a custody chain, signatures, key policy and pinned checkpoint."""
    if not isinstance(events, list) or not events:
        raise RecordError("nonempty custody event array required")
    if not isinstance(signatures, list):
        raise RecordError("signatures must be an array")
    if not isinstance(registry, dict) or registry.get("schema_version") != "1.0":
        raise RecordError("trust registry schema_version must be 1.0")
    if not isinstance(anchor, dict) or anchor.get("schema_version") != "1.0":
        raise RecordError("anchor schema_version must be 1.0")
    # Reuse Phase 16's complete hash-chain validator with a no-op append.
    probe = {"custodian_id": "chain-validator", "action": "verified",
             "timestamp": "validation-only", "note": "not appended"}
    append_custody_event(events, probe, package_sha256)
    if anchor.get("package_sha256") != package_sha256:
        raise RecordError("anchor package binding mismatch")
    if type(anchor.get("sequence")) is not int or not 1 <= anchor["sequence"] <= len(events):
        raise RecordError("anchor sequence outside custody chain")
    if anchor.get("event_sha256") != events[anchor["sequence"] - 1]["event_sha256"]:
        raise RecordError("independent anchor does not match custody chain")
    keys = registry.get("keys")
    if not isinstance(keys, list):
        raise RecordError("trust registry keys must be an array")
    keymap = {}
    for key in keys:
        if not isinstance(key, dict):
            raise RecordError("trust key must be an object")
        kid, owner = key.get("key_id"), key.get("custodian_id")
        if not isinstance(kid, str) or not kid.strip() or kid in keymap:
            raise RecordError("key_id must be nonempty and unique")
        if not isinstance(owner, str) or not owner.strip():
            raise RecordError("custodian_id must be nonempty")
        if type(key.get("approved")) is not bool or type(key.get("revoked")) is not bool:
            raise RecordError("approved and revoked must be booleans")
        keymap[kid] = (owner, key["approved"], key["revoked"],
                       Ed25519PublicKey.from_public_bytes(
                           _b64(key.get("public_key_b64"), 32, "public_key_b64")))
    by_sequence = {}
    for item in signatures:
        if not isinstance(item, dict) or type(item.get("sequence")) is not int:
            raise RecordError("signature sequence must be integer")
        seq = item["sequence"]
        if seq in by_sequence or not 1 <= seq <= len(events):
            raise RecordError("duplicate or unknown signature sequence")
        by_sequence[seq] = item
    results = []
    for event in events:
        seq = event["sequence"]
        item = by_sequence.get(seq)
        status = "missing"
        if item is not None:
            kid = item.get("key_id")
            if kid not in keymap:
                status = "untrusted_key"
            else:
                owner, approved, revoked, public = keymap[kid]
                if owner != event["custodian_id"]:
                    status = "custodian_key_mismatch"
                elif revoked:
                    status = "revoked_key"
                elif not approved:
                    status = "unapproved_key"
                else:
                    signature = _b64(item.get("signature_b64"), 64, "signature_b64")
                    try:
                        public.verify(signature, custody_signature_payload(event))
                        status = "valid"
                    except InvalidSignature:
                        status = "invalid_signature"
        results.append({"sequence": seq, "custodian_id": event["custodian_id"],
                        "signature_status": status})
    complete = all(x["signature_status"] == "valid" for x in results)
    payload = {
        "report_version": "1.0",
        "package_sha256": package_sha256,
        "chain_head_sha256": events[-1]["event_sha256"],
        "registry_sha256": sha256_data(registry),
        "signatures_sha256": sha256_data(signatures),
        "anchor_sha256": sha256_data(anchor),
        "anchored_sequence": anchor["sequence"],
        "all_events_cryptographically_signed": complete,
        "chain_matches_supplied_anchor": True,
        "anchor_independently_authenticated": False,
        "real_world_custodian_identity_verified": False,
        "trusted_timestamp_verified": False,
        "scientific_replication_verified": False,
        "events": results,
        "disclaimer": "Signatures bind enrolled keys to event hashes; external anchor authenticity, custodian identity, timestamps and physical custody require out-of-band verification.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
