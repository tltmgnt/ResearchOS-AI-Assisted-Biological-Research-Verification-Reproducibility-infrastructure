"""Phase 21: reproducible, fail-closed independent auditor acceptance scenarios.

The suite invokes only fixed ResearchOS verification functions. An auditor must
supply genuine independently sourced fixtures and sign off out of band.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit_verify import verify_audit_package
from .core import RecordError, sha256_data
from .trust_anchor import verify_published_anchor


REQUIRED_SCENARIOS = frozenset({
    "valid_audit_package", "tampered_audit_package",
    "valid_publisher_quorum", "tampered_publisher_signature",
    "wrong_publisher_registry_pin", "wrong_checkpoint_binding",
})


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{label} must be nonempty text")
    return value


def evaluate_auditor_acceptance(suite: dict[str, Any],
                                fixture_root: str | Path) -> dict[str, Any]:
    """Execute declared expected-success/failure cases against fixed verifiers.

    Suite input is untrusted. No arbitrary shell commands, Python evaluation,
    network requests or external-file paths are permitted.
    """
    if not isinstance(suite, dict) or suite.get("schema_version") != "1.0":
        raise RecordError("acceptance suite schema_version must be 1.0")
    _nonempty(suite.get("suite_id"), "suite_id")
    cases = suite.get("cases")
    if not isinstance(cases, list) or len(cases) != len(REQUIRED_SCENARIOS):
        raise RecordError("acceptance suite must contain all six required cases")
    root = Path(fixture_root).resolve(strict=True)
    if not root.is_dir():
        raise RecordError("fixture_root must be a directory")
    seen = set()
    results = []
    for case in cases:
        if not isinstance(case, dict):
            raise RecordError("acceptance case must be an object")
        scenario = case.get("scenario")
        if scenario not in REQUIRED_SCENARIOS or scenario in seen:
            raise RecordError("duplicate or unknown acceptance scenario")
        seen.add(scenario)
        if type(case.get("expect_success")) is not bool:
            raise RecordError("expect_success must be boolean")
        expected_success = scenario.startswith("valid_")
        if case["expect_success"] != expected_success:
            raise RecordError("scenario expectation cannot be overridden")
        kind = "audit_package" if scenario.endswith("audit_package") else "publisher_anchor"
        fixture = case.get("fixture")
        if not isinstance(fixture, dict):
            raise RecordError("case fixture must be an object")
        try:
            if kind == "audit_package":
                if set(fixture) != {"path", "expected_sha256"}:
                    raise RecordError("audit package fixture must specify path and expected_sha256")
                name = fixture["path"]
                if (not isinstance(name, str) or not name or name in (".", "..")
                        or "/" in name or "\\" in name or "\x00" in name):
                    raise RecordError("audit fixture path must be a plain filename")
                source = root / name
                if source.is_symlink() or not source.is_file():
                    raise RecordError("audit fixture must be a regular non-symlink file")
                verify_audit_package(source, fixture["expected_sha256"])
                verified = True
            else:
                required = {"checkpoint", "attestations", "publisher_registry",
                            "pinned_publisher_registry_sha256", "expected_package_sha256",
                            "expected_custody_head_sha256", "expected_registry_head_sha256"}
                if set(fixture) != required:
                    raise RecordError("publisher anchor fixture fields mismatch")
                report = verify_published_anchor(
                    fixture["checkpoint"], fixture["attestations"],
                    fixture["publisher_registry"], fixture["pinned_publisher_registry_sha256"],
                    fixture["expected_package_sha256"],
                    fixture["expected_custody_head_sha256"],
                    fixture["expected_registry_head_sha256"])
                verified = report["cryptographic_publisher_quorum_met"]
            outcome = "verified" if verified else "rejected"
        except (RecordError, OSError, ValueError, TypeError, KeyError):
            outcome = "rejected"
        passed = (outcome == "verified") == expected_success
        results.append({"scenario": scenario, "expected": "verified" if expected_success else "rejected",
                        "observed": outcome, "passed": passed})
    if seen != REQUIRED_SCENARIOS:
        raise RecordError("missing required acceptance scenarios")
    results.sort(key=lambda x: x["scenario"])
    accepted = all(x["passed"] for x in results)
    payload = {
        "report_version": "1.0", "suite_id": suite["suite_id"],
        "suite_sha256": sha256_data(suite),
        "all_software_acceptance_scenarios_passed": accepted,
        "required_scenario_count": len(REQUIRED_SCENARIOS),
        "independent_auditor_executed": False,
        "external_auditor_approved": False,
        "real_world_publisher_identity_verified": False,
        "scientific_replication_verified": False,
        "scenarios": results,
        "disclaimer": "This locally executed acceptance suite does not prove an independent auditor ran it, approved results, authenticated registry pins, or validated biological claims.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
