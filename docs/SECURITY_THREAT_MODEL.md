# Phase 20 — Security Threat Model and Hardening

## Scope

Phase 20 hardens Phase 15/16 evidence export and standalone ZIP verification. This is an engineering threat model, **not** a completed independent security audit or penetration test.

| Threat | Security boundary | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Tampered evidence | Source artifact digest | SHA-256 recomputation and exact manifest binding | Declared digest provenance not authenticated |
| Path traversal | ZIP member and source path | Reject absolute, traversal, noncanonical and control-character names | Caller must protect source directory from concurrent mutation |
| ZIP symlink or special file | Archive member type | Reject Unix symlink and nonregular file types | Other archive tooling may behave differently |
| Resource exhaustion | ZIP metadata, members and payload | Configurable max member count, JSON metadata and aggregate uncompressed byte limits | ZIP central-directory parsing and malicious JSON nesting remain bounded by operational process limits |
| ZIP member injection | Archive manifest | Exact member inventory and unique evidence IDs | An attacker with authority to replace expected digest can forge a self-consistent package |
| Publisher key substitution | Signed checkpoint | Independently pinned publisher registry hash and Ed25519 quorum | Pin must be authenticated out of band |
| Registry revision rewrite | Historical trust registry | Hash-linked snapshots and pinned head | Effective dates and revision assignments not independently timestamped |
| Custody forgery | Signed custody events | Domain-separated Ed25519 signatures | Key compromise, coercion, identity spoofing and private-key handling |
| Archive disclosure | Portable source evidence | Operator access controls and approved distribution | ZIP archives are **not encrypted** and may contain sensitive data |

## Hardened CLI

```sh
python -m researchos_bio export-audit-package dossier.json ./evidence paths.json audit.zip --max-file-bytes 100000000 --max-total-bytes 500000000

python -m researchos_bio verify-audit-package audit.zip EXPECTED_SHA256 --max-total-bytes 500000000 --max-members 10000 --max-metadata-bytes 10000000 --output verification.json
```

The export refuses to create a ZIP when aggregate source evidence plus metadata exceeds its limit, and computes the final ZIP digest incrementally. Verification refuses oversized member inventories, oversized metadata, nonregular Unix members, control-character paths, and unsafe path structures before processing evidence contents.

## Remaining pre-production work

- Replace path check + read with descriptor-relative, no-follow opens to mitigate time-of-check/time-of-use races; operate only on immutable evidence snapshots meanwhile.
- Avoid holding all source evidence bytes in memory during ZIP export; stream with bounded aggregate size.
- Limit JSON nesting and total input sizes at the CLI boundary.
- Add fuzzing, dependency scanning, static analysis, SBOM, secret scanning and a formal security review.
- Integrate an independently authenticated transparency log and enforce signed registry-revision assignments.
- Add an explicit threat-model sign-off by a security reviewer independent of the implementation team.
- Define PII/PHI classification, encryption at rest/in transit, retention, redaction and incident response before real biological or human-subject data is used.

**Passing unit tests and CI are not security certification.** The software cannot establish biological reproducibility or real-world custody from metadata alone.
