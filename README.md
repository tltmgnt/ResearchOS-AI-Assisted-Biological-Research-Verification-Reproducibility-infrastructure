# ResearchOS — Biological Research Verification & Reproducibility Infrastructure

ResearchOS is an early-stage, **model-agnostic research-assurance prototype** for documenting, checking, and independently reviewing claims produced during AI-assisted biological research. It treats generated assertions as **candidates**, not validated biological knowledge.

**Current scope:** lightweight Python records for claims, traceable evidence, experiment/protocol metadata, deterministic consistency checks, and verifiable evaluation reports. The software does **not** yet validate experimental biology, execute independent reproductions, establish scientific truth, demonstrate improved performance, or provide clinical decision support.

## Quick start

Requires Python 3.11+. Phase 4 Ed25519 verification requires the `cryptography` package. Install with `python -m pip install -e .`.

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

## Phase 4: cryptographic reviewer attestations

Ed25519 signatures authenticate a review's exact JSON contents and its bound source record hash against an **operator-provisioned public-key trust registry**. Signatures are domain-separated (`researchos.review-attestation.v1`) and use canonical JSON bytes.

```sh
python -m researchos_bio verify-attestations record.json review-bundle.json trusted-keys.json signatures.json --output signature-report.json
```

`trusted-keys.json` must be provisioned separately by the trusted operator:

```json
{"schema_version":"1.0","keys":[{"key_id":"key-1","reviewer_id":"reviewer-1","public_key_b64":"<base64-encoded raw 32-byte Ed25519 public key>"}]}
```

`signatures.json` format:

```json
{"schema_version":"1.0","signatures":[{"review_id":"review-1","key_id":"key-1","signature_b64":"<base64-encoded raw 64-byte Ed25519 signature>"}]}
```

A signer signs the output of `attestation_payload(record, review)` from `researchos_bio.attestations` using their securely stored Ed25519 private key. **Never commit private keys or sensitive biological/patient data.** The CLI returns 0 when all reviews have valid trusted signatures, 2 for missing/invalid/untrusted signatures, and 1 for malformed input. The report fingerprints the trust registry and signatures to support later replay.

**Trust boundary:** the registry must be authenticated and distributed out-of-band. Signature verification proves possession of a corresponding private key, **not** real-world reviewer identity, absence of collusion, experimental reproducibility, or biological validity. Key rotation, revocation, certificate chains and independent identity proofing are not yet implemented.

## Integrated assurance assessment (new)

The `assess` command composes four existing verification layers into one **conservative advisory** claim-level gate. It requires **real local evidence files**, a one-protocol manifest, reviewer declarations, an **externally provisioned** trusted public-key registry, and review signatures. No default/demo key is trusted by the software.

```sh
python -m researchos_bio assess record.json manifest.json review-bundle.json trusted-keys.json signatures.json \\
  --root ./local-artifacts --output assurance-report.json
```

The record, manifest, review bundle, registry and signatures follow the JSON contracts described above. The command does not generate signatures or provision trust. Exit status **0** means every claim is **ready for manual adjudication**, **2** means at least one claim needs review, needs evidence or is contested, and **1** means an input or I/O error.

The deterministic report includes the source hashes and hashes of all four layer reports. It emits one of:

| Advisory gate | Meaning |
| --- | --- |
| `needs_evidence` | Missing, uncertain, or locally mismatched evidence |
| `needs_review` | No self-declared eligible **signed** review, reviewer/operator overlap, or an unsigned review |
| `contested` | A recorded failed check or unresolved review challenge (including unsigned challenges) |
| `ready_for_manual_adjudication` | Local artifacts match, passing evidence is recorded and signed, self-declared eligible reviews exist, with no unresolved challenges |

**No state is promoted automatically.** In particular, `ready_for_manual_adjudication` does **not** imply experimental reproduction, reviewer identity, independence, correctness of scientific methods or biological validity. Even a signed, independent-looking reviewer may be colluding or misrepresenting the work. An unsigned challenge is deliberately escalated for manual adjudication, not treated as trustworthy evidence of failure.

**Threat boundaries:** a malicious party may fabricate evidence, sign misleading reviews with their own trusted key, or manipulate external identity information. This layer authenticates bytes and checks declared metadata, **not scientific truth**. Key management/revocation, biological assay adapters, external identity proofing, provenance-standard interoperability and objective replication benchmarks remain future work. Do not use this prototype for clinical decisions.

### Safety and regression tests

`python -m unittest discover -s tests -v` includes synthetic adversarial cases for artifact tampering, unsigned/invalid reviewer signatures, conflicts of interest, shared operators, challenged claims, wrong protocol bindings, and record tampering. They are software tests only, not evidence of biological validity.

## Next implementation milestones

1. Add content-addressed artifact ingestion and access controls (local hash verification now implemented).
2. Protocol, environment, toolchain, random seed and dataset manifests.
3. External identity / key-lifecycle verification and evidence independence audit workflow (signed attestations now implemented).
4. Preregistered statistical/biological assay validation adapters and ground-truth benchmarks.
5. Matched evaluation against manual and unstructured AI-assisted research workflows.

## License

Apache License 2.0; see [`LICENSE`](LICENSE).
