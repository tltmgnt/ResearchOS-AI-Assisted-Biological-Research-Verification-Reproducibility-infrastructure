# Phase 21 — External Auditor Acceptance Protocol

## Objective

Provide a reproducible, offline acceptance suite for an independent auditor to execute using independently supplied inputs. The tool evaluates **software behavior**, not whether an external auditor actually participated.

## Six mandatory scenarios

| Scenario | Expected outcome |
| --- | --- |
| `valid_audit_package` | Verified |
| `tampered_audit_package` | Rejected |
| `valid_publisher_quorum` | Verified |
| `tampered_publisher_signature` | Rejected |
| `wrong_publisher_registry_pin` | Rejected |
| `wrong_checkpoint_binding` | Rejected |

The six scenario IDs and their expected outcomes are fixed in code. A suite cannot remove, duplicate or invert them. Archive paths must be simple filenames inside the supplied fixture directory; arbitrary command execution and network access are not supported.

## Input contract

A suite is JSON with `schema_version: "1.0"`, a nonempty `suite_id` and exactly six `cases`:

```json
{
  "schema_version": "1.0",
  "suite_id": "external-audit-2026-001",
  "cases": [
    {
      "scenario": "valid_audit_package",
      "expect_success": true,
      "fixture": {"path": "valid-audit.zip", "expected_sha256": "<SHA-256>"}
    }
  ]
}
```

The example above shows the shape of **one case**, not a complete suite. For `tampered_audit_package`, supply a tampered ZIP or an intentionally wrong digest. For publisher cases, the `fixture` object must contain `checkpoint`, `attestations`, `publisher_registry`, `pinned_publisher_registry_sha256`, `expected_package_sha256`, `expected_custody_head_sha256` and `expected_registry_head_sha256`, matching the Phase 19 verifier.

```sh
python -m researchos_bio auditor-acceptance suite.json ./fixtures --output acceptance-report.json
```

The command returns exit status 0 if all six expected outcomes occur, 2 if an acceptance scenario fails, and 1 on malformed suite or runtime input. The report is deterministic for identical fixtures and records `suite_sha256`, case-level outcomes and `report_sha256`.

## External auditor sign-off checklist

1. Obtain the exact release commit and independently build the project in a controlled environment.
2. Obtain authentic, independently authenticated registry pins and package digests from outside the implementation team.
3. Inspect fixture provenance and ensure negative cases exercise the intended fault, not merely malformed unrelated input.
4. Execute the six acceptance cases, archive the input suite, fixture digests, report and command logs.
5. Independently assess key custody, publisher organization independence, timestamps and transparency inclusion evidence.
6. Sign a separate audit decision using the external audit governance process, documenting scope, exclusions and findings.
7. Refuse production approval if any required evidence or external authentication is missing.

## Limits

The acceptance runner deliberately reports `independent_auditor_executed: false` and `external_auditor_approved: false`. It cannot determine whether a human external auditor executed the tests. A negative scenario is currently satisfied by **any** rejection, so the auditor must manually confirm the failure reason matches the intended attack. This suite does not establish physical custody, identity, biological reproducibility or an independent penetration-test sign-off.
