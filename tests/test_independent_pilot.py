import copy
import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.independent_pilot import evaluate_independent_pilot


def report(**kwargs):
    payload = {"report_version": "1.0", **kwargs}
    return {**payload, "report_sha256": sha256_data(payload)}


class IndependentPilotTests(unittest.TestCase):
    def setUp(self):
        self.dossier = report(administrative_dossier_complete=True)
        self.package = report(source_artifact_bytes_verified=True, package_sha256="a" * 64)
        self.acceptance = report(all_software_acceptance_scenarios_passed=True)
        self.evidence = {
            "schema_version": "1.0", "pilot_id": "synthetic-01",
            "dossier_sha256": self.dossier["report_sha256"],
            "package_report_sha256": self.package["report_sha256"],
            "auditor_acceptance_sha256": self.acceptance["report_sha256"],
            "audit_package_sha256": "a" * 64,
            "external_operator_id": "test-operator",
            "external_organization_id": "test-org",
            "operator_affiliation_declaration": "independent",
            "protocol_registration_sha256": "b" * 64,
            "raw_observations_sha256": "c" * 64,
            "signed_review_artifact_sha256": "d" * 64,
            "external_publication_receipt_sha256": "e" * 64,
            "independent_signoff_declared": True,
        }

    def check(self):
        return evaluate_independent_pilot(
            self.dossier, self.package, self.acceptance, self.evidence)

    def test_documentary_gate_passes_without_claiming_independence(self):
        result = self.check()
        self.assertTrue(result["documentary_pilot_gate_passed"])
        for field in ("independent_operator_identity_authenticated",
                      "independent_execution_verified",
                      "independent_signoff_cryptographically_verified",
                      "external_publication_receipt_verified",
                      "biological_replication_verified",
                      "production_release_authorized"):
            self.assertFalse(result[field])
        self.assertEqual(result, self.check())

    def test_dossier_tampering_rejected(self):
        self.dossier["administrative_dossier_complete"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_dossier_link_mismatch_rejected(self):
        self.evidence["dossier_sha256"] = "f" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_package_link_mismatch_rejected(self):
        self.evidence["audit_package_sha256"] = "f" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_acceptance_link_mismatch_rejected(self):
        self.evidence["auditor_acceptance_sha256"] = "f" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_negative_auditor_gate_fails(self):
        self.acceptance = report(all_software_acceptance_scenarios_passed=False)
        self.evidence["auditor_acceptance_sha256"] = self.acceptance["report_sha256"]
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])

    def test_source_bytes_not_verified_fails(self):
        self.package = report(source_artifact_bytes_verified=False, package_sha256="a" * 64)
        self.evidence["package_report_sha256"] = self.package["report_sha256"]
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])

    def test_affiliated_operator_fails(self):
        self.evidence["operator_affiliation_declaration"] = "affiliated"
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])

    def test_missing_signoff_fails(self):
        self.evidence["independent_signoff_declared"] = False
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])

    def test_placeholder_receipt_fails(self):
        self.evidence["external_publication_receipt_sha256"] = "0" * 64
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])

    def test_missing_evidence_field_rejected(self):
        del self.evidence["raw_observations_sha256"]
        with self.assertRaises(RecordError):
            self.check()

    def test_invalid_hash_rejected(self):
        self.evidence["raw_observations_sha256"] = "bad"
        with self.assertRaises(RecordError):
            self.check()

    def test_boolean_instead_of_signoff_rejected(self):
        self.evidence["independent_signoff_declared"] = 1
        with self.assertRaises(RecordError):
            self.check()

    def test_unknown_affiliation_reduces_gate(self):
        self.evidence["operator_affiliation_declaration"] = "unknown"
        self.assertFalse(self.check()["documentary_pilot_gate_passed"])


if __name__ == "__main__":
    unittest.main()
