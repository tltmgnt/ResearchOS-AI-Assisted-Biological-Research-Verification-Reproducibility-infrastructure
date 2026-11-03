import copy
import json
import unittest
from pathlib import Path

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.reviews import evaluate_reviews, verify_review_report

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.bundle = {
            "schema_version": "1.0",
            "record_sha256": sha256_data(self.record),
            "reviews": [{
                "review_id": "review-1",
                "claim_id": "claim-synthetic-1",
                "reviewer_id": "reviewer-synthetic",
                "organization_id": "independent-demo-lab",
                "reviewed_at": "2026-11-03T10:00:00Z",
                "decision": "confirm",
                "reproduction_method": "synthetic protocol comparison",
                "protocol_id": "synthetic-control-check-v1",
                "evidence_ids": ["ev-01"],
                "independent_of_original_team": True,
                "raw_data_available": True,
                "protocol_followed": True,
                "conflicts_of_interest": [],
                "notes": "Synthetic declaration, not a real reviewer.",
            }],
        }

    def test_review_determinism(self):
        a = evaluate_reviews(self.record, self.bundle)
        self.assertEqual(a, evaluate_reviews(self.record, self.bundle))
        self.assertTrue(verify_review_report(self.record, self.bundle, a))
        self.assertEqual(a["claims"][0]["self_declared_eligible_count"], 1)
        self.assertFalse(a["claims"][0]["independent_replication_verified"])
        self.assertFalse(a["reviews"][0]["identity_authenticated"])

    def test_report_tampering(self):
        report = evaluate_reviews(self.record, self.bundle)
        report["reviews"][0]["identity_authenticated"] = True
        self.assertFalse(verify_review_report(self.record, self.bundle, report))

    def test_record_binding(self):
        self.record["claims"][0]["statement"] = "changed"
        with self.assertRaises(RecordError):
            evaluate_reviews(self.record, self.bundle)

    def test_conflict_blocks_eligibility(self):
        self.bundle["reviews"][0]["conflicts_of_interest"] = ["same laboratory"]
        result = evaluate_reviews(self.record, self.bundle)
        self.assertFalse(result["reviews"][0]["self_declared_eligible"])

    def test_challenge_requires_adjudication(self):
        self.bundle["reviews"][0]["decision"] = "challenge"
        result = evaluate_reviews(self.record, self.bundle)
        self.assertTrue(result["claims"][0]["requires_adjudication"])
        self.assertEqual(result["claims"][0]["recommended_action"], "resolve_challenge")

    def test_unknown_evidence_rejected(self):
        self.bundle["reviews"][0]["evidence_ids"] = ["unknown"]
        with self.assertRaises(RecordError):
            evaluate_reviews(self.record, self.bundle)

    def test_wrong_protocol_rejected(self):
        self.bundle["reviews"][0]["protocol_id"] = "different"
        with self.assertRaises(RecordError):
            evaluate_reviews(self.record, self.bundle)

    def test_duplicate_review_ids_rejected(self):
        self.bundle["reviews"].append(copy.deepcopy(self.bundle["reviews"][0]))
        with self.assertRaises(RecordError):
            evaluate_reviews(self.record, self.bundle)

    def test_missing_boolean_rejected(self):
        del self.bundle["reviews"][0]["independent_of_original_team"]
        with self.assertRaises(RecordError):
            evaluate_reviews(self.record, self.bundle)

    def test_failing_evidence_blocks_eligibility(self):
        self.record["evidence"][0]["verdict"] = "fail"
        self.bundle["record_sha256"] = sha256_data(self.record)
        result = evaluate_reviews(self.record, self.bundle)
        self.assertFalse(result["reviews"][0]["self_declared_eligible"])


if __name__ == "__main__":
    unittest.main()
