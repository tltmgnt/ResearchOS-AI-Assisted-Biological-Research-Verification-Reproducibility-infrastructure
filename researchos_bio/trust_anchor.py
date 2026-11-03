"""Phase 19: portable, signed trust-anchor checkpoint verification.

Publication is external. This module checks explicitly supplied signatures and
pinned publisher registry, not network transparency or trusted timestamps.
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import RecordError, canonical_bytes, sha256_data


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError(f"{name} must be lowercase SHA-256")
    return value


def _b64(value: Any, length: int, name: str) -> bytes:
    if not isinstance(value, str):
        raise RecordError(f"{name} must be base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RecordError(f"{name} must be valid base64") from exc
    if len(decoded) != length:
        raise RecordError(f"{name} must decode to {length} bytes")
    return decoded


def anchor_payload(checkpoint: dict[str, Any]) -> bytes:
    """Domain-separated canonical bytes to sign with a publisher Ed25519 key."""
    if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != "1.0":
        raise RecordError("checkpoint schema_version must be 1.0")
    for name in ("package_sha256", "custody_head_sha256", "registry_head_sha256"):
        _sha(checkpoint.get(name), name)
    if type(checkpoint.get("custody_sequence")) is not int or checkpoint["custody_sequence"] < 1:
        raise RecordError("custody_sequence must be positive integer")
    if not isinstance(checkpoint.get("checkpoint_id"), str) or not checkpoint["checkpoint_id"].strip():
        raise RecordError("checkpoint_id must be nonempty")
    if not isinstance(checkpoint.get("declared_at"), str) or not checkpoint["declared_at"].strip():
        raise RecordError("declared_at must be nonempty")
    return canonical_bytes({"domain": "researchos.external-trust-anchor.v1",
                            "checkpoint": checkpoint})


def verify_published_anchor(
    checkpoint: dict[str, Any],
    attestations: list[dict[str, Any]],
    publisher_registry: dict[str, Any],
    pinned_publisher_registry_sha256: str,
    expected_package_sha256: str,
    expected_custody_head_sha256: str,
    expected_registry_head_sha256: str,
    minimum_publishers: int = 2,
) -> dict[str, Any]:
    """Verify publisher signatures and exact checkpoint bindings.

    A registry hash must be independently authenticated to establish trust.
    Publisher organizations are configured identifiers, not verified identities.
    """
    payload_bytes = anchor_payload(checkpoint)
    _sha(pinned_publisher_registry_sha256, "pinned_publisher_registry_sha256")
    for name, value in (("expected_package_sha256", expected_package_sha256),
                        ("expected_custody_head_sha256", expected_custody_head_sha256),
                        ("expected_registry_head_sha256", expected_registry_head_sha256)):
        _sha(value, name)
    if (checkpoint["package_sha256"] != expected_package_sha256
            or checkpoint["custody_head_sha256"] != expected_custody_head_sha256
            or checkpoint["registry_head_sha256"] != expected_registry_head_sha256):
        raise RecordError("checkpoint not bound to expected package, custody and registry heads")
    if not isinstance(publisher_registry, dict) or publisher_registry.get("schema_version") != "1.0":
        raise RecordError("publisher registry schema_version must be 1.0")
    if sha256_data(publisher_registry) != pinned_publisher_registry_sha256:
        raise RecordError("publisher registry does not match independently pinned digest")
    if type(minimum_publishers) is not int or minimum_publishers < 2:
        raise RecordError("minimum_publishers must be integer >= 2")
    keys = publisher_registry.get("keys")
    if not isinstance(keys, list) or not isinstance(attestations, list):
        raise RecordError("publisher keys and attestations must be arrays")
    keymap = {}
    for key in keys:
        if not isinstance(key, dict):
            raise RecordError("publisher key must be object")
        kid, publisher, org = key.get("key_id"), key.get("publisher_id"), key.get("organization_id")
        if any(not isinstance(v, str) or not v.strip() for v in (kid, publisher, org)):
            raise RecordError("publisher key ID, publisher and organization must be nonempty")
        if kid in keymap:
            raise RecordError("duplicate publisher key ID")
        if type(key.get("approved")) is not bool or type(key.get("revoked")) is not bool:
            raise RecordError("approved/revoked must be booleans")
        keymap[kid] = (publisher, org, key["approved"], key["revoked"],
                       Ed25519PublicKey.from_public_bytes(
                           _b64(key.get("public_key_b64"), 32, "public_key_b64")))
    seen_keys, seen_publishers = set(), set()
    results, valid_orgs = [], set()
    for attestation in attestations:
        if not isinstance(attestation, dict):
            raise RecordError("attestation must be object")
        kid = attestation.get("key_id")
        if not isinstance(kid, str) or not kid.strip() or kid in seen_keys:
            raise RecordError("attestation key IDs must be unique nonempty strings")
        seen_keys.add(kid)
        status = "untrusted_key"
        publisher = None
        org = None
        if kid in keymap:
            publisher, org, approved, revoked, public = keymap[kid]
            if publisher in seen_publishers:
                raise RecordError("duplicate publisher identity")
            seen_publishers.add(publisher)
            if revoked:
                status = "revoked_key"
            elif not approved:
                status = "unapproved_key"
            else:
                signature = _b64(attestation.get("signature_b64"), 64, "signature_b64")
                try:
                    public.verify(signature, payload_bytes)
                    status = "valid"
                    valid_orgs.add(org)
                except InvalidSignature:
                    status = "invalid_signature"
        results.append({"key_id": kid, "publisher_id": publisher,
                        "organization_id": org, "signature_status": status})
    accepted = (len(valid_orgs) >= minimum_publishers and
                all(x["signature_status"] == "valid" for x in results))
    report = {
        "report_version": "1.0",
        "checkpoint_sha256": sha256_data(checkpoint),
        "publisher_registry_sha256": sha256_data(publisher_registry),
        "attestations_sha256": sha256_data(attestations),
        "valid_publisher_organizations": len(valid_orgs),
        "minimum_publishers": minimum_publishers,
        "cryptographic_publisher_quorum_met": accepted,
        "independent_publication_confirmed": False,
        "real_world_publisher_identity_verified": False,
        "trusted_publication_timestamp_verified": False,
        "scientific_replication_verified": False,
        "attestations": results,
        "disclaimer": "Signatures verify enrolled publisher keys only. Independent registry authentication, real-world organizations, public append-only posting and trusted timestamps require out-of-band evidence.",
    }
    return {**report, "report_sha256": sha256_data(report)}
