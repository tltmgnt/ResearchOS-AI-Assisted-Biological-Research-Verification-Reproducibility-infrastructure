# ResearchOS — Biological Research Verification & Reproducibility Infrastructure

ResearchOS is an early-stage, **model-agnostic research-assurance prototype** for documenting, checking, and independently reviewing claims produced during AI-assisted biological research. It treats generated assertions as **candidates**, not validated biological knowledge.

**Current scope:** dependency-free Python records for claims, traceable evidence, experiment/protocol metadata, deterministic consistency checks, and verifiable evaluation reports. The software does **not** yet validate experimental biology, execute independent reproductions, establish scientific truth, demonstrate improved performance, or provide clinical decision support.

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

## Phase 5: reviewer enrollment, key revocation and administrative review quorum

`evaluate-governance` combines the signed review verification of Phase 4 with an **operator-maintained** enrollment/revocation policy. A claim is marked `administrative_review_ready` only when at least two distinct approved organizations have qualifying, cryptographically signed confirmations and there are no unresolved challenges.

```sh
python -m researchos_bio evaluate-governance record.json review-bundle.json trusted-keys.json signatures.json policy.json --output governance-report.json
```

The operator-controlled policy format is:

```json
{
  "schema_version": "1.0",
  "minimum_distinct_organizations": 2,
  "revoked_key_ids": ["revoked-key-id"],
  "enrolled_reviewers": [
    {"reviewer_id": "reviewer-1", "organization_id": "lab-1", "approved": true}
  ]
}
```

A revoked key or unapproved reviewer does not contribute to quorum. Duplicate enrollments and revocation entries are rejected. Distinct organizations count once, regardless of the number of reviewers or signatures. All challenges block readiness. Reports bind to the input policy and records by SHA-256.

**Critical limitations:** enrollment is an operator assertion, not an independently checked identity credential; the revocation list is not time-stamped or externally distributed; colluding organizations may still claim independence. Administrative readiness **never** means independent replication verified or biological claim validated. Trust-registry and policy authenticity, governance authorization, reviewer vetting, independent experimental reproduction and clinical/biological assessment require external controls.

## Phase 6: preregistered numeric reproduction benchmarks

The `evaluate-benchmark` command checks supplied numeric reproduction outcomes against a **frozen, hash-bound plan**. A plan specifies the claim, exact protocol ID, metric, unit, reference value, analysis method, absolute tolerance, and timezone-aware registration timestamp. Outcomes must reference the exact plan SHA-256 and a known evidence ID for each claim.

```sh
python -m researchos_bio evaluate-benchmark record.json benchmark-plan.json outcomes.json --output benchmark-report.json
```

Plan shape:

```json
{
  "schema_version": "1.0",
  "record_sha256": "<canonical source record SHA-256>",
  "registered_at": "2026-11-03T09:00:00Z",
  "comparisons": [{
    "claim_id": "claim-synthetic-1",
    "protocol_id": "synthetic-control-check-v1",
    "metric": "synthetic_signal",
    "unit": "arbitrary_units",
    "analysis_method": "absolute_difference",
    "reference_value": 100,
    "absolute_tolerance": 5
  }]
}
```

Outcomes shape:

```json
{
  "schema_version": "1.0",
  "plan_sha256": "<canonical benchmark plan SHA-256>",
  "results": [{
    "claim_id": "claim-synthetic-1",
    "run_id": "synthetic-run-1",
    "operator_id": "demo-operator",
    "organization_id": "demo-lab",
    "artifact_evidence_id": "ev-01",
    "observed_at": "2026-11-03T12:00:00Z",
    "observed_value": 103
  }]
}
```

The acceptance rule is `abs(observed_value - reference_value) <= absolute_tolerance`, inclusive. Missing, duplicated, out-of-plan, invalid, or nonfinite values are handled explicitly. Exit code 0 means all planned numeric results fall within tolerance, 2 means missing or outside-tolerance results, and 1 means invalid input. **Do not interpret a within-tolerance result as verified biological replication.** Neither the registration timestamp nor source results are authenticated by this module; scientific protocols, independence, raw artifact integrity, statistical appropriateness, and preregistration timing require external audit.

## Phase 7: unified, non-certifying assurance records

`assemble-assurance` **recomputes** all earlier verification layers rather than trusting previously generated reports. It links each claim to file integrity, signed reviewer declarations, governance readiness, and preregistered numerical comparison outcomes. The output includes the SHA-256 fingerprints of all underlying layer reports and a deterministic packet fingerprint.

```sh
python -m researchos_bio assemble-assurance record.json manifest.json ./artifacts review-bundle.json trusted-keys.json signatures.json policy.json benchmark-plan.json outcomes.json --output assurance-report.json
```

An `assurance_packet_complete` flag is set only if the underlying artifacts match, the administrative review quorum is ready, qualifying reviewer declarations have trusted valid signatures, and the benchmark comparison is within its preregistered tolerance. All planned claims must have benchmark entries. Missing or failed checks block completeness. CLI exit code 0 means complete administrative packets, 2 means incomplete packets, and 1 means malformed inputs.

**This is not a scientific validation or certification engine.** The report always states `scientific_validation_performed: false`, `independent_replication_verified: false`, and `scientific_claim_validated: false`. External identity, provenance, preregistration timing, independent experimental execution and domain expert scientific audits remain necessary.

## Next implementation milestones

1. Add content-addressed artifact ingestion and access controls (local hash verification now implemented).
2. Protocol, environment, toolchain, random seed and dataset manifests.
3. Signed reviewer attestations and evidence independence audit workflow.
4. Preregistered statistical/biological assay validation adapters and ground-truth benchmarks.
5. Matched evaluation against manual and unstructured AI-assisted research workflows.

## License

Apache License 2.0; see [`LICENSE`](LICENSE).
