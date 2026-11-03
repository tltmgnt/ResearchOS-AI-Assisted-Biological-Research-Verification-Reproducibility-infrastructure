import base64
import copy
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.trust_anchor import anchor_payload, verify_published_anchor


class TrustAnchorTests(unittest.TestCase):
    def setUp(self):
        self.checkpoint = {
            "schema_version": "1.0", "checkpoint_id": "synthetic-1",
            "declared_at": "2026-11-03T11:00:00Z",
            "package_sha256": "a" * 64, "custody_head_sha256": "b" * 64,
            "registry_head_sha256": "c" * 64, "custody_sequence": 2}
        self.privates = [Ed25519PrivateKey.generate() for _ in range(2)]
        keys = []
        self.attestations = []
        for i, private in enumerate(self.privates):
            public = private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)
            keys.append({"key_id": f"key-{i}", "publisher_id": f"publisher-{i}",
                         "organization_id": f"org-{i}", "approved": True, "revoked": False,
                         "public_key_b64": base64.b64encode(public).decode()})
            self.attestations.append({"key_id": f"key-{i}", "signature_b64":
                base64.b64encode(private.sign(anchor_payload(self.checkpoint))).decode()})
        self.registry = {"schema_version": "1.0", "keys": keys}
        self.pin = sha256_data(self.registry)

    def verify(self):
        return verify_published_anchor(
            self.checkpoint, self.attestations, self.registry, self.pin,
            "a" * 64, "b" * 64, "c" * 64)

    def test_two_organizations_accepted(self):
        report = self.verify()
        self.assertTrue(report["cryptographic_publisher_quorum_met"])
        self.assertFalse(report["independent_publication_confirmed"])
        self.assertFalse(report["scientific_replication_verified"])
        self.assertEqual(report, self.verify())

    def test_tampered_signature_fails(self):
        self.attestations[0]["signature_b64"] = base64.b64encode(b"0" * 64).decode()
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_unapproved_key_fails(self):
        self.registry["keys"][0]["approved"] = False
        self.pin = sha256_data(self.registry)
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_revoked_key_fails(self):
        self.registry["keys"][0]["revoked"] = True
        self.pin = sha256_data(self.registry)
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_registry_pin_mismatch_rejected(self):
        self.registry["keys"][0]["organization_id"] = "attacker"
        with self.assertRaises(RecordError):
            self.verify()

    def test_checkpoint_binding_mismatch_rejected(self):
        self.checkpoint["package_sha256"] = "d" * 64
        with self.assertRaises(RecordError):
            self.verify()

    def test_checkpoint_change_invalidates_signatures(self):
        self.checkpoint["declared_at"] = "changed"
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_duplicate_attestation_rejected(self):
        self.attestations.append(copy.deepcopy(self.attestations[0]))
        with self.assertRaises(RecordError):
            self.verify()

    def test_same_org_not_a_quorum(self):
        self.registry["keys"][1]["organization_id"] = "org-0"
        self.pin = sha256_data(self.registry)
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_single_attestation_not_a_quorum(self):
        self.attestations = self.attestations[:1]
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_unknown_key_fails(self):
        self.attestations[0]["key_id"] = "unknown"
        self.assertFalse(self.verify()["cryptographic_publisher_quorum_met"])

    def test_invalid_minimum_rejected(self):
        with self.assertRaises(RecordError):
            verify_published_anchor(self.checkpoint, self.attestations, self.registry,
                                    self.pin, "a" * 64, "b" * 64, "c" * 64,
                                    minimum_publishers=1)


if __name__ == "__main__":
    unittest.main()
