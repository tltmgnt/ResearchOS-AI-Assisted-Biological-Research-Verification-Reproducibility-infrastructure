import tempfile
from pathlib import Path
import unittest

from researchos_bio.core import RecordError
from researchos_bio.operations import evaluate_deployment_readiness, evaluate_monitoring_snapshot


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {
            "schema_version": "1.0", "environment": "staging",
            "release_commit": "a" * 40,
            "publisher_registry_pin_sha256": "b" * 64,
            "custody_registry_pin_sha256": "c" * 64,
            "external_audit_approval": True,
            "max_artifact_bytes": 1000000,
        }
        self.snapshot = {
            "schema_version": "1.0", "sample_id": "synthetic-sample",
            "verification_attempts": 12, "verification_failures": 0,
            "rejected_archive_inputs": 0, "unexpected_process_restarts": 0,
            "last_success_age_seconds": 15,
        }

    def test_preflight_passes_but_does_not_authorize_production(self):
        report = evaluate_deployment_readiness(self.config, self.root)
        self.assertTrue(report["operational_preflight_passed"])
        self.assertFalse(report["production_release_authorized"])
        self.assertFalse(report["external_audit_approval_authenticated"])
        self.assertFalse(report["deployment_performed"])
        self.assertEqual(report, evaluate_deployment_readiness(self.config, self.root))

    def test_missing_directory_fails_closed(self):
        self.assertFalse(evaluate_deployment_readiness(
            self.config, self.root / "missing")["operational_preflight_passed"])

    def test_symlinked_root_fails_closed(self):
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        self.assertFalse(evaluate_deployment_readiness(
            self.config, link)["operational_preflight_passed"])

    def test_missing_approval_fails(self):
        self.config["external_audit_approval"] = False
        self.assertFalse(evaluate_deployment_readiness(
            self.config, self.root)["operational_preflight_passed"])

    def test_placeholder_pin_fails(self):
        self.config["publisher_registry_pin_sha256"] = "0" * 64
        self.assertFalse(evaluate_deployment_readiness(
            self.config, self.root)["operational_preflight_passed"])

    def test_bad_maximum_rejected(self):
        self.config["max_artifact_bytes"] = -1
        with self.assertRaises(RecordError):
            evaluate_deployment_readiness(self.config, self.root)

    def test_unknown_config_field_rejected(self):
        self.config["secret"] = "never expose secrets"
        with self.assertRaises(RecordError):
            evaluate_deployment_readiness(self.config, self.root)

    def test_clean_snapshot_has_no_alert(self):
        report = evaluate_monitoring_snapshot(self.snapshot)
        self.assertFalse(report["any_alert"])
        self.assertFalse(report["monitoring_service_connected"])
        self.assertEqual(report, evaluate_monitoring_snapshot(self.snapshot))

    def test_verification_failure_alert(self):
        self.snapshot["verification_failures"] = 1
        self.assertTrue(evaluate_monitoring_snapshot(self.snapshot)["any_alert"])

    def test_unexpected_restart_critical(self):
        self.snapshot["unexpected_process_restarts"] = 1
        self.assertTrue(evaluate_monitoring_snapshot(self.snapshot)["critical_alert"])

    def test_stale_verification_critical(self):
        self.snapshot["last_success_age_seconds"] = 3601
        self.assertTrue(evaluate_monitoring_snapshot(self.snapshot)["critical_alert"])

    def test_no_activity_alert(self):
        self.snapshot["verification_attempts"] = 0
        self.assertTrue(evaluate_monitoring_snapshot(self.snapshot)["any_alert"])

    def test_invalid_metric_count_rejected(self):
        self.snapshot["verification_failures"] = 13
        with self.assertRaises(RecordError):
            evaluate_monitoring_snapshot(self.snapshot)

    def test_negative_metric_rejected(self):
        self.snapshot["rejected_archive_inputs"] = -1
        with self.assertRaises(RecordError):
            evaluate_monitoring_snapshot(self.snapshot)


if __name__ == "__main__":
    unittest.main()
