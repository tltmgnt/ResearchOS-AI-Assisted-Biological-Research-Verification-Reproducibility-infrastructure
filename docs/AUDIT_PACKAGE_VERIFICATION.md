# Phase 16 — Independent ZIP Verification and Chain of Custody

## Standalone verification

An external auditor needs only the exported Phase 15 ZIP, its independently communicated SHA-256 and a Python environment with ResearchOS installed. No original source directory is required.

```sh
python -m researchos_bio verify-audit-package audit-package.zip <expected-64-character-sha256> --output verification.json
```

The verifier compares the entire ZIP against the expected fingerprint, checks the dossier fingerprint, verifies the index-to-dossier binding, validates the exact ZIP member set, rejects duplicate names, unsafe paths, unexpected entries, encrypted/compressed entries and oversized uncompressed content, and recomputes every evidence file's SHA-256 and size. The verifier reads ZIP members without extracting them to disk.

**Obtain the expected ZIP fingerprint from a separately authenticated channel.** A digest received with an untrusted ZIP does not authenticate the package.

## Hash-linked custody declarations

Each custody event is a JSON object with `custodian_id`, `action`, `timestamp` and `note`. Actions are `created`, `transferred`, `received`, `verified`, or `archived`. Each event is bound to the ZIP fingerprint, numbered, linked to the previous event hash and hashed canonically.

Example `event.json`:

```json
{"custodian_id":"evaluator-1","action":"received","timestamp":"2026-11-03T10:00:00Z","note":"received via controlled handoff"}
```

Initialize `events.json` with `[]`, then:

```sh
python -m researchos_bio append-custody-event events.json event.json <package-sha256> --output next-events.json
```

The append operation verifies the existing chain before creating a new event. Preserve prior copies in an independently controlled immutable log. The software does **not** sign events, validate wall-clock timestamps, prove custodian identity, prevent deletion or replacement of the entire chain, or authenticate the transfer channel.

## Trust and security boundaries

The ZIP verifier establishes that supplied bytes match the authenticated expected ZIP digest and the internal declared source digests. It does not prove that source measurements were collected honestly or that scientific findings replicate. The chain detects modifications relative to an externally anchored known-good event hash, but cannot independently prove a human custody history. For deployment, use independently signed custody events, trusted timestamps, secure key enrollment, immutable storage and an externally anchored chain head.
