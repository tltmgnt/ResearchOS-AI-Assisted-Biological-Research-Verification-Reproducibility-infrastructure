# Phase 18 — Custody Trust Registry Lifecycle and Revocation

## Goal

Verify a versioned, hash-linked history of custodian public-key registries and assess each signed custody event against an explicitly assigned historical registry revision. This distinguishes a key's historical administrative status from its current status.

## Snapshot format

```json
{
  "schema_version": "1.0",
  "revision": 1,
  "previous_snapshot_sha256": "<64 zeros for genesis>",
  "effective_at": "2026-11-03T10:00:00Z",
  "change_reason": "initial enrollment",
  "registry": {
    "schema_version": "1.0",
    "keys": [
      {
        "key_id": "custody-key-1",
        "custodian_id": "operator-1",
        "approved": true,
        "revoked": false,
        "public_key_b64": "<Ed25519 raw public key, base64>"
      }
    ]
  },
  "snapshot_sha256": "<canonical SHA-256 of snapshot excluding this field>"
}
```

Each successive revision increments `revision` by one and binds `previous_snapshot_sha256` to the preceding snapshot. A key ID cannot be reassigned to a different public key or custodian, and a revoked key ID cannot be reactivated; rotation requires a new key ID. Changes should have a meaningful reason and a separately authenticated effective timestamp.

## Per-event assignments

```json
[{"sequence":1,"registry_revision":1},{"sequence":2,"registry_revision":2}]
```

Every custody event must be assigned exactly one registry revision. The verifier checks the complete event hash chain, validates signatures under the assigned registry revision, checks a supplied custody anchor, and checks the complete registry history against an externally supplied pinned head hash.

```sh
python -m researchos_bio verify-registry-lifecycle snapshots.json events.json signatures.json PACKAGE_SHA256 custody-anchor.json assignments.json PINNED_REGISTRY_HEAD_SHA256 --output lifecycle-report.json
```

## Interpretation and limitations

A signature made while a key was approved can remain valid under its assigned historical snapshot even if that key is now revoked. A signature assigned to a revision where the key is revoked is rejected. **This is conditional historical policy evaluation, not proof that the event actually occurred at that revision.**

The tool does not independently verify revision effective times, enrollment authority, event timestamps, or that a registry assignment was chosen contemporaneously. An attacker controlling all inputs can fabricate a self-consistent history. For a defensible custody trail, independently timestamp and authenticate each registry revision, each event-to-revision assignment, the registry head and the custody anchor in a separate append-only service. Investigate compromised keys according to an external incident-response policy, including retroactive distrust where justified.

A verified key history does not establish physical custody, evaluator independence, or biological replication.
