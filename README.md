# ResearchOS — Biological Research Verification & Reproducibility Infrastructure

ResearchOS is an early-stage, **model-agnostic research-assurance prototype** for documenting, checking, and independently reviewing claims produced during AI-assisted biological research. It treats generated assertions as **candidates**, not validated biological knowledge.

**Current scope:** dependency-free Python records for claims, traceable evidence, experiment/protocol metadata, deterministic consistency checks, and verifiable evaluation reports. The software does **not** yet validate experimental biology, execute independent reproductions, establish scientific truth, demonstrate improved performance, or provide clinical decision support.

## Quick start

Requires Python 3.11+; no third-party runtime dependencies.

```sh
python -m researchos_bio evaluate examples/synthetic_record.json --output report.json
python -m researchos_bio verify examples/synthetic_record.json report.json
python -m unittest discover -s tests -v
```

The synthetic example uses invented inputs and deliberately illustrative artifact hashes. Do not interpret it as verified biological evidence.

## Initial infrastructure

- **Claim/evidence contracts:** unique claim IDs, versioned protocol and software context, provenance URIs, evidence digest fields, operators, timestamps and stated test verdicts.
- **Structural validation:** reject duplicate or dangling IDs, cross-claim links, malformed SHA-256 strings, unknown statuses, timestamp omissions, and invalid independence references.
- **Evidence-state review:** recommend `unverified`, `supported` or `contested` based on recorded checks; preserve the distinction between reports of test success and external scientific verification.
- **Reproducibility:** canonical SHA-256 fingerprints for the source record and deterministic evaluation report, with a command to recompute and compare the report.
- **Independence caution:** same-operator warnings; independence is never automatically verified from self-reported metadata.
- **Audit-friendly CLI:** no network calls; local JSON input/output and deterministic processing.

### Example workflow

```text
AI / human-generated claim
        ↓
Versioned claim and protocol ID
        ↓
Evidence metadata + external artifact digest
        ↓
Record integrity / reference validation
        ↓
Deterministic review recommendation
        ↓
Independent researcher checks sources, protocols and artifacts
        ↓
External replication and domain-specific biological validation (future)
```

### Status and limitations

`recommended_status` is an **advisory metadata assessment**, not an authorized promotion. A passing verdict is a statement in an input record, not a verified fact. Digest fields are syntactically checked, but the prototype does not retrieve source artifacts to confirm their hashes. Neither SHA-256 fingerprints nor same-operator checks prove authorship, independence or experimental accuracy. `verified_report` means reproducibility of the **software's report**, not reproducibility of a biological claim.

The initial state vocabulary reserves `reproduced` and `validated` for downstream independent review; this prototype never automatically assigns them. No biological subject data, patient records, real assay results, or protected health information is supplied.

## Phase 2: local artifact verification

The `verify-artifacts` command verifies the SHA-256 **contents of actual local files**, not just the shape of a declared digest. Provide a JSON manifest containing `schema_version`, `protocol_id`, `protocol_version`, `software_version`, `environment`, `random_seed`, and an `artifacts` array of `{ "evidence_id": "...", "path": "relative/file" }` objects. Every evidence ID must map exactly once. The manifest protocol/software versions must match the claim record.

```sh
python -m researchos_bio verify-artifacts record.json manifest.json --root ./local-artifacts --output artifact-report.json
```

Exit status 0 indicates all artifact hashes match; status 2 indicates missing or mismatched files; status 1 indicates invalid inputs or I/O errors. Paths must be relative to the declared artifact root; traversal and symlinks are rejected. This is an **integrity check**, not proof of independent replication or scientific correctness. A file may be correctly hashed yet scientifically invalid.

## Next implementation milestones

1. Add content-addressed artifact ingestion and access controls (local hash verification now implemented).
2. Protocol, environment, toolchain, random seed and dataset manifests.
3. Signed reviewer attestations and evidence independence audit workflow.
4. Preregistered statistical/biological assay validation adapters and ground-truth benchmarks.
5. Matched evaluation against manual and unstructured AI-assisted research workflows.

## License

Apache License 2.0; see [`LICENSE`](LICENSE).
