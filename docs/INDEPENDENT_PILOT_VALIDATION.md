# Phase 23 — Independent Pilot Validation

## Objective

Link the Phase 14 evaluation dossier, Phase 16 verified audit package, Phase 21 auditor acceptance report and a pilot evidence manifest into a deterministic **documentary** validation report. The gate checks evidence references and administrative claims, but cannot verify actual independent execution.

## Input manifest

Provide `pilot-evidence.json` with the following fields:

```json
{
  "schema_version": "1.0",
  "pilot_id": "external-pilot-001",
  "dossier_sha256": "<dossier report_sha256>",
  "package_report_sha256": "<ZIP verification report_sha256>",
  "auditor_acceptance_sha256": "<acceptance report_sha256>",
  "audit_package_sha256": "<verified ZIP SHA-256>",
  "external_operator_id": "operator-as-enrolled",
  "external_organization_id": "organization-as-enrolled",
  "operator_affiliation_declaration": "unknown",
  "protocol_registration_sha256": "<SHA-256>",
  "raw_observations_sha256": "<SHA-256>",
  "signed_review_artifact_sha256": "<SHA-256>",
  "external_publication_receipt_sha256": "<SHA-256>",
  "independent_signoff_declared": false
}
```

Replace placeholders with lowercase 64-character SHA-256 values. For real evidence, obtain each digest from independently preserved documents. A declaration of `independent` or a true sign-off flag must be backed by out-of-band human and cryptographic checks; the CLI does not authenticate them.

```sh
python -m researchos_bio validate-independent-pilot dossier.json package-verification.json acceptance-report.json pilot-evidence.json --output pilot-validation.json
```

Exit 0 indicates all documentary checks pass; 2 means one or more checks fail; 1 means malformed or inconsistent input.

## Documentary gate

The gate requires a complete administrative dossier, source bytes marked verified in a fingerprinted package report, a passing fingerprinted auditor software acceptance report, an `independent` operator declaration, a declared sign-off, and nonzero fingerprints for protocol registration, raw observations, signed review and external publication receipt. It rejects tampered reports, broken cross-report links, missing fields and invalid digests.

The report **always** states `independent_execution_verified: false`, `independent_signoff_cryptographically_verified: false`, `external_publication_receipt_verified: false`, `biological_replication_verified: false` and `production_release_authorized: false`. A passing documentary gate is not an independent validation certificate.

## Required external pilot work

1. Preregister protocol, case selection, metrics, statistical analysis and acceptance thresholds before collecting observations.
2. Engage an auditor and an operating organization independent of the implementation team; authenticate their legal identity and key custody outside ResearchOS.
3. Run the software on independently controlled infrastructure with a fixed release commit and immutable source evidence.
4. Retain original timing observations, exclusions, failures, protocol deviations, signed reviewer decisions and source bytes.
5. Recompute the evaluation dossier, ZIP verification and auditor acceptance report without using implementation-team-provided expected results.
6. Obtain an independently timestamped publication receipt and authenticate its inclusion proof.
7. Have independent reviewers sign a substantive acceptance or rejection decision and archive the evidence.
8. Evaluate whether scientific outcomes, usability, performance and data-handling obligations actually satisfy preregistered thresholds.

**Outstanding:** no external operator has been engaged or independently authenticated by this code; no external pilot has been performed by this change; no actual external publication receipt, scientific replication or independent approval is supplied.
