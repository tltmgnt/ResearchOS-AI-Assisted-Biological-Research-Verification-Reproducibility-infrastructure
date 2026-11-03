import base64
import copy
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from researchos_bio.audit_verify import append_custody_event
from researchos_bio.core import RecordError
from researchos_bio.signed_custody import custody_signature_payload, verify_signed_custody


class SignedCustodyTests(unittest.TestCase):
    def setUp(self):
        self.package_sha = "a" * 64
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.registry = {"schema_version": "1.0", "keys": [{
            "key_id": "lab-key", "custodian_id": "operator-1",
            "approved": True, "revoked": False,
            "public_key_b64": base64.b64encode(public).decode("ascii")}]}
        event = {"custodian_id": "operator-1", "action": "created",
                 "timestamp": "2026-11-03T11:00:00Z", "note": "synthetic"}
        self.events = append_custody_event([], event, self.package_sha)
        self.signatures = [{"sequence": 1, "key_id": "lab-key",
                            "signature_b64": base64.b64encode(
                                self.private.sign(custody_signature_payload(self.events[0]))
                            ).decode("ascii")}]
        self.anchor = {"schema_version": "1.0", "package_sha256": self.package_sha,
                       "sequence": 1, "event_sha256": self.events[0]["event_sha256"]}

    def check(self):
        return verify_signed_custody(self.events, self.signatures, self.registry,
                                     self.package_sha, self.anchor)

    def test_valid_signature_and_anchor(self):
        report = self.check()
        self.assertTrue(report["all_events_cryptographically_signed"])
        self.assertTrue(report["chain_matches_supplied_anchor"])
        self.assertFalse(report["anchor_independently_authenticated"])
        self.assertFalse(report["real_world_custodian_identity_verified"])
        self.assertEqual(report, self.check())

    def test_tampered_signature(self):
        self.signatures[0]["signature_b64"] = base64.b64encode(b"0" * 64).decode()
        self.assertFalse(self.check()["all_events_cryptographically_signed"])

    def test_revoked_key(self):
        self.registry["keys"][0]["revoked"] = True
        self.assertEqual(self.check()["events"][0]["signature_status"], "revoked_key")

    def test_unapproved_key(self):
        self.registry["keys"][0]["approved"] = False
        self.assertEqual(self.check()["events"][0]["signature_status"], "unapproved_key")

    def test_identity_mismatch(self):
        self.registry["keys"][0]["custodian_id"] = "someone-else"
        self.assertEqual(self.check()["events"][0]["signature_status"], "custodian_key_mismatch")

    def test_anchor_tampering_rejected(self):
        self.anchor["event_sha256"] = "0" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_package_tampering_rejected(self):
        with self.assertRaises(RecordError):
            verify_signed_custody(self.events, self.signatures, self.registry,
                                  "b" * 64, self.anchor)

    def test_event_tampering_rejected(self):
        self.events[0]["note"] = "altered"
        with self.assertRaises(RecordError):
            self.check()

    def test_missing_signature_fails_closed(self):
        self.signatures = []
        self.assertFalse(self.check()["all_events_cryptographically_signed"])

    def test_duplicate_signature_rejected(self):
        self.signatures.append(copy.deepcopy(self.signatures[0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_wrong_domain_signature_rejected(self):
        self.signatures[0]["signature_b64"] = base64.b64encode(
            self.private.sign(b"not-custody-domain")).decode()
        self.assertEqual(self.check()["events"][0]["signature_status"], "invalid_signature")

    def test_unsigned_second_event_not_accepted(self):
        self.events = append_custody_event(self.events, {
            "custodian_id": "operator-1", "action": "transferred",
            "timestamp": "2026-11-03T11:30:00Z", "note": "synthetic"}, self.package_sha)
        self.assertFalse(self.check()["all_events_cryptographically_signed"])


if __name__ == "__main__":
    unittest.main()
