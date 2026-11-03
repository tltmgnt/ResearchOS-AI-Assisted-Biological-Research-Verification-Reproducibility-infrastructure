import base64
import copy
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.external_audit import audit_payload, verify_external_audit


class ExternalAuditTests(unittest.TestCase):
    def setUp(self):
        payload = {"report_version": "1.0", "software_pilot_gate_passed": True}
        self.pilot = {**payload, "report_sha256": sha256_data(payload)}
        self.keys = [Ed25519PrivateKey.generate() for _ in range(2)]
        self.registry = {"schema_version": "1.0", "keys": []}
        self.bundle = {"schema_version": "1.0", "pilot_report_sha256": sha256_data(self.pilot),
                       "decisions": []}
        for i, key in enumerate(self.keys):
            evaluator, org, kid = f"auditor-{i}", f"org-{i}", f"key-{i}"
            self.registry["keys"].append({
                "key_id": kid, "evaluator_id": evaluator, "organization_id": org,
                "approved": True, "revoked": False,
                "public_key_b64": base64.b64encode(key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode(),
            })
            decision = {"decision_id": f"decision-{i}", "evaluator_id": evaluator,
                        "organization_id": org, "verdict": "approve",
                        "reason": "synthetic audit of software evidence"}
            self.bundle["decisions"].append({
                "key_id": kid, "decision": decision,
                "signature_b64": base64.b64encode(key.sign(audit_payload(self.pilot, decision))).decode(),
            })

    def check(self):
        return verify_external_audit(self.pilot, self.registry, self.bundle)

    def resign(self, i):
        item = self.bundle["decisions"][i]
        item["signature_b64"] = base64.b64encode(
            self.keys[i].sign(audit_payload(self.pilot, item["decision"]))).decode()

    def test_two_organization_quorum_not_science(self):
        result = self.check()
        self.assertTrue(result["administrative_external_audit_accepted"])
        self.assertFalse(result["scientific_validation_performed"])
        self.assertFalse(result["real_world_evaluator_identity_verified"])
        self.assertEqual(result, self.check())

    def test_revoked_key(self):
        self.registry["keys"][0]["revoked"] = True
        self.assertFalse(self.check()["administrative_external_audit_accepted"])

    def test_unapproved_key(self):
        self.registry["keys"][0]["approved"] = False
        self.assertFalse(self.check()["administrative_external_audit_accepted"])

    def test_signature_tamper(self):
        self.bundle["decisions"][0]["decision"]["reason"] = "changed"
        self.assertEqual(self.check()["decisions"][0]["signature_status"], "invalid_signature")

    def test_negative_verdict_veto(self):
        self.bundle["decisions"][0]["decision"]["verdict"] = "reject"
        self.resign(0)
        self.assertTrue(self.check()["negative_decision_veto"])
        self.assertFalse(self.check()["administrative_external_audit_accepted"])

    def test_same_organization_does_not_form_quorum(self):
        self.registry["keys"][1]["organization_id"] = "org-0"
        self.bundle["decisions"][1]["decision"]["organization_id"] = "org-0"
        self.resign(1)
        self.assertEqual(self.check()["valid_approving_organizations"], 1)

    def test_pilot_report_tamper(self):
        self.pilot["software_pilot_gate_passed"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_pilot_gate_must_pass(self):
        self.pilot["software_pilot_gate_passed"] = False
        self.pilot["report_sha256"] = sha256_data({
            k: v for k, v in self.pilot.items() if k != "report_sha256"})
        self.bundle["pilot_report_sha256"] = sha256_data(self.pilot)
        for i in range(2):
            self.resign(i)
        self.assertFalse(self.check()["administrative_external_audit_accepted"])

    def test_duplicate_evaluator_rejected(self):
        self.bundle["decisions"].append(copy.deepcopy(self.bundle["decisions"][0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_wrong_reviewer_key(self):
        self.bundle["decisions"][0]["key_id"] = "key-1"
        self.assertEqual(self.check()["decisions"][0]["signature_status"], "identity_mismatch")

    def test_untrusted_key(self):
        self.bundle["decisions"][0]["key_id"] = "missing"
        self.assertEqual(self.check()["decisions"][0]["signature_status"], "untrusted_key")

    def test_threshold_enforced(self):
        with self.assertRaises(RecordError):
            verify_external_audit(self.pilot, self.registry, self.bundle, minimum_organizations=1)


if __name__ == "__main__":
    unittest.main()
