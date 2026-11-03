import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from researchos_bio.assurance import assemble_assurance
from researchos_bio.core import RecordError

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class AssuranceTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text())
        self.artifact = {"report_sha256": "a", "all_artifacts_verified": True,
                         "artifacts": [{"evidence_id": x["evidence_id"], "status": "match"}
                                       for x in self.record["evidence"]]}
        self.review = {"report_sha256": "b", "reviews": [{
            "review_id": "r1", "claim_id": "claim-synthetic-1",
            "reviewer_id": "reviewer-1", "self_declared_eligible": True,
        }]}
        self.signed = {"report_sha256": "c", "reviews": [{
            "review_id": "r1", "cryptographically_attested": True,
        }]}
        self.governance = {"report_sha256": "d", "claims": [{
            "claim_id": "claim-synthetic-1", "accepted_reviewer_ids": ["reviewer-1"],
            "administrative_review_ready": True,
        }]}
        self.benchmark = {"report_sha256": "e", "comparisons": [{
            "claim_id": "claim-synthetic-1", "within_tolerance": True,
        }]}

    def check(self):
        with patch("researchos_bio.assurance.verify_artifacts", return_value=self.artifact), \
             patch("researchos_bio.assurance.evaluate_reviews", return_value=self.review), \
             patch("researchos_bio.assurance.verify_attestations", return_value=self.signed), \
             patch("researchos_bio.assurance.evaluate_governance", return_value=self.governance), \
             patch("researchos_bio.assurance.evaluate_benchmark", return_value=self.benchmark):
            return assemble_assurance(self.record, {}, ".", {}, {}, {}, {}, {}, {})

    def test_complete_packet_not_scientific_validation(self):
        result = self.check()
        self.assertTrue(result["all_assurance_packets_complete"])
        self.assertFalse(result["scientific_validation_performed"])
        self.assertFalse(result["claims"][0]["independent_replication_verified"])
        self.assertEqual(result, self.check())

    def test_artifact_mismatch_blocks_packet(self):
        self.artifact["artifacts"][0]["status"] = "mismatch"
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])

    def test_governance_failure_blocks_packet(self):
        self.governance["claims"][0]["administrative_review_ready"] = False
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])

    def test_benchmark_failure_blocks_packet(self):
        self.benchmark["comparisons"][0]["within_tolerance"] = False
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])

    def test_unsigned_review_blocks_packet(self):
        self.signed["reviews"][0]["cryptographically_attested"] = False
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])

    def test_no_qualifying_review_blocks_packet(self):
        self.review["reviews"][0]["self_declared_eligible"] = False
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])

    def test_missing_benchmark_rejected(self):
        self.benchmark["comparisons"] = []
        with self.assertRaises(RecordError):
            self.check()

    def test_unaccepted_reviewer_blocks_packet(self):
        self.governance["claims"][0]["accepted_reviewer_ids"] = []
        self.assertFalse(self.check()["claims"][0]["assurance_packet_complete"])


if __name__ == "__main__":
    unittest.main()
