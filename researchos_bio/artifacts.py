"""Offline artifact integrity and reproducibility manifest checks.

Checks local bytes and declared execution metadata. Does not validate science.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .core import RecordError, sha256_data, validate_record

_HEX = re.compile(r"^[0-9a-f]{64}$")


def _safe_relative_path(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RecordError("artifact path must be a nonempty POSIX relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise RecordError("artifact path must not escape artifact root")
    if ":" in value or "\x00" in value:
        raise RecordError("invalid artifact path")
    return Path(*pure.parts)


def _digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifacts(record: dict[str, Any], manifest: dict[str, Any], root: str | Path) -> dict[str, Any]:
    """Verify that every evidence digest matches an explicitly mapped local file.

    Symlinks are rejected throughout the path to avoid escaping the declared root.
    Missing files and mismatched digests are reported, not silently ignored.
    """
    _, evidence = validate_record(record)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise RecordError("manifest schema_version must be 1.0")
    for field in ("protocol_id", "protocol_version", "software_version", "environment", "random_seed"):
        if field not in manifest:
            raise RecordError(f"manifest missing {field}")
    if not isinstance(manifest["environment"], dict) or not manifest["environment"]:
        raise RecordError("environment must be a nonempty object")
    if not isinstance(manifest["random_seed"], (str, int)) or isinstance(manifest["random_seed"], bool):
        raise RecordError("random_seed must be a string or integer")
    for field in ("protocol_id", "protocol_version", "software_version"):
        if not isinstance(manifest[field], str) or not manifest[field].strip():
            raise RecordError(f"{field} must be a nonempty string")
    if manifest["protocol_version"] != record["protocol_version"] or manifest["software_version"] != record["software_version"]:
        raise RecordError("manifest versions do not match record")
    if not isinstance(manifest.get("artifacts"), list):
        raise RecordError("manifest artifacts must be an array")
    root_path = Path(root).resolve(strict=True)
    if not root_path.is_dir():
        raise RecordError("artifact root must be a directory")
    declared = {}
    for entry in manifest["artifacts"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("evidence_id"), str):
            raise RecordError("artifact entries require evidence_id")
        eid = entry["evidence_id"]
        if eid in declared:
            raise RecordError("duplicate artifact evidence_id")
        declared[eid] = _safe_relative_path(entry.get("path"))
    expected = {item.evidence_id: item for item in evidence}
    if set(declared) != set(expected):
        raise RecordError("manifest must map every evidence item exactly once")
    results = []
    for eid in sorted(expected):
        rel = declared[eid]
        target = root_path
        for part in rel.parts:
            target = target / part
            if target.is_symlink():
                raise RecordError("symlinked artifact paths are not allowed")
        if not target.is_file():
            results.append({"evidence_id": eid, "path": rel.as_posix(), "status": "missing"})
            continue
        actual = _digest_file(target)
        results.append({"evidence_id": eid, "path": rel.as_posix(),
                        "status": "match" if actual == expected[eid].artifact_sha256 else "mismatch",
                        "actual_sha256": actual, "expected_sha256": expected[eid].artifact_sha256})
    payload = {"report_version": "1.0", "record_sha256": sha256_data(record),
               "manifest_sha256": sha256_data(manifest), "artifacts": results,
               "all_artifacts_verified": all(item["status"] == "match" for item in results),
               "disclaimer": "Artifact integrity only; experimental accuracy and independence are not verified."}
    return {**payload, "report_sha256": sha256_data(payload)}
