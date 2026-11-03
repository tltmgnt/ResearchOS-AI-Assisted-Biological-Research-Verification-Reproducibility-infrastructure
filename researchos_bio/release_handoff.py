"""Phase 24: reproducible release candidate and handoff evidence gate.

A software-generated report cannot itself authorize production or attest to
independent reviews. External approval evidence remains an operator obligation.
"""
from __future__ import annotations

from typing import Any

from .core import RecordError, sha256_data


REQUIRED_EXTERNAL_GATES = (
    "independent_security_review",
    "independent_auditor_signoff",
    "independent_pilot_execution",
    "external_publication_receipt",
    "production_operations_approval",
)


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError(f"{label} must be lowercase SHA-256")
    return value


def _report(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("report_version") != "1.0":
        raise RecordError(f"{name} must be version 1.0 report")
    if value.get("report_sha256") != sha256_data({k: v for k, v in value.items() if k != "report_sha256"}):
        raise RecordError(f"{name} fingerprint mismatch")
    return value


def evaluate_release_handoff(
    manifest: dict[str, Any],
    auditor_acceptance: dict[str, Any],
    deployment_preflight: dict[str, Any],
    independent_pilot: dict[str, Any],
) -> dict[str, Any]:
    """Validate immutable links, software gates and external evidence inventory.

    The gate checks *declared* evidence references, not external authenticity.
    It intentionally never claims production authorization.
    """
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise RecordError("release manifest schema_version must be 1.0")
    required = {"schema_version", "release_version", "release_commit",
                "auditor_acceptance_report_sha256", "deployment_preflight_report_sha256",
                "independent_pilot_report_sha256", "handoff_owner_id",
                "handoff_runbook_sha256", "rollback_plan_sha256",
                "external_evidence"}
    if set(manifest) != required:
        raise RecordError("release manifest fields mismatch")
    version = manifest["release_version"]
    if version != "1.0.0-rc1":
        raise RecordError("Phase 24 targets 1.0.0-rc1, not a final production release")
    commit = manifest["release_commit"]
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise RecordError("release_commit must be a full lowercase git SHA-1")
    owner = manifest["handoff_owner_id"]
    if not isinstance(owner, str) or not owner.strip():
        raise RecordError("handoff_owner_id must be nonempty")
    for name in ("auditor_acceptance_report_sha256", "deployment_preflight_report_sha256",
                 "independent_pilot_report_sha256", "handoff_runbook_sha256",
                 "rollback_plan_sha256"):
        _sha(manifest[name], name)
    auditor = _report(auditor_acceptance, "auditor acceptance")
    preflight = _report(deployment_preflight, "deployment preflight")
    pilot = _report(independent_pilot, "independent pilot")
    for name, value in (("auditor_acceptance_report_sha256", auditor),
                        ("deployment_preflight_report_sha256", preflight),
                        ("independent_pilot_report_sha256", pilot)):
        if manifest[name] != value["report_sha256"]:
            raise RecordError(f"{name} does not match supplied report")
    evidence = manifest["external_evidence"]
    if not isinstance(evidence, dict) or set(evidence) != set(REQUIRED_EXTERNAL_GATES):
        raise RecordError("external_evidence must cover all five required gates")
    evidence_checks = []
    for name in REQUIRED_EXTERNAL_GATES:
        item = evidence[name]
        if not isinstance(item, dict) or set(item) != {"artifact_sha256", "declared_approved"}:
            raise RecordError(f"{name} must have artifact_sha256 and declared_approved")
        digest = _sha(item["artifact_sha256"], f"{name}.artifact_sha256")
        if type(item["declared_approved"]) is not bool:
            raise RecordError(f"{name}.declared_approved must be boolean")
        evidence_checks.append({"gate": name,
                                "documentary_reference_present": digest != "0" * 64,
                                "declared_approved": item["declared_approved"],
                                "externally_authenticated": False})
    checks = [
        {"gate": "release_commit", "passed": commit != "0" * 40},
        {"gate": "auditor_software_acceptance", "passed": auditor.get("all_software_acceptance_scenarios_passed") is True},
        {"gate": "deployment_preflight", "passed": preflight.get("operational_preflight_passed") is True},
        {"gate": "pilot_documentary_validation", "passed": pilot.get("documentary_pilot_gate_passed") is True},
        {"gate": "handoff_runbook", "passed": manifest["handoff_runbook_sha256"] != "0" * 64},
        {"gate": "rollback_plan", "passed": manifest["rollback_plan_sha256"] != "0" * 64},
    ]
    checks.extend({"gate": item["gate"], "passed": item["documentary_reference_present"] and item["declared_approved"]}
                  for item in evidence_checks)
    payload = {
        "report_version": "1.0",
        "release_version": version,
        "release_commit": commit,
        "manifest_sha256": sha256_data(manifest),
        "checks": checks,
        "external_evidence": evidence_checks,
        "release_candidate_documentary_gate_passed": all(x["passed"] for x in checks),
        "external_approvals_authenticated": False,
        "independent_security_signoff_verified": False,
        "independent_pilot_execution_verified": False,
        "production_deployment_performed": False,
        "production_release_authorized": False,
        "scientific_replication_verified": False,
        "disclaimer": "This release-candidate report checks supplied declarations and hash consistency only. Actual independent approvals, identity, production authorization and scientific replication require external verification.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
