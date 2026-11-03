# Phase 17 — Signed Custody and Externally Pinned Chain Heads

## Purpose

Phase 16 custody events are self-declared hash-chain records. Phase 17 adds **Ed25519 signature verification** against an explicitly provisioned trust registry and a supplied externally pinned custody checkpoint. The verifier does not create or distribute private keys.

## Inputs

The `verify-signed-custody` command consumes:

- `events.json`: Phase 16 ordered custody event array.
- `signatures.json`: array of `{"sequence":1,"key_id":"lab-key","signature_b64":"..."}`.
- `registry.json`: approved key registry with `schema_version: "1.0"` and `keys`, each containing `key_id`, `custodian_id`, `approved`, `revoked`, and `public_key_b64`.
- `package_sha256`: the 64-character package digest obtained from an authenticated independent channel.
- `anchor.json`: `{"schema_version":"1.0","package_sha256":"...","sequence":1,"event_sha256":"..."}`.

```sh
python -m researchos_bio verify-signed-custody events.json signatures.json registry.json PACKAGE_SHA256 anchor.json --output custody-verification.json
```

## Signing contract

Each event is signed over canonical JSON with:

```json
{"domain":"researchos.custody-attestation.v1","event_sha256":"...","package_sha256":"...","sequence":1}
```

Use Ed25519 with a securely stored private key corresponding to the custodian's enrolled public key. Signature payloads must match ResearchOS canonical JSON encoding (sorted keys, compact separators). Never put private keys in source control, ZIP packages or chat messages.

## Trust model and limits

The verifier checks the full Phase 16 chain, pinned event hash, package binding, key enrollment, approval and revocation status, custodian-key ownership, and every event's Ed25519 signature. Missing or invalid signatures make the `all_events_cryptographically_signed` gate false.

The anchor and trust registry are **supplied inputs**. The tool does not independently authenticate either one. For genuine independent trust anchoring, publish the checkpoint hash and registry digest in a separately authenticated, append-only system; validate its timestamp and retention policy out of band. Registry revocation status is assessed at verification time, not historical signing time.

A cryptographically valid custody record proves that an enrolled private key signed an event hash. It does **not** prove real-world custodian identity, physical transfer, trusted event time, independent evaluation, or biological reproducibility.
