import copy
import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.pilot_comparison import evaluate_pilot_comparison


class PilotComparisonTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"schema_version": "1.0", "metric": "audit_reconstruction_minutes",
                     "comparison_design": "paired", "minimum_pairs": 2,
                     "registered_at": "2026-11-03T09:00:00Z",
                     "protocol_id": "synthetic-audit-timing-v1"}
        self.observations = {"schema_version": "1.0", "plan_sha256": sha256_data(self.plan),
                             "pairs": [
                                 {"case_id": "synthetic-1", "baseline_minutes": 20,
                                  "researchos_minutes": 10, "evaluator_id": "synthetic-evaluator"},
                                 {"case_id": "synthetic-2", "baseline_minutes": 30,
                                  "researchos_minutes": 15, "evaluator_id": "synthetic-evaluator"},
                             ]}

    def check(self):
        return evaluate_pilot_comparison(self.plan, self.observations)

    def test_descriptive_metrics_not_causality(self):
        result = self.check()
        self.assertTrue(result["minimum_sample_size_met"])
        self.assertEqual(result["observed_time_reduction_fraction"], 0.5)
        self.assertEqual(result["median_paired_difference_minutes"], 12.5)
        self.assertFalse(result["causal_effect_established"])
        self.assertFalse(result["independent_evaluation_verified"])
        self.assertEqual(result, self.check())

    def test_plan_tampering_rejected(self):
        self.plan["minimum_pairs"] = 3
        with self.assertRaises(RecordError):
            self.check()

    def test_missing_pairs_reported(self):
        self.observations["pairs"] = self.observations["pairs"][:1]
        self.assertFalse(self.check()["minimum_sample_size_met"])

    def test_duplicate_case_rejected(self):
        self.observations["pairs"][1]["case_id"] = "synthetic-1"
        with self.assertRaises(RecordError):
            self.check()

    def test_negative_duration_rejected(self):
        self.observations["pairs"][0]["baseline_minutes"] = -1
        with self.assertRaises(RecordError):
            self.check()

    def test_nan_rejected(self):
        self.observations["pairs"][0]["researchos_minutes"] = float("nan")
        with self.assertRaises(RecordError):
            self.check()

    def test_zero_duration_rejected(self):
        self.observations["pairs"][0]["researchos_minutes"] = 0
        with self.assertRaises(RecordError):
            self.check()

    def test_boolean_duration_rejected(self):
        self.observations["pairs"][0]["researchos_minutes"] = True
        with self.assertRaises(RecordError):
            self.check()

    def test_no_pairs_does_not_divide_by_zero(self):
        self.observations["pairs"] = []
        result = self.check()
        self.assertIsNone(result["observed_time_reduction_fraction"])
        self.assertFalse(result["minimum_sample_size_met"])

    def test_time_increase_is_reported(self):
        self.observations["pairs"][0]["researchos_minutes"] = 40
        result = self.check()
        self.assertLess(result["observed_time_reduction_fraction"], 0.5)

    def test_wrong_metric_rejected(self):
        self.plan["metric"] = "biological_truth"
        self.observations["plan_sha256"] = sha256_data(self.plan)
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
