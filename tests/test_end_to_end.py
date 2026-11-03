import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
from end_to_end_demo import run, synthetic_case  # noqa: E402


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.case = synthetic_case(Path(self.tmp.name))

    def test_full_positive_path(self):
        result = run(self.case)
        self.assertTrue(result["all_assurance_packets_complete"])
        self.assertFalse(result["scientific_validation_performed"])
        self.assertFalse(result["claims"][0]["scientific_claim_validated"])

    def test_revoked_key_fails(self):
        self.case["policy"]["revoked_key_ids"] = ["key-1"]
        self.assertFalse(run(self.case)["all_assurance_packets_complete"])

    def test_artifact_tamper_fails(self):
        (Path(self.case["root"]) / "synthetic-control-1.txt").write_text("changed")
        self.assertFalse(run(self.case)["all_assurance_packets_complete"])

    def test_outside_tolerance_fails(self):
        self.case["outcomes"]["results"][0]["observed_value"] = 120
        self.assertFalse(run(self.case)["all_assurance_packets_complete"])

    def test_unsigned_review_fails(self):
        self.case["attestations"]["signatures"].pop()
        self.assertFalse(run(self.case)["all_assurance_packets_complete"])

    def test_challenge_fails(self):
        self.case["bundle"]["reviews"][0]["decision"] = "challenge"
        self.assertFalse(run(self.case)["all_assurance_packets_complete"])

    def test_report_replay_stable(self):
        self.assertEqual(run(self.case), run(self.case))


if __name__ == "__main__":
    unittest.main()
