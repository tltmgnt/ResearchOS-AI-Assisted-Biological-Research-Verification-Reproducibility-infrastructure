"""Phase 15: verify actual source bytes and export a portable, deterministic audit ZIP.

Source artifacts must be regular files under a trusted, immutable directory.
Hashes authenticate bytes relative to the declared manifest, not provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any
from zipfile import ZipFile, ZIP_STORED, ZipInfo

from .core import RecordError, canonical_bytes, sha256_data


def _safe_relative(name: Any) -> str:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise RecordError("artifact path must be a nonempty POSIX relative path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in (".", "..") for part in name.split("/")):
        raise RecordError("absolute paths and traversal are forbidden")
    if any(not part for part in name.split("/")) or name.startswith("/") or ":" in name.split("/")[0]:
        raise RecordError("artifact path must be normalized and relative")
    return name


def _digest(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError("sha256 must be 64 lowercase hexadecimal characters")
    return value


def export_verified_audit_package(
    dossier: dict[str, Any],
    source_root: str | Path,
    artifact_paths: dict[str, str],
    destination: str | Path,
    max_file_bytes: int = 100_000_000,
) -> dict[str, Any]:
    """Verify source bytes and write a deterministic, integrity-indexed ZIP.

    This is a local export operation. Do not concurrently modify source files.
    """
    if not isinstance(dossier, dict) or dossier.get("report_version") != "1.0":
        raise RecordError("dossier must be a version 1.0 report")
    if dossier.get("report_sha256") != sha256_data({
        k: v for k, v in dossier.items() if k != "report_sha256"}):
        raise RecordError("dossier report fingerprint mismatch")
    inventory = dossier.get("source_evidence")
    if not isinstance(inventory, list) or not inventory:
        raise RecordError("dossier must include a nonempty source evidence inventory")
    if not isinstance(artifact_paths, dict):
        raise RecordError("artifact_paths must be an object")
    if type(max_file_bytes) is not int or max_file_bytes < 1:
        raise RecordError("max_file_bytes must be positive integer")
    root = Path(source_root).resolve(strict=True)
    if not root.is_dir():
        raise RecordError("source_root must be a directory")
    expected_ids = set()
    for item in inventory:
        if not isinstance(item, dict):
            raise RecordError("source evidence entry must be an object")
        eid = item.get("evidence_id")
        if not isinstance(eid, str) or not eid.strip() or eid in expected_ids:
            raise RecordError("source evidence IDs must be unique nonempty strings")
        _digest(item.get("sha256"))
        expected_ids.add(eid)
    if set(artifact_paths) != expected_ids:
        raise RecordError("artifact_paths must map exactly every source evidence ID")
    content = {}
    manifest = []
    used_paths = set()
    for item in sorted(inventory, key=lambda x: x["evidence_id"]):
        eid = item["evidence_id"]
        rel = _safe_relative(artifact_paths[eid])
        if rel in used_paths:
            raise RecordError("duplicate source path")
        used_paths.add(rel)
        candidate = root
        # Reject symlinks at every path component, including the leaf.
        for part in rel.split("/"):
            candidate = candidate / part
            if candidate.is_symlink():
                raise RecordError("symlink source paths are forbidden")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
            st = resolved.stat()
        except (OSError, ValueError) as exc:
            raise RecordError("artifact must exist inside source_root") from exc
        if not stat.S_ISREG(st.st_mode) or st.st_size > max_file_bytes:
            raise RecordError("artifact must be a regular file within size limit")
        # This is a prototype; concurrent modification remains an external risk.
        data = resolved.read_bytes()
        if len(data) > max_file_bytes or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise RecordError("source artifact bytes do not match declared SHA-256")
        content[rel] = data
        manifest.append({"evidence_id": eid, "path": f"artifacts/{rel}",
                         "role": item["role"], "sha256": item["sha256"],
                         "size_bytes": len(data)})
    index = {
        "package_version": "1.0",
        "dossier_sha256": sha256_data(dossier),
        "artifact_count": len(manifest),
        "artifacts": manifest,
        "source_bytes_verified": True,
        "scientific_replication_verified": False,
        "disclaimer": "Verified bytes match declared digests; provenance, timestamps, reviewer independence and biological validity remain unverified.",
    }
    destination = Path(destination)
    if destination.exists():
        raise RecordError("refusing to overwrite existing audit package")
    # Fixed metadata and sorted names make identical inputs byte-for-byte reproducible.
    entries = {"dossier.json": canonical_bytes(dossier),
               "index.json": canonical_bytes(index)}
    entries.update({f"artifacts/{name}": data for name, data in content.items()})
    with ZipFile(destination, "x", compression=ZIP_STORED) as archive:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {**index, "package_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
