# Phase 24 — Release Candidate and Operational Handoff

## Release status

Phase 24 completes the **proposed implementation roadmap**, not the real-world external acceptance process. The current package version remains `0.1.0`; `1.0.0-rc1` is a **candidate target identifier** in the documentary handoff manifest, not a published GitHub release, PyPI distribution or authorized production version.

## Reproducible handoff gate

```sh
python -m researchos_bio release-handoff release-manifest.json auditor-acceptance.json deployment-preflight.json pilot-validation.json --output release-handoff-report.json
```

The manifest requires:

- `schema_version: "1.0"`, `release_version: "1.0.0-rc1"`, a 40-character lowercase Git commit and nonempty `handoff_owner_id`.
- Exact report SHA-256 links: `auditor_acceptance_report_sha256`, `deployment_preflight_report_sha256` and `independent_pilot_report_sha256`.
- Nonplaceholder `handoff_runbook_sha256` and `rollback_plan_sha256`.
- An `external_evidence` object containing **exactly** these five gates: `independent_security_review`, `independent_auditor_signoff`, `independent_pilot_execution`, `external_publication_receipt`, and `production_operations_approval`. Each gate requires `artifact_sha256` and boolean `declared_approved`.

The gate rejects missing or inconsistent evidence, tampered reports, failing software checks, invalid declarations and missing rollback/runbook references. Exit 0 means the *documentary* candidate gate passed, 2 means a gate failed and 1 means malformed inputs.

**Important:** All external evidence hashes and approval flags are supplied declarations. The software cannot authenticate external signers, publication receipts, pilot execution or organizational independence. The report always records `production_release_authorized: false` and `external_approvals_authenticated: false`, even if every documentary check passes.

## Release handoff checklist

1. **Integrate branch stack:** Review the full stacked PR ancestry and merge all required changes into `main` in the correct order. Verify `main` contains the actual commits. A merged stacked PR is not proof of mainline integration.
2. **Build reproducibly:** Pin the release commit, Python interpreter and dependency hashes. Generate wheel/sdist, SBOM and package SHA-256; verify clean-install behavior.
3. **Run CI:** Execute unit, adversarial and release-candidate workflows against the final integration commit. Preserve logs, dependency versions and results.
4. **Security review:** Resolve outstanding source-file race conditions, memory use, input-depth limits, secrets/PHI handling and independent penetration-test findings. Obtain signed security sign-off.
5. **Auditor acceptance:** Have a genuinely independent auditor execute the Phase 21 acceptance suite using independently authenticated inputs, and sign an auditable decision.
6. **External pilot:** Run the Phase 23 protocol on independently controlled infrastructure with original raw observations, preregistered thresholds, deviation accounting and a substantive independent decision.
7. **Trust anchors:** Authenticate the publisher registry and publish checkpoints to an independent append-only service; verify inclusion receipts and independently sourced timestamps.
8. **Operations:** Complete deployment automation, access controls, monitoring collector, alert routing, incident runbooks, backup/restore and rollback drills.
9. **Final release approval:** Verify all external evidence and obtain an explicit accountable production release authorization; only then create the final version tag and release artifacts.
10. **Handoff:** Transfer custody of release artifacts, runbooks, keys, monitoring dashboards, incident contacts, service ownership and recovery documentation to named operators.

## Release blockers at handoff

- No independently authenticated external auditor acceptance or pilot execution.
- No independent penetration-test sign-off or production security certification.
- No actual independent transparency-log publication and receipt verification.
- No real deployment, live telemetry collection, alert routing or rollback rehearsal.
- The full stacked feature branch chain is not demonstrated to be integrated into `main`.
- No production release authorization or demonstrated scientific replication.

The implementation roadmap's final phase is not equivalent to production acceptance. Keep these blockers open until separately evidenced.
