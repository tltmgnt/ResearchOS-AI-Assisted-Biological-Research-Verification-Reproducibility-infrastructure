import base64
import copy
import json
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from researchos_bio.attestations import attestation_payload
from researchos_bio.core import RecordError, sha256_data
from researchos_bio.governance import evaluate_governance

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text())
        self.keys = [Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()]
        reviews = []
        keys = []
        signatures = []
        enrolled = []
        for i in range(2):
            reviewer, org, rid, kid = f"reviewer-{i}", f"lab-{i}", f"review-{i}", f"key-{i}"
            review = {
                "review_id": rid, "claim_id": "claim-synthetic-1",
                "reviewer_id": reviewer, "organization_id": org,
                "reviewed_at": "2026-11-03T12:00:00Z", "decision": "confirm",
                "reproduction_method": "synthetic comparison",
                "protocol_id": "synthetic-control-check-v1", "evidence_ids": ["ev-01"],
                "independent_of_original_team": True, "raw_data_available": True,
                "protocol_followed": True, "conflicts_of_interest": [],
            }
            reviews.append(review)
            keys.append({
                "key_id": kid, "reviewer_id": reviewer,
                "public_key_b64": base64.b64encode(self.keys[i].public_key().public_bytes(
                    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode(),
            })
            signatures.append({
                "review_id": rid, "key_id": kid,
                "signature_b64": base64.b64encode(self.keys[i].sign(
                    attestation_payload(self.record, review))).decode(),
            })
            enrolled.append({"reviewer_id": reviewer, "organization_id": org, "approved": True})
        self.bundle = {"schema_version": "1.0", "record_sha256": sha256_data(self.record), "reviews": reviews}
        self.registry = {"schema_version": "1.0", "keys": keys}
        self.signatures = {"schema_version": "1.0", "signatures": signatures}
        self.policy = {"schema_version": "1.0", "minimum_distinct_organizations": 2,
                       "revoked_key_ids": [], "enrolled_reviewers": enrolled}

    def run_check(self):
        return evaluate_governance(self.record, self.bundle, self.registry, self.signatures, self.policy)["claims"][0]

    def test_quorum_ready_is_not_scientific_validation(self):
        result = self.run_check()
        self.assertTrue(result["administrative_review_ready"])
        self.assertFalse(result["independent_replication_verified"])
        self.assertFalse(result["biological_claim_validated"])

    def test_revoked_key_blocks_quorum(self):
        self.policy["revoked_key_ids"] = ["key-1"]
        self.assertFalse(self.run_check()["administrative_review_ready"])

    def test_unapproved_reviewer_blocks_quorum(self):
        self.policy["enrolled_reviewers"][0]["approved"] = False
        self.assertFalse(self.run_check()["administrative_review_ready"])

    def test_organization_mismatch_blocks_quorum(self):
        self.policy["enrolled_reviewers"][0]["organization_id"] = "wrong"
        self.assertFalse(self.run_check()["administrative_review_ready"])

    def test_same_organization_does_not_count_twice(self):
        self.bundle["reviews"][1]["organization_id"] = "lab-0"
        self.policy["enrolled_reviewers"][1]["organization_id"] = "lab-0"
        self.signatures["signatures"][1]["signature_b64"] = base64.b64encode(
            self.keys[1].sign(attestation_payload(self.record, self.bundle["reviews"][1]))).decode()
        self.assertEqual(self.run_check()["distinct_approved_organizations"], 1)

    def test_challenge_blocks_quorum(self):
        self.bundle["reviews"][0]["decision"] = "challenge"
        self.signatures["signatures"][0]["signature_b64"] = base64.b64encode(
            self.keys[0].sign(attestation_payload(self.record, self.bundle["reviews"][0]))).decode()
        self.assertFalse(self.run_check()["administrative_review_ready"])

    def test_signature_tamper_blocks_quorum(self):
        self.signatures["signatures"][0]["signature_b64"] = self.signatures["signatures"][1]["signature_b64"]
        self.assertFalse(self.run_check()["administrative_review_ready"])

    def test_threshold_minimum_enforced(self):
        self.policy["minimum_distinct_organizations"] = 1
        with self.assertRaises(RecordError):
            self.run_check()

    def test_duplicate_enrollment_rejected(self):
        self.policy["enrolled_reviewers"].append(copy.deepcopy(self.policy["enrolled_reviewers"][0]))
        with self.assertRaises(RecordError):
            self.run_check()

    def test_duplicate_revocation_rejected(self):
        self.policy["revoked_key_ids"] = ["key-1", "key-1"]
        with self.assertRaises(RecordError):
            self.run_check()


if __name__ == "__main__":
    unittest.main()
