import base64
import hashlib
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from researchos_bio.audit_export import export_verified_audit_package
from researchos_bio.auditor_acceptance import evaluate_auditor_acceptance
from researchos_bio.core import RecordError, sha256_data
from researchos_bio.trust_anchor import anchor_payload


class AuditorAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = b"synthetic test-only evidence"
        (self.root / "source.txt").write_bytes(data)
        payload = {"report_version": "1.0", "source_evidence": [{
            "evidence_id": "e1", "role": "synthetic",
            "sha256": hashlib.sha256(data).hexdigest()}]}
        dossier = {**payload, "report_sha256": sha256_data(payload)}
        archive = self.root / "audit.zip"
        result = export_verified_audit_package(dossier, self.root,
                                               {"e1": "source.txt"}, archive)
        self.checkpoint = {
            "schema_version": "1.0", "checkpoint_id": "test-only",
            "declared_at": "2026-11-03T11:00:00Z",
            "package_sha256": result["package_sha256"],
            "custody_head_sha256": "b" * 64,
            "registry_head_sha256": "c" * 64, "custody_sequence": 1}
        keys = []
        attestations = []
        for i in range(2):
            private = Ed25519PrivateKey.generate()
            public = private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)
            keys.append({"key_id": f"k{i}", "publisher_id": f"p{i}",
                         "organization_id": f"org{i}", "approved": True,
                         "revoked": False,
                         "public_key_b64": base64.b64encode(public).decode()})
            attestations.append({"key_id": f"k{i}",
                                 "signature_b64": base64.b64encode(
                                     private.sign(anchor_payload(self.checkpoint))).decode()})
        registry = {"schema_version": "1.0", "keys": keys}
        base = {"checkpoint": self.checkpoint, "attestations": attestations,
                "publisher_registry": registry,
                "pinned_publisher_registry_sha256": sha256_data(registry),
                "expected_package_sha256": result["package_sha256"],
                "expected_custody_head_sha256": "b" * 64,
                "expected_registry_head_sha256": "c" * 64}
        import copy
        invalid_sig = copy.deepcopy(base)
        invalid_sig["attestations"][0]["signature_b64"] = base64.b64encode(b"0" * 64).decode()
        invalid_pin = copy.deepcopy(base)
        invalid_pin["pinned_publisher_registry_sha256"] = "d" * 64
        invalid_binding = copy.deepcopy(base)
        invalid_binding["expected_package_sha256"] = "d" * 64
        self.suite = {"schema_version": "1.0", "suite_id": "synthetic-auditor-test",
                      "cases": [
                          {"scenario": "valid_audit_package", "expect_success": True,
                           "fixture": {"path": "audit.zip", "expected_sha256": result["package_sha256"]}},
                          {"scenario": "tampered_audit_package", "expect_success": False,
                           "fixture": {"path": "audit.zip", "expected_sha256": "d" * 64}},
                          {"scenario": "valid_publisher_quorum", "expect_success": True,
                           "fixture": base},
                          {"scenario": "tampered_publisher_signature", "expect_success": False,
                           "fixture": invalid_sig},
                          {"scenario": "wrong_publisher_registry_pin", "expect_success": False,
                           "fixture": invalid_pin},
                          {"scenario": "wrong_checkpoint_binding", "expect_success": False,
                           "fixture": invalid_binding}]}

    def check(self):
        return evaluate_auditor_acceptance(self.suite, self.root)

    def test_all_scenarios_pass(self):
        report = self.check()
        self.assertTrue(report["all_software_acceptance_scenarios_passed"])
        self.assertEqual(len(report["scenarios"]), 6)
        self.assertFalse(report["external_auditor_approved"])
        self.assertFalse(report["independent_auditor_executed"])

    def test_corrupt_positive_case_fails(self):
        self.suite["cases"][0]["fixture"]["expected_sha256"] = "0" * 64
        self.assertFalse(self.check()["all_software_acceptance_scenarios_passed"])

    def test_negative_case_unexpectedly_valid_fails(self):
        self.suite["cases"][1]["fixture"]["expected_sha256"] = (
            self.suite["cases"][0]["fixture"]["expected_sha256"])
        self.assertFalse(self.check()["all_software_acceptance_scenarios_passed"])

    def test_missing_scenario_rejected(self):
        self.suite["cases"].pop()
        with self.assertRaises(RecordError):
            self.check()

    def test_duplicate_scenario_rejected(self):
        self.suite["cases"][1] = self.suite["cases"][0]
        with self.assertRaises(RecordError):
            self.check()

    def test_expectation_cannot_be_flipped(self):
        self.suite["cases"][0]["expect_success"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_path_traversal_cannot_escape_root(self):
        self.suite["cases"][0]["fixture"]["path"] = "../outside.zip"
        self.assertFalse(self.check()["all_software_acceptance_scenarios_passed"])

    def test_untrusted_symlink_cannot_be_opened(self):
        (self.root / "alias.zip").symlink_to(self.root / "audit.zip")
        self.suite["cases"][0]["fixture"]["path"] = "alias.zip"
        self.assertFalse(self.check()["all_software_acceptance_scenarios_passed"])

    def test_unknown_scenario_rejected(self):
        self.suite["cases"][0]["scenario"] = "arbitrary_command"
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
