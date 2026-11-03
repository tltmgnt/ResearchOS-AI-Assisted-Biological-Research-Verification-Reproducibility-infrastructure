import copy
import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.evaluation_dossier import assemble_evaluation_dossier


def sealed(payload):
    return {**payload, "report_sha256": sha256_data(payload)}


class EvaluationDossierTests(unittest.TestCase):
    def setUp(self):
        self.pilot = sealed({"report_version": "1.0", "software_pilot_gate_passed": True})
        self.comparison = sealed({
            "report_version": "1.0", "plan_sha256": "plan",
            "observations_sha256": "observations", "observed_time_reduction_fraction": 0.2})
        self.stats = sealed({
            "report_version": "1.0",
            "descriptive_report_sha256": self.comparison["report_sha256"],
            "plan_sha256": "plan", "observations_sha256": "observations",
            "planned_cases": 2, "completed_cases": 2,
            "missing_cases": [], "excluded_cases": [],
            "minimum_sample_size_met": True,
            "normal_approximation_95pct_interval_minutes": [-2.0, 10.0]})
        self.audit = sealed({
            "report_version": "1.0",
            "pilot_report_sha256": sha256_data(self.pilot),
            "administrative_external_audit_accepted": True})
        self.evidence = [{"evidence_id": "synthetic-raw-1", "role": "raw_timing",
                          "sha256": "a" * 64}]

    def check(self):
        return assemble_evaluation_dossier(
            self.pilot, self.comparison, self.stats, self.audit, self.evidence)

    def reseal(self, obj):
        obj["report_sha256"] = sha256_data({
            k: v for k, v in obj.items() if k != "report_sha256"})

    def test_complete_dossier_not_scientific_validation(self):
        report = self.check()
        self.assertTrue(report["administrative_dossier_complete"])
        self.assertFalse(report["source_artifact_bytes_verified"])
        self.assertFalse(report["independent_scientific_replication_verified"])
        self.assertEqual(report, self.check())

    def test_pilot_tamper_rejected(self):
        self.pilot["software_pilot_gate_passed"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_wrong_comparison_binding(self):
        self.stats["descriptive_report_sha256"] = "0" * 64
        self.reseal(self.stats)
        with self.assertRaises(RecordError):
            self.check()

    def test_wrong_audit_binding(self):
        self.audit["pilot_report_sha256"] = "0" * 64
        self.reseal(self.audit)
        with self.assertRaises(RecordError):
            self.check()

    def test_missing_case_blocks_completeness(self):
        self.stats["completed_cases"] = 1
        self.stats["missing_cases"] = [{"case_id": "c2", "reason": "missing timing"}]
        self.reseal(self.stats)
        self.assertFalse(self.check()["administrative_dossier_complete"])

    def test_exclusion_blocks_completeness(self):
        self.stats["completed_cases"] = 1
        self.stats["excluded_cases"] = [{"case_id": "c2", "reason": "deviation"}]
        self.reseal(self.stats)
        self.assertFalse(self.check()["administrative_dossier_complete"])

    def test_case_count_mismatch_rejected(self):
        self.stats["completed_cases"] = 1
        self.reseal(self.stats)
        with self.assertRaises(RecordError):
            self.check()

    def test_duplicate_evidence_rejected(self):
        self.evidence.append(copy.deepcopy(self.evidence[0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_bad_digest_rejected(self):
        self.evidence[0]["sha256"] = "not-a-digest"
        with self.assertRaises(RecordError):
            self.check()

    def test_no_source_inventory_blocks_completeness(self):
        self.evidence = []
        self.assertFalse(self.check()["administrative_dossier_complete"])

    def test_audit_rejection_blocks_completeness(self):
        self.audit["administrative_external_audit_accepted"] = False
        self.reseal(self.audit)
        self.assertFalse(self.check()["administrative_dossier_complete"])

    def test_sample_size_failure_blocks_completeness(self):
        self.stats["minimum_sample_size_met"] = False
        self.reseal(self.stats)
        self.assertFalse(self.check()["administrative_dossier_complete"])


if __name__ == "__main__":
    unittest.main()
