"""Phase 22: local, read-only operational readiness and monitoring probes.

No network listener is started and no telemetry is transmitted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import sys
from typing import Any

from .core import RecordError, sha256_data


CHECKS = ("runtime_python", "artifact_directory", "release_commit",
          "publisher_registry_pin", "custody_registry_pin", "external_audit_approval")


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError(f"{name} must be a lowercase SHA-256")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{name} must be nonempty text")
    return value


def evaluate_deployment_readiness(config: dict[str, Any],
                                  artifact_root: str | Path) -> dict[str, Any]:
    """Read-only preflight; caller-provided approvals are declarations, not proof."""
    if not isinstance(config, dict) or config.get("schema_version") != "1.0":
        raise RecordError("deployment config schema_version must be 1.0")
    if set(config) != {"schema_version", "environment", "release_commit",
                       "publisher_registry_pin_sha256", "custody_registry_pin_sha256",
                       "external_audit_approval", "max_artifact_bytes"}:
        raise RecordError("deployment config fields mismatch")
    environment = config["environment"]
    if environment not in ("development", "staging", "production"):
        raise RecordError("environment must be development, staging or production")
    release = config["release_commit"]
    if not isinstance(release, str) or len(release) != 40 or any(c not in "0123456789abcdef" for c in release):
        raise RecordError("release_commit must be a full lowercase git SHA-1")
    for field in ("publisher_registry_pin_sha256", "custody_registry_pin_sha256"):
        _digest(config[field], field)
    if type(config["external_audit_approval"]) is not bool:
        raise RecordError("external_audit_approval must be boolean")
    maximum = config["max_artifact_bytes"]
    if type(maximum) is not int or not 1 <= maximum <= 500_000_000:
        raise RecordError("max_artifact_bytes must be integer in 1..500000000")
    root = Path(artifact_root)
    checks = []
    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
    add("runtime_python", sys.version_info >= (3, 11), "Python 3.11 or newer required")
    # Fail closed on symlinked roots and non-directories; never create paths.
    add("artifact_directory", root.is_dir() and not root.is_symlink(),
        "Artifact directory must exist and must not be a symlink")
    add("release_commit", release != "0" * 40, "Release commit must be nonzero")
    add("publisher_registry_pin", config["publisher_registry_pin_sha256"] != "0" * 64,
        "Publisher registry pin must be nonzero")
    add("custody_registry_pin", config["custody_registry_pin_sha256"] != "0" * 64,
        "Custody registry pin must be nonzero")
    add("external_audit_approval", config["external_audit_approval"],
        "Operator declaration only; approval authenticity not verified")
    preflight = all(x["passed"] for x in checks)
    payload = {
        "report_version": "1.0", "environment": environment,
        "config_sha256": sha256_data(config),
        "checks": checks,
        "operational_preflight_passed": preflight,
        "deployment_performed": False,
        "external_audit_approval_authenticated": False,
        "independent_security_signoff_verified": False,
        "production_release_authorized": False,
        "scientific_replication_verified": False,
        "disclaimer": "Preflight checks local declarations and paths only. Passing does not authenticate approvals, secure a deployment, verify external monitoring or authorize production.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}


def evaluate_monitoring_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Pure deterministic alert rules for externally collected metrics."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != "1.0":
        raise RecordError("monitoring snapshot schema_version must be 1.0")
    expected = {"schema_version", "sample_id", "verification_attempts",
                "verification_failures", "rejected_archive_inputs",
                "unexpected_process_restarts", "last_success_age_seconds"}
    if set(snapshot) != expected:
        raise RecordError("monitoring snapshot fields mismatch")
    _string(snapshot["sample_id"], "sample_id")
    for name in expected - {"schema_version", "sample_id"}:
        value = snapshot[name]
        if type(value) is not int or value < 0 or value > 1_000_000_000:
            raise RecordError(f"{name} must be nonnegative bounded integer")
    attempts = snapshot["verification_attempts"]
    failures = snapshot["verification_failures"]
    if failures > attempts:
        raise RecordError("verification_failures cannot exceed verification_attempts")
    alerts = []
    def alert(code: str, triggered: bool, severity: str) -> None:
        alerts.append({"code": code, "triggered": triggered, "severity": severity})
    alert("verification_failures", failures > 0, "warning")
    alert("suspicious_archive_inputs", snapshot["rejected_archive_inputs"] > 0, "warning")
    alert("unexpected_restarts", snapshot["unexpected_process_restarts"] > 0, "critical")
    alert("stale_verification", snapshot["last_success_age_seconds"] > 3600, "critical")
    alert("no_verification_activity", attempts == 0, "warning")
    alerts.sort(key=lambda item: item["code"])
    payload = {
        "report_version": "1.0", "sample_id": snapshot["sample_id"],
        "snapshot_sha256": sha256_data(snapshot),
        "critical_alert": any(a["triggered"] and a["severity"] == "critical" for a in alerts),
        "any_alert": any(a["triggered"] for a in alerts),
        "alerts": alerts,
        "metrics_source_authenticated": False,
        "monitoring_service_connected": False,
        "incident_response_activated": False,
        "disclaimer": "Deterministic alert evaluation only; metrics are supplied by caller and are not authenticated or collected by this tool.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
