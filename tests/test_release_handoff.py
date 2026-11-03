import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.release_handoff import (
    REQUIRED_EXTERNAL_GATES, evaluate_release_handoff,
)


def report(**fields):
    data = {"report_version": "1.0", **fields}
    return {**data, "report_sha256": sha256_data(data)}


class ReleaseHandoffTests(unittest.TestCase):
    def setUp(self):
        self.auditor = report(all_software_acceptance_scenarios_passed=True)
        self.preflight = report(operational_preflight_passed=True)
        self.pilot = report(documentary_pilot_gate_passed=True)
        self.manifest = {
            "schema_version": "1.0",
            "release_version": "1.0.0-rc1",
            "release_commit": "a" * 40,
            "auditor_acceptance_report_sha256": self.auditor["report_sha256"],
            "deployment_preflight_report_sha256": self.preflight["report_sha256"],
            "independent_pilot_report_sha256": self.pilot["report_sha256"],
            "handoff_owner_id": "synthetic-test-owner",
            "handoff_runbook_sha256": "b" * 64,
            "rollback_plan_sha256": "c" * 64,
            "external_evidence": {
                name: {"artifact_sha256": "d" * 64, "declared_approved": True}
                for name in REQUIRED_EXTERNAL_GATES},
        }

    def check(self):
        return evaluate_release_handoff(
            self.manifest, self.auditor, self.preflight, self.pilot)

    def test_documentary_gate_passes_but_does_not_authorize(self):
        result = self.check()
        self.assertTrue(result["release_candidate_documentary_gate_passed"])
        for name in ("external_approvals_authenticated",
                     "independent_security_signoff_verified",
                     "independent_pilot_execution_verified",
                     "production_deployment_performed",
                     "production_release_authorized",
                     "scientific_replication_verified"):
            self.assertFalse(result[name])
        self.assertEqual(result, self.check())

    def test_broken_report_link_rejected(self):
        self.manifest["independent_pilot_report_sha256"] = "f" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_tampered_report_rejected(self):
        self.auditor["all_software_acceptance_scenarios_passed"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_failed_auditor_gate_fails(self):
        self.auditor = report(all_software_acceptance_scenarios_passed=False)
        self.manifest["auditor_acceptance_report_sha256"] = self.auditor["report_sha256"]
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_failed_preflight_fails(self):
        self.preflight = report(operational_preflight_passed=False)
        self.manifest["deployment_preflight_report_sha256"] = self.preflight["report_sha256"]
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_failed_pilot_fails(self):
        self.pilot = report(documentary_pilot_gate_passed=False)
        self.manifest["independent_pilot_report_sha256"] = self.pilot["report_sha256"]
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_missing_external_gate_rejected(self):
        del self.manifest["external_evidence"]["independent_security_review"]
        with self.assertRaises(RecordError):
            self.check()

    def test_unapproved_external_gate_fails(self):
        self.manifest["external_evidence"]["independent_pilot_execution"]["declared_approved"] = False
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_missing_external_reference_fails(self):
        self.manifest["external_evidence"]["external_publication_receipt"]["artifact_sha256"] = "0" * 64
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_boolean_as_approval_rejected(self):
        self.manifest["external_evidence"]["production_operations_approval"]["declared_approved"] = 1
        with self.assertRaises(RecordError):
            self.check()

    def test_final_release_version_rejected(self):
        self.manifest["release_version"] = "1.0.0"
        with self.assertRaises(RecordError):
            self.check()

    def test_placeholder_commit_fails(self):
        self.manifest["release_commit"] = "0" * 40
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_missing_rollback_plan_fails(self):
        self.manifest["rollback_plan_sha256"] = "0" * 64
        self.assertFalse(self.check()["release_candidate_documentary_gate_passed"])

    def test_unknown_manifest_field_rejected(self):
        self.manifest["secret"] = "not allowed"
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
