# Phase 15 — Source-Verified Audit Package Export

## Purpose

Phase 14 inventories **declared** SHA-256 digests. Phase 15 reads actual source files, recomputes SHA-256, and exports a deterministic ZIP containing the evidence bytes, original dossier and a manifest.

## Command

Provide a Phase 14 dossier, a trusted local source directory, a JSON map from each evidence ID to a relative path, and a new ZIP filename.

```json
{"timing-export-1":"raw/timing-export.csv","protocol-registration-1":"protocol/registration.json"}
```

```sh
python -m researchos_bio export-audit-package dossier.json ./evidence artifact-paths.json audit-package.zip --max-file-bytes 100000000
```

The export rejects mismatched hashes, missing or extra mappings, duplicate source paths, absolute paths, traversal, symlink components, nonregular files, files above the configured limit, and attempts to overwrite an existing ZIP. ZIP metadata and member ordering are fixed so identical inputs produce identical bytes. The returned package SHA-256 should be archived independently.

## ZIP layout

- `dossier.json`: canonical full evaluation dossier.
- `index.json`: dossier fingerprint, evidence IDs, relative ZIP paths, source SHA-256, role, size, and explicit verification boundaries.
- `artifacts/...`: verified original evidence bytes, with paths relative to the trusted source root.

## Security and scientific limitations

The export checks actual file bytes against **supplied digests**. It does not authenticate who created the files, when they were collected, or whether the evidence reflects real biological experiments. Verify trust registry provenance and reviewer independence separately.

This prototype reads files after checking their paths. Concurrent replacement or modification of source files (TOCTOU) is not fully prevented. Run it against an immutable, access-controlled source snapshot; enforce operational disk-space limits and scan untrusted evidence before external distribution. The per-file size limit is not an aggregate ZIP size limit. The ZIP contains source files and may contain sensitive data; apply access control, retention rules, and data minimization.

An independent auditor should unpack the ZIP in a sandbox, verify the ZIP SHA-256, recompute every file hash against `index.json`, compare `dossier.json` to the archived Phase 14 report, and authenticate the original data custodian out of band.

**Source byte integrity is not scientific replication or proof of biological validity.**
