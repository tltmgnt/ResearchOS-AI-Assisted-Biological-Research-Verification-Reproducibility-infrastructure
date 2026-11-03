# Phase 19 — Signed External Trust-Anchor Checkpoints

## Purpose

Create a portable checkpoint format and verify signatures from multiple configured publishing organizations. This is **offline verification of supplied publisher attestations**, not an integrated external publication service.

## Checkpoint format

```json
{
  "schema_version": "1.0",
  "checkpoint_id": "external-publication-2026-001",
  "declared_at": "2026-11-03T11:00:00Z",
  "package_sha256": "<64 lowercase hex characters>",
  "custody_head_sha256": "<64 lowercase hex characters>",
  "registry_head_sha256": "<64 lowercase hex characters>",
  "custody_sequence": 2
}
```

Publisher signatures are Ed25519 over canonical JSON:

```json
{"domain":"researchos.external-trust-anchor.v1","checkpoint":{ "...": "exact checkpoint object" }}
```

The publisher registry has `schema_version: "1.0"` and a `keys` array. Each key contains `key_id`, `publisher_id`, `organization_id`, `approved`, `revoked` and `public_key_b64`. Attestations are an array of `{"key_id":"...","signature_b64":"..."}`. Each publisher ID and key ID may appear once. The default policy requires valid signatures from at least **two distinct configured organizations**.

## Verification

```sh
python -m researchos_bio verify-published-anchor checkpoint.json attestations.json publisher-registry.json PINNED_PUBLISHER_REGISTRY_SHA256 EXPECTED_PACKAGE_SHA256 EXPECTED_CUSTODY_HEAD_SHA256 EXPECTED_REGISTRY_HEAD_SHA256 --minimum-publishers 2 --output publication-report.json
```

The registry digest and expected package/custody/registry heads must be obtained through independently authenticated channels. The verifier rejects a registry that does not match the pinned digest or a checkpoint that does not match the expected heads, and fails the administrative quorum when signatures are missing, invalid, revoked or from too few organizations.

## External publication workflow

1. Verify the Phase 16 audit ZIP and Phase 18 registry history.
2. Freeze the exact checkpoint bytes and compute its digest.
3. Obtain Ed25519 attestations from independently governed publisher keys.
4. Publish the checkpoint, attestations, and digest in one or more independently controlled append-only systems.
5. Authenticate the publisher registry digest and checkpoint from an external trust channel before using this CLI.
6. Archive publication receipts, transparency inclusion proofs, independently verified timestamps and external source URLs separately.

**Not implemented:** posting to an external transparency service, fetching or validating publication receipts, trusted timestamp verification, legal identity checks, or proof that the configured organizations are genuinely independent. A self-consistent signed checkpoint does not establish scientific validity or biological replication.
