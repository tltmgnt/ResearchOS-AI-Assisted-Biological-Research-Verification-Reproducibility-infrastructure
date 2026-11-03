# Phase 22 — Deployment and Monitoring Operations

## Scope

Phase 22 adds **read-only deployment preflight** and **deterministic monitoring alert evaluation**. It does not deploy software, run a daemon, open a network port, collect metrics or authenticate operator declarations. Production authorization remains false in every software-generated report.

## Deployment preflight

Create a JSON configuration without credentials:

```json
{
  "schema_version": "1.0",
  "environment": "staging",
  "release_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "publisher_registry_pin_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "custody_registry_pin_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "external_audit_approval": false,
  "max_artifact_bytes": 100000000
}
```

Replace placeholders with independently authenticated values. Do **not** change `external_audit_approval` to true unless the real approval exists; this is a caller declaration, not authenticated evidence. Run:

```sh
python -m researchos_bio deployment-preflight deployment.json ./artifacts --output preflight-report.json
```

Checks cover Python version, artifact-directory existence and symlink rejection, nonplaceholder release commit, nonplaceholder publisher and custody registry pins, and declared external audit approval. Exit 0 means these *local checks* pass; exit 2 means at least one check fails; exit 1 means malformed inputs. Passing is **not production approval**.

## Monitoring snapshot

An external operator/collector supplies a JSON object:

```json
{
  "schema_version": "1.0",
  "sample_id": "staging-2026-11-03T12:00Z",
  "verification_attempts": 12,
  "verification_failures": 0,
  "rejected_archive_inputs": 0,
  "unexpected_process_restarts": 0,
  "last_success_age_seconds": 15
}
```

```sh
python -m researchos_bio monitoring-snapshot snapshot.json --output monitoring-report.json
```

Rules: any verification failure or rejected archive is a warning; unexpected process restarts or a last successful verification older than 3600 seconds are critical; no verification activity is a warning. Exit 2 indicates a critical alert; exit 0 indicates no critical alert (warnings may still be present). Exit 1 indicates invalid input. The tool does not collect or authenticate metrics.

## Deployment runbook

1. Pin a reviewed release commit and lock dependencies. Run CI, unit tests, and the Phase 21 auditor acceptance suite.
2. Obtain genuine, independently authenticated registry pins and publisher checkpoint evidence.
3. Obtain independent security sign-off and external auditor approval. Do not treat a boolean config flag as sufficient.
4. Provision a restricted service account, read-only evidence inputs, least-privilege filesystem permissions, encrypted storage and TLS termination.
5. Apply network isolation, secrets management, request limits, centralized audit logging and approved PHI/PII data handling.
6. Run preflight against the staging artifact directory. Review every check and retain the report and its SHA-256.
7. Exercise positive and negative verification cases and manually verify monitoring and paging.
8. Configure an external metrics collector to supply monitoring snapshots and alert on critical conditions.
9. Perform staged deployment, rollback exercise, backup/restore validation, and incident response drill.
10. Have a separately authorized operator sign production approval and record immutable deployment evidence.

## Outstanding production blockers

No production deployment automation, external telemetry collector, alert routing, secrets integration, trusted timestamps, audit approval authentication, security certification, backup/restore automation or disaster recovery verification is included. Preflight and monitoring are useful offline controls but **not** proof of production readiness or biological reproducibility.
