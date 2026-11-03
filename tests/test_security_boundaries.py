"""Adversarial tests for Phase 20 archive input boundaries."""
import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
from zipfile import ZipFile, ZipInfo, ZIP_STORED

from researchos_bio.audit_export import export_verified_audit_package
from researchos_bio.audit_verify import verify_audit_package
from researchos_bio.core import RecordError, sha256_data


class SecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        data = b"synthetic evidence"
        (self.root / "source.txt").write_bytes(data)
        payload = {"report_version": "1.0", "source_evidence": [{
            "evidence_id": "e1", "role": "raw_timing",
            "sha256": hashlib.sha256(data).hexdigest()}]}
        self.dossier = {**payload, "report_sha256": sha256_data(payload)}
        self.zip = self.root / "audit.zip"
        self.result = export_verified_audit_package(
            self.dossier, self.root, {"e1": "source.txt"}, self.zip)

    def verify(self, **kwargs):
        return verify_audit_package(
            self.zip, hashlib.sha256(self.zip.read_bytes()).hexdigest(), **kwargs)

    def test_normal_package_still_verifies(self):
        self.assertTrue(self.verify()["source_artifact_bytes_verified"])

    def test_member_count_limit(self):
        with self.assertRaises(RecordError):
            self.verify(max_members=2)

    def test_metadata_limit(self):
        with self.assertRaises(RecordError):
            self.verify(max_metadata_bytes=10)

    def test_invalid_member_limit(self):
        with self.assertRaises(RecordError):
            self.verify(max_members=1)

    def test_invalid_metadata_limit(self):
        with self.assertRaises(RecordError):
            self.verify(max_metadata_bytes=0)

    def test_symlink_entry_rejected(self):
        with ZipFile(self.zip, "r") as z:
            contents = {info.filename: z.read(info.filename) for info in z.infolist()}
        with ZipFile(self.zip, "w", compression=ZIP_STORED) as z:
            for name, data in sorted(contents.items()):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = ((stat.S_IFLNK | 0o777) if name.startswith("artifacts/") else (stat.S_IFREG | 0o644)) << 16
                z.writestr(info, data)
        with self.assertRaises(RecordError):
            self.verify()

    def test_noncanonical_archive_path_rejected(self):
        with ZipFile(self.zip, "a") as z:
            z.writestr("artifacts/../injected", b"malicious")
        with self.assertRaises(RecordError):
            self.verify()

    def test_control_character_path_rejected(self):
        with ZipFile(self.zip, "a") as z:
            z.writestr("artifacts/control\nfile", b"malicious")
        with self.assertRaises(RecordError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
