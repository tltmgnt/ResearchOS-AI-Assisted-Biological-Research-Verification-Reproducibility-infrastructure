import base64
import copy
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from researchos_bio.attestations import attestation_payload, verify_attestations
from researchos_bio.core import RecordError, sha256_data

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.review = {
            "review_id": "review-1", "claim_id": "claim-synthetic-1",
            "reviewer_id": "reviewer-a", "organization_id": "synthetic-lab",
            "reviewed_at": "2026-11-03T12:00:00Z", "decision": "confirm",
            "reproduction_method": "synthetic check",
            "protocol_id": "synthetic-control-check-v1",
            "evidence_ids": ["ev-01"], "independent_of_original_team": True,
            "raw_data_available": True, "protocol_followed": True,
            "conflicts_of_interest": [],
        }
        self.bundle = {"schema_version": "1.0", "record_sha256": sha256_data(self.record),
                       "reviews": [self.review]}
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.registry = {"schema_version": "1.0", "keys": [{
            "key_id": "key-1", "reviewer_id": "reviewer-a",
            "public_key_b64": base64.b64encode(public).decode("ascii"),
        }]}
        self.attestations = {"schema_version": "1.0", "signatures": [{
            "review_id": "review-1", "key_id": "key-1",
            "signature_b64": base64.b64encode(
                self.key.sign(attestation_payload(self.record, self.review))).decode("ascii"),
        }]}

    def test_valid_signature(self):
        result = verify_attestations(self.record, self.bundle, self.registry, self.attestations)
        self.assertTrue(result["all_reviews_signed"])
        self.assertEqual(result["reviews"][0]["signature_status"], "valid")
        self.assertFalse(result["reviews"][0]["identity_independently_verified"])
        self.assertFalse(result["reviews"][0]["independent_replication_verified"])

    def test_review_tamper_invalidates_signature(self):
        self.review["decision"] = "challenge"
        result = verify_attestations(self.record, self.bundle, self.registry, self.attestations)
        self.assertEqual(result["reviews"][0]["signature_status"], "invalid_signature")

    def test_record_change_breaks_binding(self):
        self.record["claims"][0]["statement"] = "altered"
        with self.assertRaises(RecordError):
            verify_attestations(self.record, self.bundle, self.registry, self.attestations)

    def test_missing_signature(self):
        self.attestations["signatures"] = []
        self.assertEqual(verify_attestations(self.record, self.bundle, self.registry, self.attestations)
                         ["reviews"][0]["signature_status"], "missing")

    def test_untrusted_key(self):
        self.attestations["signatures"][0]["key_id"] = "unknown"
        self.assertEqual(verify_attestations(self.record, self.bundle, self.registry, self.attestations)
                         ["reviews"][0]["signature_status"], "untrusted_key")

    def test_wrong_reviewer_key(self):
        self.registry["keys"][0]["reviewer_id"] = "other"
        self.assertEqual(verify_attestations(self.record, self.bundle, self.registry, self.attestations)
                         ["reviews"][0]["signature_status"], "reviewer_key_mismatch")

    def test_duplicate_signature(self):
        self.attestations["signatures"].append(copy.deepcopy(self.attestations["signatures"][0]))
        with self.assertRaises(RecordError):
            verify_attestations(self.record, self.bundle, self.registry, self.attestations)

    def test_unknown_review(self):
        self.attestations["signatures"][0]["review_id"] = "unknown"
        with self.assertRaises(RecordError):
            verify_attestations(self.record, self.bundle, self.registry, self.attestations)

    def test_malformed_signature(self):
        self.attestations["signatures"][0]["signature_b64"] = "invalid"
        with self.assertRaises(RecordError):
            verify_attestations(self.record, self.bundle, self.registry, self.attestations)

    def test_bad_public_key(self):
        self.registry["keys"][0]["public_key_b64"] = "invalid"
        with self.assertRaises(RecordError):
            verify_attestations(self.record, self.bundle, self.registry, self.attestations)


if __name__ == "__main__":
    unittest.main()
