# Phase 10 — Signed External Audit Handoff

This feature records signed decisions by **operator-enrolled external evaluators** over a specific Phase 9 pilot report. It is not scientific certification or an identity-verification service.

## Inputs

- `pilot-report.json`: full Phase 9 report including `report_sha256`.
- `audit-trust-registry.json`: operator-authenticated public keys and approval/revocation declarations.
- `audit-bundle.json`: reviewer decisions signed over a domain-separated canonical payload binding the exact pilot report SHA-256 and decision object.

Trust registry:

```json
{"schema_version":"1.0","keys":[{"key_id":"audit-key-1","evaluator_id":"evaluator-1","organization_id":"institution-1","approved":true,"revoked":false,"public_key_b64":"<base64 raw Ed25519 public key>"}]}
```

Audit bundle:

```json
{"schema_version":"1.0","pilot_report_sha256":"<canonical SHA-256 of entire pilot report>","decisions":[{"key_id":"audit-key-1","decision":{"decision_id":"decision-1","evaluator_id":"evaluator-1","organization_id":"institution-1","verdict":"approve","reason":"reviewed supplied administrative evidence"},"signature_b64":"<base64 raw Ed25519 signature>"}]}
```

Use `researchos_bio.external_audit.audit_payload(pilot_report, decision)` as the **exact bytes** to sign.

```sh
python -m researchos_bio verify-external-audit pilot-report.json audit-trust-registry.json audit-bundle.json --minimum-organizations 2 --output external-audit-report.json
```

The administrative audit gate requires a passing software pilot, at least two distinct organizations with valid approved signatures, no valid negative decisions, and no invalid audit decisions. Duplicate evaluator decisions, malformed inputs and altered pilot report hashes are rejected. An invalid or revoked signature cannot contribute to quorum.

## Explicit trust limits

A key signature proves possession of a private key only. Registry provenance, enrollment authority, reviewer independence, organizational affiliation, credential proofing, timing of revocation, real-world identity, and biological ground truth must be established separately. A valid signature on a negative verdict vetoes administrative acceptance. No signed decision upgrades a claim to scientifically validated.

## External evaluator checklist

1. Authenticate registry provenance and organizational credentials independently.
2. Check that each reviewer is genuinely independent of the research team and other reviewers.
3. Verify original artifact bytes, experimental protocol, preregistration timing, and raw data.
4. Independently rerun selected experiments and document discrepancies.
5. Archive signed decisions, reasons, timestamps, environment, and input hashes in an externally controlled audit log.
