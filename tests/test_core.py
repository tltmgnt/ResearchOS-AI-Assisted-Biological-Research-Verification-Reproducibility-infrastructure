import copy
import json
import unittest
from pathlib import Path
from researchos_bio import RecordError, evaluate_record, validate_record, verify_report

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_deterministic_report_and_verify(self):
        a = evaluate_record(self.record)
        self.assertEqual(a, evaluate_record(self.record))
        self.assertTrue(verify_report(self.record, a))
        self.assertEqual(a["decisions"][0]["recommended_status"], "supported")
        self.assertFalse(a["decisions"][0]["independent_replication_verified"])
        self.assertTrue(a["decisions"][0]["shared_operator_warning"])

    def test_detects_tampering(self):
        report = evaluate_record(self.record)
        report["decisions"][0]["independent_replication_verified"] = True
        self.assertFalse(verify_report(self.record, report))
        self.record["claims"][0]["statement"] = "new claim"
        self.assertFalse(verify_report(self.record, evaluate_record(json.loads(EXAMPLE.read_text()))))

    def test_missing_evidence_is_rejected(self):
        self.record["claims"][0]["evidence_ids"].append("missing")
        with self.assertRaises(RecordError):
            validate_record(self.record)

    def test_foreign_evidence_and_orphans_rejected(self):
        self.record["evidence"][0]["claim_id"] = "other"
        with self.assertRaises(RecordError):
            validate_record(self.record)

    def test_evidence_failure_contests_claim(self):
        self.record["evidence"][0]["verdict"] = "fail"
        self.assertEqual(evaluate_record(self.record)["decisions"][0]["recommended_status"], "contested")

    def test_uncertainty_blocks_support(self):
        self.record["evidence"][0]["verdict"] = "uncertain"
        self.assertEqual(evaluate_record(self.record)["decisions"][0]["recommended_status"], "unverified")

    def test_invalid_digests_are_rejected(self):
        self.record["evidence"][0]["artifact_sha256"] = "not-sha256"
        with self.assertRaises(RecordError):
            validate_record(self.record)

    def test_naive_timestamps_are_rejected(self):
        self.record["evidence"][0]["observed_at"] = "2026-11-03"
        with self.assertRaises(RecordError):
            validate_record(self.record)

    def test_unverifiable_independence_reference_rejected(self):
        self.record["evidence"][0]["independent_of"] = ["not-present"]
        with self.assertRaises(RecordError):
            validate_record(self.record)

    def test_nonfinite_metadata_rejected(self):
        self.record["arbitrary"] = float("nan")
        with self.assertRaises(RecordError):
            evaluate_record(self.record)


if __name__ == "__main__":
    unittest.main()
