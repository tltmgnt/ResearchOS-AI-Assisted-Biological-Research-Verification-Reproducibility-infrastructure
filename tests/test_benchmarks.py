import copy
import json
import unittest
from pathlib import Path

from researchos_bio.benchmarks import evaluate_benchmark
from researchos_bio.core import RecordError, sha256_data

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text())
        self.plan = {
            "schema_version": "1.0", "record_sha256": sha256_data(self.record),
            "registered_at": "2026-11-03T09:00:00Z",
            "comparisons": [{
                "claim_id": "claim-synthetic-1", "protocol_id": "synthetic-control-check-v1",
                "metric": "synthetic_signal", "unit": "arbitrary_units",
                "analysis_method": "absolute_difference",
                "reference_value": 100.0, "absolute_tolerance": 5.0,
            }],
        }
        self.outcomes = {
            "schema_version": "1.0", "plan_sha256": sha256_data(self.plan),
            "results": [{
                "claim_id": "claim-synthetic-1", "run_id": "synthetic-run-1",
                "operator_id": "demo-operator", "organization_id": "demo-lab",
                "artifact_evidence_id": "ev-01", "observed_at": "2026-11-03T12:00:00Z",
                "observed_value": 103.0,
            }],
        }

    def check(self):
        return evaluate_benchmark(self.record, self.plan, self.outcomes)

    def test_within_tolerance_is_not_replication(self):
        result = self.check()
        self.assertTrue(result["all_reported_results_within_tolerance"])
        self.assertFalse(result["scientific_reproduction_verified"])
        self.assertFalse(result["comparisons"][0]["external_replication_verified"])

    def test_outside_tolerance(self):
        self.outcomes["results"][0]["observed_value"] = 110
        self.assertEqual(self.check()["comparisons"][0]["status"], "outside_tolerance")

    def test_missing_result(self):
        self.outcomes["results"] = []
        self.assertEqual(self.check()["comparisons"][0]["status"], "missing")

    def test_boundary_inclusive(self):
        self.outcomes["results"][0]["observed_value"] = 105
        self.assertTrue(self.check()["comparisons"][0]["within_tolerance"])

    def test_plan_tamper(self):
        self.plan["comparisons"][0]["absolute_tolerance"] = 10
        with self.assertRaises(RecordError):
            self.check()

    def test_record_tamper(self):
        self.record["claims"][0]["statement"] = "changed"
        with self.assertRaises(RecordError):
            self.check()

    def test_negative_tolerance(self):
        self.plan["comparisons"][0]["absolute_tolerance"] = -1
        self.outcomes["plan_sha256"] = sha256_data(self.plan)
        with self.assertRaises(RecordError):
            self.check()

    def test_nan_rejected(self):
        self.outcomes["results"][0]["observed_value"] = float("nan")
        with self.assertRaises(RecordError):
            self.check()

    def test_duplicate_result(self):
        self.outcomes["results"].append(copy.deepcopy(self.outcomes["results"][0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_timestamp_precedes_plan(self):
        self.outcomes["results"][0]["observed_at"] = "2026-11-02T12:00:00Z"
        with self.assertRaises(RecordError):
            self.check()

    def test_unknown_evidence(self):
        self.outcomes["results"][0]["artifact_evidence_id"] = "unknown"
        with self.assertRaises(RecordError):
            self.check()

    def test_wrong_protocol(self):
        self.plan["comparisons"][0]["protocol_id"] = "wrong"
        self.outcomes["plan_sha256"] = sha256_data(self.plan)
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
