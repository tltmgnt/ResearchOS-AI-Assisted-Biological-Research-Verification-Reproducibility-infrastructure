import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from researchos_bio import RecordError
from researchos_bio.artifacts import verify_artifacts

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.manifest = {
            "schema_version": "1.0", "protocol_id": "synthetic-control-check-v1",
            "protocol_version": "pilot-1", "software_version": "0.1.0",
            "environment": {"python": "3.11", "platform": "synthetic"},
            "random_seed": 123,
            "artifacts": [
                {"evidence_id": "ev-01", "path": "a.txt"},
                {"evidence_id": "ev-02", "path": "b.txt"},
            ],
        }
        for index, name in enumerate(("a.txt", "b.txt")):
            data = f"synthetic artifact {index}".encode()
            (self.root / name).write_bytes(data)
            self.record["evidence"][index]["artifact_sha256"] = hashlib.sha256(data).hexdigest()

    def test_match(self):
        result = verify_artifacts(self.record, self.manifest, self.root)
        self.assertTrue(result["all_artifacts_verified"])
        self.assertEqual([x["status"] for x in result["artifacts"]], ["match", "match"])

    def test_tampering(self):
        (self.root / "b.txt").write_text("tampered")
        self.assertFalse(verify_artifacts(self.record, self.manifest, self.root)["all_artifacts_verified"])

    def test_missing_file(self):
        (self.root / "a.txt").unlink()
        self.assertEqual(verify_artifacts(self.record, self.manifest, self.root)["artifacts"][0]["status"], "missing")

    def test_reject_traversal(self):
        self.manifest["artifacts"][0]["path"] = "../outside"
        with self.assertRaises(RecordError):
            verify_artifacts(self.record, self.manifest, self.root)

    def test_reject_symlink(self):
        (self.root / "a.txt").unlink()
        (self.root / "a.txt").symlink_to(self.root / "b.txt")
        with self.assertRaises(RecordError):
            verify_artifacts(self.record, self.manifest, self.root)

    def test_missing_evidence_mapping(self):
        self.manifest["artifacts"].pop()
        with self.assertRaises(RecordError):
            verify_artifacts(self.record, self.manifest, self.root)

    def test_manifest_version_mismatch(self):
        self.manifest["protocol_version"] = "other"
        with self.assertRaises(RecordError):
            verify_artifacts(self.record, self.manifest, self.root)


if __name__ == "__main__":
    unittest.main()
