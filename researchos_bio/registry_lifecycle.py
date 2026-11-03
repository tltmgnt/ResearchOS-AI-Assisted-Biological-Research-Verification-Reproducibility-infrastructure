"""Phase 18: hash-linked custody trust-registry snapshots and lifecycle policy.

Registry revision history is verified for internal consistency, not external
authenticity or historical timestamp accuracy.
"""
from __future__ import annotations

from typing import Any

from .core import RecordError, sha256_data
from .signed_custody import verify_signed_custody


def _snapshot(snapshot: Any, previous: str, revision: int) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != "1.0":
        raise RecordError("registry snapshot schema_version must be 1.0")
    if type(snapshot.get("revision")) is not int or snapshot["revision"] != revision:
        raise RecordError("registry revision sequence mismatch")
    if snapshot.get("previous_snapshot_sha256") != previous:
        raise RecordError("registry snapshot chain mismatch")
    if not isinstance(snapshot.get("effective_at"), str) or not snapshot["effective_at"].strip():
        raise RecordError("registry effective_at must be nonempty")
    if not isinstance(snapshot.get("change_reason"), str) or not snapshot["change_reason"].strip():
        raise RecordError("registry change_reason must be nonempty")
    registry = snapshot.get("registry")
    if not isinstance(registry, dict) or registry.get("schema_version") != "1.0":
        raise RecordError("embedded trust registry schema_version must be 1.0")
    keys = registry.get("keys")
    if not isinstance(keys, list):
        raise RecordError("registry keys must be an array")
    seen = set()
    for key in keys:
        if not isinstance(key, dict):
            raise RecordError("registry key must be an object")
        kid = key.get("key_id")
        if not isinstance(kid, str) or not kid.strip() or kid in seen:
            raise RecordError("registry key IDs must be unique and nonempty")
        seen.add(kid)
        if not isinstance(key.get("custodian_id"), str) or not key["custodian_id"].strip():
            raise RecordError("registry custodian_id must be nonempty")
        if type(key.get("approved")) is not bool or type(key.get("revoked")) is not bool:
            raise RecordError("registry approved/revoked must be booleans")
    expected = sha256_data({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    if snapshot.get("snapshot_sha256") != expected:
        raise RecordError("registry snapshot fingerprint mismatch")
    return registry


def verify_registry_lifecycle(snapshots: list[dict[str, Any]],
                              events: list[dict[str, Any]],
                              signatures: list[dict[str, Any]],
                              package_sha256: str,
                              anchor: dict[str, Any],
                              assignments: list[dict[str, Any]],
                              pinned_head_sha256: str) -> dict[str, Any]:
    """Verify historical registry linkage and per-event assigned revision.

    Historical acceptance is conditional on authenticated external checkpoints
    and accurate, independently attested registry effective dates.
    """
    if not isinstance(snapshots, list) or not snapshots:
        raise RecordError("nonempty registry snapshot history required")
    if not isinstance(assignments, list) or not isinstance(events, list):
        raise RecordError("assignments and custody events must be arrays")
    previous = "0" * 64
    registries = {}
    key_origins = {}
    for number, snapshot in enumerate(snapshots, 1):
        registry = _snapshot(snapshot, previous, number)
        registries[number] = registry
        for key in registry["keys"]:
            kid = key["key_id"]
            binding = (key["custodian_id"], key.get("public_key_b64"))
            if kid in key_origins and key_origins[kid] != binding:
                raise RecordError("key ID cannot be reassigned or rotated in place")
            key_origins[kid] = binding
        previous = snapshot["snapshot_sha256"]
    if not isinstance(pinned_head_sha256, str) or pinned_head_sha256 != previous:
        raise RecordError("registry history does not match supplied pinned head")
    if len(assignments) != len(events):
        raise RecordError("every custody event requires a registry assignment")
    assignment_map = {}
    for item in assignments:
        if not isinstance(item, dict):
            raise RecordError("registry assignment must be an object")
        seq, rev = item.get("sequence"), item.get("registry_revision")
        if type(seq) is not int or type(rev) is not int or seq in assignment_map:
            raise RecordError("registry assignments require unique integer sequence/revision")
        if rev not in registries:
            raise RecordError("assignment refers to unknown registry revision")
        assignment_map[seq] = rev
    if set(assignment_map) != set(range(1, len(events) + 1)):
        raise RecordError("registry assignments must cover all custody events")
    # Reuse the Phase 17 validator once per event under its assigned registry.
    # Each prefix is a valid chain and its final event must have a valid
    # signature under the assigned revision. Earlier events may have been
    # signed under different revisions and are checked separately.
    results = []
    for i, event in enumerate(events, 1):
        revision = assignment_map[i]
        prefix = events[:i]
        selected = [s for s in signatures if isinstance(s, dict) and s.get("sequence") == i]
        prefix_anchor = {"schema_version": "1.0", "package_sha256": package_sha256,
                         "sequence": i, "event_sha256": event.get("event_sha256")}
        # Validate the full chain and signature for this event.
        report = verify_signed_custody(prefix, selected, registries[revision],
                                       package_sha256, prefix_anchor)
        status = report["events"][-1]["signature_status"]
        results.append({"sequence": i, "registry_revision": revision,
                        "signature_status": status})
    # Validate the independently supplied custody checkpoint as well.
    if not isinstance(anchor, dict) or anchor.get("schema_version") != "1.0":
        raise RecordError("custody anchor schema_version must be 1.0")
    seq = anchor.get("sequence")
    if type(seq) is not int or not 1 <= seq <= len(events):
        raise RecordError("custody anchor sequence invalid")
    if anchor.get("package_sha256") != package_sha256 or anchor.get("event_sha256") != events[seq - 1].get("event_sha256"):
        raise RecordError("custody anchor mismatch")
    complete = bool(results) and all(x["signature_status"] == "valid" for x in results)
    payload = {
        "report_version": "1.0",
        "package_sha256": package_sha256,
        "registry_head_sha256": previous,
        "registry_revisions": len(snapshots),
        "custody_anchor_sha256": sha256_data(anchor),
        "assignments_sha256": sha256_data(assignments),
        "all_assigned_signatures_valid": complete,
        "external_registry_head_authenticated": False,
        "historical_registry_timestamps_authenticated": False,
        "real_world_custodian_identity_verified": False,
        "scientific_replication_verified": False,
        "events": results,
        "disclaimer": "Historical signature acceptance is conditional on externally authenticated registry snapshots, revision assignments and timestamps. Hash chains alone do not establish their authenticity.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
