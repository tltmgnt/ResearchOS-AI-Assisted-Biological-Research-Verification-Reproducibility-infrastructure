"""Phase 23: evidence-linked independent pilot validation gate.

Checks cryptographic consistency of supplied reports and documentary declarations;
cannot establish human independence or scientific truth.
"""
from __future__ import annotations

from typing import Any

from .core import RecordError, sha256_data


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RecordError(f"{label} must be lowercase SHA-256")
    return value


def _report(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("report_version") != "1.0":
        raise RecordError(f"{label} must be version 1.0 report")
    if value.get("report_sha256") != sha256_data({k: v for k, v in value.items() if k != "report_sha256"}):
        raise RecordError(f"{label} report fingerprint mismatch")
    return value


def evaluate_independent_pilot(
    dossier: dict[str, Any],
    package_verification: dict[str, Any],
    auditor_acceptance: dict[str, Any],
    pilot_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a fail-closed documentary gate for a pilot evidence packet."""
    dossier = _report(dossier, "dossier")
    package = _report(package_verification, "package verification")
    acceptance = _report(auditor_acceptance, "auditor acceptance")
    if not isinstance(pilot_evidence, dict) or pilot_evidence.get("schema_version") != "1.0":
        raise RecordError("pilot evidence schema_version must be 1.0")
    required = {"schema_version", "pilot_id", "dossier_sha256", "package_report_sha256",
                "auditor_acceptance_sha256", "audit_package_sha256",
                "external_operator_id", "external_organization_id",
                "operator_affiliation_declaration", "protocol_registration_sha256",
                "raw_observations_sha256", "signed_review_artifact_sha256",
                "external_publication_receipt_sha256", "independent_signoff_declared"}
    if set(pilot_evidence) != required:
        raise RecordError("pilot evidence fields mismatch")
    for field in ("pilot_id", "external_operator_id", "external_organization_id"):
        value = pilot_evidence[field]
        if not isinstance(value, str) or not value.strip():
            raise RecordError(f"{field} must be nonempty text")
    if pilot_evidence["operator_affiliation_declaration"] not in ("independent", "affiliated", "unknown"):
        raise RecordError("operator_affiliation_declaration must be independent, affiliated or unknown")
    if type(pilot_evidence["independent_signoff_declared"]) is not bool:
        raise RecordError("independent_signoff_declared must be boolean")
    for field in required:
        if field.endswith("_sha256"):
            _digest(pilot_evidence[field], field)
    if pilot_evidence["dossier_sha256"] != dossier["report_sha256"]:
        raise RecordError("pilot evidence not bound to dossier")
    if pilot_evidence["package_report_sha256"] != package["report_sha256"]:
        raise RecordError("pilot evidence not bound to package verification")
    if pilot_evidence["auditor_acceptance_sha256"] != acceptance["report_sha256"]:
        raise RecordError("pilot evidence not bound to auditor acceptance")
    if pilot_evidence["audit_package_sha256"] != package.get("package_sha256"):
        raise RecordError("pilot evidence not bound to verified audit ZIP")
    checks = [
        {"check": "administrative_dossier", "passed": dossier.get("administrative_dossier_complete") is True},
        {"check": "source_bytes", "passed": package.get("source_artifact_bytes_verified") is True},
        {"check": "auditor_software_acceptance", "passed": acceptance.get("all_software_acceptance_scenarios_passed") is True},
        {"check": "external_operator_declaration", "passed": pilot_evidence["operator_affiliation_declaration"] == "independent"},
        {"check": "independent_signoff_declaration", "passed": pilot_evidence["independent_signoff_declared"]},
        {"check": "protocol_registration_reference", "passed": pilot_evidence["protocol_registration_sha256"] != "0" * 64},
        {"check": "raw_observations_reference", "passed": pilot_evidence["raw_observations_sha256"] != "0" * 64},
        {"check": "signed_review_reference", "passed": pilot_evidence["signed_review_artifact_sha256"] != "0" * 64},
        {"check": "external_publication_reference", "passed": pilot_evidence["external_publication_receipt_sha256"] != "0" * 64},
    ]
    payload = {
        "report_version": "1.0",
        "pilot_id": pilot_evidence["pilot_id"],
        "dossier_sha256": dossier["report_sha256"],
        "package_report_sha256": package["report_sha256"],
        "auditor_acceptance_sha256": acceptance["report_sha256"],
        "pilot_evidence_sha256": sha256_data(pilot_evidence),
        "documentary_pilot_gate_passed": all(c["passed"] for c in checks),
        "independent_operator_identity_authenticated": False,
        "independent_execution_verified": False,
        "independent_signoff_cryptographically_verified": False,
        "external_publication_receipt_verified": False,
        "biological_replication_verified": False,
        "production_release_authorized": False,
        "checks": checks,
        "disclaimer": "This is a documentary consistency gate. Nonzero evidence hashes and declared independence are not verification of the underlying documents, real-world identity, external execution or scientific replication.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
