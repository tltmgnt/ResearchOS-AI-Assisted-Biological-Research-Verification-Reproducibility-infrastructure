# Phase 14 — Independent Evaluation Dossier and Evidence Traceability

## Purpose

Produce a single **administrative evaluation dossier** linking the Phase 9 pilot gate, Phase 12 paired performance comparison, Phase 13 missing-data/statistical report, and Phase 10 signed evaluator audit. All reports must contain valid canonical SHA-256 fingerprints and mutually consistent references.

## Inputs

The command consumes five JSON files:

1. `pilot-report.json`: complete Phase 9 pilot readiness report.
2. `comparison-report.json`: complete Phase 12 paired timing comparison.
3. `statistics-report.json`: complete Phase 13 statistics report, bound to the supplied comparison, plan and observations.
4. `audit-report.json`: complete Phase 10 external audit report bound to the supplied pilot report.
5. `source-evidence.json`: inventory of **declared** source evidence digests.

Evidence inventory example:

```json
[
  {"evidence_id":"timing-export-1","role":"raw_timing","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
  {"evidence_id":"protocol-registration-1","role":"preregistration","sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
]
```

Supported roles: `raw_timing`, `preregistration`, `case_accounting`, `reviewer_identity`, `protocol_deviation`, `audit_log`.

```sh
python -m researchos_bio assemble-evaluation-dossier \
  pilot-report.json comparison-report.json statistics-report.json \
  audit-report.json source-evidence.json --output dossier.json
```

The administrative dossier completion gate requires a passing pilot, accepted signed audit, adequate paired sample size, reconciled case counts, no missing or excluded cases, and a nonempty source-evidence inventory. The report includes case accounting, timing results, interval, source digest declarations and hashes of every input report.

## Verification limits

The current dossier verifies **report consistency and declared digests**, not the underlying source artifact bytes. An evaluator must independently retrieve each original source artifact, calculate SHA-256, authenticate the custodian and timestamp, check reviewer independence, and verify the original preregistration and protocol adherence. Signed audit reports attest to configured keys, not real-world identity.

The administrative gate is intentionally strict about missing/excluded cases. A noncomplete dossier may still contain useful scientifically reportable results if deviations are transparently explained; it is not automatically evidence of scientific failure. Conversely, a complete dossier is **not** proof of scientific replication, causality or independent validation.
