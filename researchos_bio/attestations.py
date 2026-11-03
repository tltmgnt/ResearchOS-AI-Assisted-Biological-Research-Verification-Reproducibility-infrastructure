"""Ed25519 review attestations verified against an explicit local trust registry.

A valid signature authenticates possession of a private key for a configured
reviewer ID; it does not prove scientific correctness or reviewer independence.
"""
from __future__ import annotations

import base64
import binascii
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .core import RecordError, canonical_bytes, sha256_data, validate_record
from .reviews import evaluate_reviews


def _b64(value: Any, label: str, length: int) -> bytes:
    if not isinstance(value, str):
        raise RecordError(f"{label} must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RecordError(f"{label} is invalid base64") from exc
    if len(raw) != length:
        raise RecordError(f"{label} must decode to {length} bytes")
    return raw


def attestation_payload(record: dict[str, Any], review: dict[str, Any]) -> bytes:
    """Stable, domain-separated bytes to sign for exactly one review."""
    validate_record(record)
    if not isinstance(review, dict):
        raise RecordError("review must be an object")
    return canonical_bytes({
        "domain": "researchos.review-attestation.v1",
        "record_sha256": sha256_data(record),
        "review": review,
    })


def verify_attestations(
    record: dict[str, Any],
    review_bundle: dict[str, Any],
    trust_registry: dict[str, Any],
    attestations: dict[str, Any],
) -> dict[str, Any]:
    """Verify all review signatures against explicitly provisioned public keys.

    Trust registry: {"schema_version":"1.0","keys":[
      {"key_id":"lab-key","reviewer_id":"reviewer-a","public_key_b64":"..."}]}
    Attestations: {"schema_version":"1.0","signatures":[
      {"review_id":"review-1","key_id":"lab-key","signature_b64":"..."}]}

    No untrusted input can enroll a new trusted key. Missing or invalid
    signatures are reported and never accepted as verified.
    """
    review_report = evaluate_reviews(record, review_bundle)
    if not isinstance(trust_registry, dict) or trust_registry.get("schema_version") != "1.0":
        raise RecordError("trust registry schema_version must be 1.0")
    if not isinstance(attestations, dict) or attestations.get("schema_version") != "1.0":
        raise RecordError("attestations schema_version must be 1.0")
    keys = trust_registry.get("keys")
    signatures = attestations.get("signatures")
    if not isinstance(keys, list) or not isinstance(signatures, list):
        raise RecordError("keys and signatures must be arrays")
    key_map: dict[str, tuple[str, Ed25519PublicKey]] = {}
    for entry in keys:
        if not isinstance(entry, dict):
            raise RecordError("trust key must be an object")
        kid, owner = entry.get("key_id"), entry.get("reviewer_id")
        if not isinstance(kid, str) or not kid.strip() or not isinstance(owner, str) or not owner.strip():
            raise RecordError("key_id and reviewer_id must be nonempty strings")
        if kid in key_map:
            raise RecordError("duplicate trusted key ID")
        key_map[kid] = (owner, Ed25519PublicKey.from_public_bytes(
            _b64(entry.get("public_key_b64"), "public_key_b64", 32)))
    sig_map: dict[str, dict[str, Any]] = {}
    for entry in signatures:
        if not isinstance(entry, dict):
            raise RecordError("signature entry must be an object")
        rid, kid = entry.get("review_id"), entry.get("key_id")
        if not isinstance(rid, str) or not rid.strip() or not isinstance(kid, str) or not kid.strip():
            raise RecordError("signature review_id and key_id must be nonempty strings")
        if rid in sig_map:
            raise RecordError("duplicate attestation review ID")
        sig_map[rid] = entry
    reviews = {item["review_id"]: item for item in review_bundle["reviews"]}
    if set(sig_map) - set(reviews):
        raise RecordError("signature references unknown review")
    results = []
    for rid in sorted(reviews):
        review = reviews[rid]
        signature = sig_map.get(rid)
        status = "missing"
        if signature is not None:
            key_id = signature["key_id"]
            if key_id not in key_map:
                status = "untrusted_key"
            elif key_map[key_id][0] != review["reviewer_id"]:
                status = "reviewer_key_mismatch"
            else:
                raw_sig = _b64(signature.get("signature_b64"), "signature_b64", 64)
                try:
                    key_map[key_id][1].verify(raw_sig, attestation_payload(record, review))
                    status = "valid"
                except InvalidSignature:
                    status = "invalid_signature"
        results.append({
            "review_id": rid, "reviewer_id": review["reviewer_id"],
            "signature_status": status,
            "cryptographically_attested": status == "valid",
            "identity_independently_verified": False,
            "independent_replication_verified": False,
        })
    payload = {
        "report_version": "1.0", "record_sha256": sha256_data(record),
        "review_bundle_sha256": sha256_data(review_bundle),
        "trust_registry_sha256": sha256_data(trust_registry),
        "attestations_sha256": sha256_data(attestations),
        "all_reviews_signed": bool(results) and all(x["cryptographically_attested"] for x in results),
        "reviews": results,
        "disclaimer": "Signature validity is not evidence of biological truth, external identity verification or independent replication.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
