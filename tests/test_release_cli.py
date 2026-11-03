"""Regression tests for the release-candidate command-line contract."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from researchos_bio.__main__ import main
from researchos_bio.core import sha256_data


class ReleaseCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, obj):
        path = self.root / name
        path.write_text(json.dumps(obj), encoding="utf-8")
        return str(path)

    def call(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(argv)

    def test_pilot_cli_no_record_arg(self):
        payload = {"report_version": "1.0", "record_sha256": "synthetic",
                   "claims": [{"claim_id": "c1", "assurance_packet_complete": True,
                               "scientific_claim_validated": False}]}
        packet = {**payload, "report_sha256": sha256_data(payload)}
        packets = self.write("packets.json", [packet])
        policy = self.write("policy.json", {
            "schema_version": "1.0", "minimum_claims": 1,
            "minimum_packet_completion_rate": 1.0})
        self.assertEqual(self.call(["assess-pilot", packets, policy]), 0)

    def test_external_audit_cli_no_record_arg(self):
        payload = {"report_version": "1.0", "software_pilot_gate_passed": False}
        pilot = self.write("pilot.json", {**payload, "report_sha256": sha256_data(payload)})
        registry = self.write("registry.json", {"schema_version": "1.0", "keys": []})
        report = json.loads(Path(pilot).read_text())
        bundle = self.write("bundle.json", {
            "schema_version": "1.0", "pilot_report_sha256": sha256_data(report),
            "decisions": []})
        self.assertEqual(self.call(["verify-external-audit", pilot, registry, bundle]), 2)

    def test_invalid_json_returns_one(self):
        path = self.root / "broken.json"
        path.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.call(["assess-pilot", str(path), str(path)]), 1)

    def test_missing_file_returns_one(self):
        self.assertEqual(self.call(["assess-pilot", "missing.json", "missing-policy.json"]), 1)


if __name__ == "__main__":
    unittest.main()
