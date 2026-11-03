import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from researchos_bio.audit_export import export_verified_audit_package
from researchos_bio.core import RecordError, sha256_data


class AuditExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "evidence").mkdir()
        self.data = b"synthetic raw timing evidence\n"
        (self.root / "evidence" / "timing.csv").write_bytes(self.data)
        payload = {"report_version": "1.0", "administrative_dossier_complete": True,
                   "source_evidence": [{"evidence_id": "raw-1", "role": "raw_timing",
                                       "sha256": hashlib.sha256(self.data).hexdigest()}]}
        self.dossier = {**payload, "report_sha256": sha256_data(payload)}
        self.paths = {"raw-1": "evidence/timing.csv"}
        self.destination = self.root / "audit.zip"

    def export(self, dest=None):
        return export_verified_audit_package(
            self.dossier, self.root, self.paths, dest or self.destination)

    def test_zip_contains_verified_bytes_and_manifest(self):
        report = self.export()
        self.assertTrue(report["source_bytes_verified"])
        self.assertFalse(report["scientific_replication_verified"])
        with ZipFile(self.destination) as z:
            self.assertEqual(z.read("artifacts/evidence/timing.csv"), self.data)
            self.assertEqual(json.loads(z.read("index.json"))["artifact_count"], 1)

    def test_reproducible_zip(self):
        first = self.export()
        second = self.export(self.root / "other.zip")
        self.assertEqual(first["package_sha256"], second["package_sha256"])

    def test_modified_bytes_rejected(self):
        (self.root / "evidence" / "timing.csv").write_bytes(b"tampered")
        with self.assertRaises(RecordError):
            self.export()

    def test_traversal_rejected(self):
        self.paths["raw-1"] = "../outside.csv"
        with self.assertRaises(RecordError):
            self.export()

    def test_absolute_path_rejected(self):
        self.paths["raw-1"] = "/tmp/unsafe"
        with self.assertRaises(RecordError):
            self.export()

    def test_symlink_rejected(self):
        (self.root / "evidence" / "alias.csv").symlink_to("timing.csv")
        self.paths["raw-1"] = "evidence/alias.csv"
        with self.assertRaises(RecordError):
            self.export()

    def test_oversized_file_rejected(self):
        with self.assertRaises(RecordError):
            export_verified_audit_package(self.dossier, self.root, self.paths,
                                          self.destination, max_file_bytes=3)

    def test_missing_mapping_rejected(self):
        self.paths = {}
        with self.assertRaises(RecordError):
            self.export()

    def test_tampered_dossier_rejected(self):
        self.dossier["administrative_dossier_complete"] = False
        with self.assertRaises(RecordError):
            self.export()

    def test_overwrite_rejected(self):
        self.export()
        with self.assertRaises(RecordError):
            self.export()

    def test_duplicate_paths_rejected(self):
        item = dict(self.dossier["source_evidence"][0])
        item["evidence_id"] = "raw-2"
        self.dossier["source_evidence"].append(item)
        self.dossier["report_sha256"] = sha256_data({
            k: v for k, v in self.dossier.items() if k != "report_sha256"})
        self.paths["raw-2"] = self.paths["raw-1"]
        with self.assertRaises(RecordError):
            self.export()


if __name__ == "__main__":
    unittest.main()
