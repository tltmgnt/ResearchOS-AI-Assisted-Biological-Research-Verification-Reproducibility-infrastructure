import copy
import math
import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.pilot_statistics import evaluate_pilot_statistics


class PilotStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"schema_version": "1.0", "metric": "audit_reconstruction_minutes",
                     "comparison_design": "paired", "minimum_pairs": 2,
                     "registered_at": "2026-11-03T09:00:00Z",
                     "protocol_id": "synthetic-timing-v1"}
        self.observations = {"schema_version": "1.0", "plan_sha256": sha256_data(self.plan),
                             "pairs": [
                                 {"case_id": "a", "baseline_minutes": 20,
                                  "researchos_minutes": 10, "evaluator_id": "demo"},
                                 {"case_id": "b", "baseline_minutes": 30,
                                  "researchos_minutes": 15, "evaluator_id": "demo"}]}
        self.accounting = {"schema_version": "1.0", "plan_sha256": sha256_data(self.plan),
                           "cases": [{"case_id": "a", "status": "completed"},
                                     {"case_id": "b", "status": "completed"},
                                     {"case_id": "c", "status": "missing", "reason": "no timing recorded"},
                                     {"case_id": "d", "status": "excluded", "reason": "protocol deviation"}]}

    def check(self):
        return evaluate_pilot_statistics(self.plan, self.observations, self.accounting)

    def test_case_accounting_and_interval(self):
        result = self.check()
        self.assertEqual(result["planned_cases"], 4)
        self.assertEqual(result["completed_cases"], 2)
        self.assertEqual(result["completion_fraction"], 0.5)
        self.assertEqual(result["mean_paired_difference_minutes"], 12.5)
        self.assertEqual(len(result["normal_approximation_95pct_interval_minutes"]), 2)
        self.assertFalse(result["interval_is_confirmatory"])
        self.assertFalse(result["scientific_replication_verified"])
        self.assertEqual(result, self.check())

    def test_missing_reason_required(self):
        self.accounting["cases"][2].pop("reason")
        with self.assertRaises(RecordError):
            self.check()

    def test_observed_case_not_accounted(self):
        self.accounting["cases"][1]["status"] = "missing"
        self.accounting["cases"][1]["reason"] = "incorrect"
        with self.assertRaises(RecordError):
            self.check()

    def test_duplicate_case_rejected(self):
        self.accounting["cases"][2]["case_id"] = "a"
        with self.assertRaises(RecordError):
            self.check()

    def test_plan_binding(self):
        self.accounting["plan_sha256"] = "0" * 64
        with self.assertRaises(RecordError):
            self.check()

    def test_empty_accounting_rejected(self):
        self.accounting["cases"] = []
        with self.assertRaises(RecordError):
            self.check()

    def test_one_pair_has_no_interval(self):
        self.observations["pairs"].pop()
        self.accounting["cases"][1]["status"] = "missing"
        self.accounting["cases"][1]["reason"] = "not recorded"
        result = self.check()
        self.assertIsNone(result["normal_approximation_95pct_interval_minutes"])
        self.assertFalse(result["minimum_sample_size_met"])

    def test_zero_pairs_has_no_interval(self):
        self.observations["pairs"] = []
        for item in self.accounting["cases"][:2]:
            item["status"] = "missing"
            item["reason"] = "no data"
        self.assertIsNone(self.check()["mean_paired_difference_minutes"])

    def test_all_missing_does_not_claim_science(self):
        self.observations["pairs"] = []
        for item in self.accounting["cases"][:2]:
            item["status"] = "missing"
            item["reason"] = "not observed"
        result = self.check()
        self.assertFalse(result["independent_evaluation_verified"])
        self.assertEqual(result["completion_fraction"], 0.0)

    def test_bad_case_status_rejected(self):
        self.accounting["cases"][0]["status"] = "verified"
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
