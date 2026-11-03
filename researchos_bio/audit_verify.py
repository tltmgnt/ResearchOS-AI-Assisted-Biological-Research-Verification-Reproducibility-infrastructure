"""Phase 16: standalone audit ZIP integrity and hash-linked custody declarations.

Checks do not establish identity, trusted time, or biological truth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from .core import RecordError, sha256_data


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError(f"{name} must be lowercase SHA-256")
    return value


def _load_json(data: bytes, name: str) -> dict[str, Any]:
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise RecordError(f"{name} must be valid UTF-8 JSON") from exc
    if not isinstance(result, dict):
        raise RecordError(f"{name} must be an object")
    return result


def verify_audit_package(path: str | Path, expected_package_sha256: str,
                         max_total_bytes: int = 500_000_000) -> dict[str, Any]:
    """Verify archive members and their SHA-256 without extracting ZIP paths."""
    expected = _digest(expected_package_sha256, "expected_package_sha256")
    if type(max_total_bytes) is not int or max_total_bytes < 1:
        raise RecordError("max_total_bytes must be positive integer")
    archive_path = Path(path)
    try:
        with archive_path.open("rb") as source:
            sha = hashlib.sha256()
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                sha.update(chunk)
        actual = sha.hexdigest()
        if actual != expected:
            raise RecordError("audit ZIP fingerprint mismatch")
        with ZipFile(archive_path) as archive:
            members = archive.infolist()
            names = [m.filename for m in members]
            if len(names) != len(set(names)):
                raise RecordError("duplicate ZIP member names")
            if names != sorted(names):
                raise RecordError("ZIP member order is not canonical")
            if any(m.is_dir() or m.compress_type != 0 or m.flag_bits & 1 for m in members):
                raise RecordError("ZIP must contain only unencrypted stored regular files")
            if any(m.file_size > max_total_bytes for m in members):
                raise RecordError("oversized ZIP member")
            if sum(m.file_size for m in members) > max_total_bytes:
                raise RecordError("ZIP uncompressed size exceeds limit")
            if "dossier.json" not in names or "index.json" not in names:
                raise RecordError("ZIP missing dossier or index")
            dossier = _load_json(archive.read("dossier.json"), "dossier")
            index = _load_json(archive.read("index.json"), "index")
            if dossier.get("report_version") != "1.0" or dossier.get("report_sha256") != sha256_data({
                k: v for k, v in dossier.items() if k != "report_sha256"}):
                raise RecordError("dossier fingerprint mismatch")
            if index.get("package_version") != "1.0" or index.get("dossier_sha256") != sha256_data(dossier):
                raise RecordError("index not bound to dossier")
            evidence = dossier.get("source_evidence")
            artifacts = index.get("artifacts")
            if not isinstance(evidence, list) or not evidence or not isinstance(artifacts, list):
                raise RecordError("missing evidence inventory")
            if index.get("artifact_count") != len(artifacts) or len(artifacts) != len(evidence):
                raise RecordError("artifact count mismatch")
            declared = {x["evidence_id"]: x for x in evidence if isinstance(x, dict) and "evidence_id" in x}
            if len(declared) != len(evidence):
                raise RecordError("duplicate or invalid dossier evidence IDs")
            paths = set()
            seen_evidence_ids = set()
            for item in artifacts:
                if not isinstance(item, dict):
                    raise RecordError("artifact manifest entry must be object")
                eid, name = item.get("evidence_id"), item.get("path")
                if eid in seen_evidence_ids:
                    raise RecordError("duplicate artifact evidence ID")
                seen_evidence_ids.add(eid)
                if eid not in declared or not isinstance(name, str) or not name.startswith("artifacts/"):
                    raise RecordError("artifact not present in dossier or invalid path")
                parts = name.split("/")
                if any(not p or p in (".", "..") for p in parts) or "\\" in name or name in paths:
                    raise RecordError("unsafe or duplicate artifact path")
                paths.add(name)
                if name not in names:
                    raise RecordError("missing artifact ZIP member")
                original = declared[eid]
                digest = _digest(item.get("sha256"), "artifact sha256")
                if digest != original.get("sha256") or item.get("role") != original.get("role"):
                    raise RecordError("artifact manifest not bound to dossier")
                if type(item.get("size_bytes")) is not int or item["size_bytes"] < 0:
                    raise RecordError("invalid artifact size")
                h = hashlib.sha256()
                size = 0
                with archive.open(name) as stream:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > max_total_bytes:
                            raise RecordError("artifact size limit exceeded")
                        h.update(chunk)
                if size != item["size_bytes"] or h.hexdigest() != digest:
                    raise RecordError("artifact content fingerprint or size mismatch")
            if set(names) != paths | {"dossier.json", "index.json"}:
                raise RecordError("unexpected ZIP members")
    except (OSError, BadZipFile, EOFError, RuntimeError, KeyError, TypeError) as exc:
        raise RecordError(f"unable to verify audit ZIP: {exc}") from exc
    payload = {
        "report_version": "1.0",
        "package_sha256": actual,
        "dossier_sha256": sha256_data(dossier),
        "index_sha256": sha256_data(index),
        "verified_artifacts": len(paths),
        "source_artifact_bytes_verified": True,
        "custodian_identity_verified": False,
        "trusted_timestamps_verified": False,
        "scientific_replication_verified": False,
    }
    return {**payload, "report_sha256": sha256_data(payload)}


def append_custody_event(events: list[dict[str, Any]], event: dict[str, Any],
                         package_sha256: str) -> list[dict[str, Any]]:
    """Append a deterministic event after verifying the existing hash chain."""
    digest = _digest(package_sha256, "package_sha256")
    if not isinstance(events, list) or not isinstance(event, dict):
        raise RecordError("custody events must be an array and event an object")
    previous = "0" * 64
    for number, existing in enumerate(events):
        if not isinstance(existing, dict) or existing.get("sequence") != number + 1:
            raise RecordError("custody sequence mismatch")
        if existing.get("package_sha256") != digest or existing.get("previous_event_sha256") != previous:
            raise RecordError("custody chain or package binding mismatch")
        expected = sha256_data({k: v for k, v in existing.items() if k != "event_sha256"})
        if existing.get("event_sha256") != expected:
            raise RecordError("custody event fingerprint mismatch")
        previous = expected
    if set(event) != {"custodian_id", "action", "timestamp", "note"}:
        raise RecordError("event requires custodian_id, action, timestamp, note")
    for name in ("custodian_id", "timestamp", "note"):
        if not isinstance(event[name], str) or not event[name].strip():
            raise RecordError(f"{name} must be nonempty text")
    if event["action"] not in ("created", "transferred", "received", "verified", "archived"):
        raise RecordError("unsupported custody action")
    payload = {**event, "sequence": len(events) + 1,
               "package_sha256": digest, "previous_event_sha256": previous}
    return [*events, {**payload, "event_sha256": sha256_data(payload)}]
