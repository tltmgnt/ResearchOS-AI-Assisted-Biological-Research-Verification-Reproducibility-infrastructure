import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_STORED

from researchos_bio.audit_export import export_verified_audit_package
from researchos_bio.audit_verify import append_custody_event, verify_audit_package
from researchos_bio.core import RecordError, sha256_data


class AuditVerifyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "timing.csv"
        self.source.write_bytes(b"synthetic time,10\n")
        data = self.source.read_bytes()
        payload = {"report_version": "1.0", "source_evidence": [{
            "evidence_id": "timing", "role": "raw_timing",
            "sha256": hashlib.sha256(data).hexdigest()}]}
        dossier = {**payload, "report_sha256": sha256_data(payload)}
        self.package = self.root / "audit.zip"
        self.index = export_verified_audit_package(
            dossier, self.root, {"timing": "timing.csv"}, self.package)
        self.sha = self.index["package_sha256"]

    def verify(self):
        return verify_audit_package(self.package, self.sha)

    def test_valid_export_verifies(self):
        result = self.verify()
        self.assertEqual(result["verified_artifacts"], 1)
        self.assertFalse(result["custodian_identity_verified"])
        self.assertFalse(result["scientific_replication_verified"])

    def test_wrong_package_hash_rejected(self):
        with self.assertRaises(RecordError):
            verify_audit_package(self.package, "0" * 64)

    def test_modified_zip_rejected(self):
        with self.package.open("ab") as f:
            f.write(b"tamper")
        with self.assertRaises(RecordError):
            self.verify()

    def test_size_limit_rejected(self):
        with self.assertRaises(RecordError):
            verify_audit_package(self.package, self.sha, max_total_bytes=5)

    def test_unexpected_member_rejected_even_with_new_outer_digest(self):
        with ZipFile(self.package, "a", compression=ZIP_STORED) as z:
            z.writestr("unexpected.txt", b"bad")
        new_sha = hashlib.sha256(self.package.read_bytes()).hexdigest()
        with self.assertRaises(RecordError):
            verify_audit_package(self.package, new_sha)

    def test_artifact_content_change_rejected_with_new_outer_digest(self):
        with ZipFile(self.package, "r") as z:
            original = {n: z.read(n) for n in z.namelist()}
        original["artifacts/timing.csv"] = b"fake"
        with ZipFile(self.package, "w", compression=ZIP_STORED) as z:
            for name in sorted(original):
                z.writestr(name, original[name])
        new_sha = hashlib.sha256(self.package.read_bytes()).hexdigest()
        with self.assertRaises(RecordError):
            verify_audit_package(self.package, new_sha)

    def test_custody_append_and_chain(self):
        event = {"custodian_id": "operator-1", "action": "created",
                 "timestamp": "2026-11-03T10:00:00Z", "note": "synthetic"}
        chain = append_custody_event([], event, self.sha)
        self.assertEqual(len(chain), 1)
        second = {**event, "action": "verified"}
        chain = append_custody_event(chain, second, self.sha)
        self.assertEqual(chain[1]["previous_event_sha256"], chain[0]["event_sha256"])

    def test_custody_tampering_rejected(self):
        event = {"custodian_id": "operator-1", "action": "created",
                 "timestamp": "2026-11-03T10:00:00Z", "note": "synthetic"}
        chain = append_custody_event([], event, self.sha)
        chain[0]["note"] = "changed"
        with self.assertRaises(RecordError):
            append_custody_event(chain, event, self.sha)

    def test_custody_wrong_package_rejected(self):
        event = {"custodian_id": "operator-1", "action": "created",
                 "timestamp": "2026-11-03T10:00:00Z", "note": "synthetic"}
        chain = append_custody_event([], event, self.sha)
        with self.assertRaises(RecordError):
            append_custody_event(chain, event, "0" * 64)

    def test_invalid_custody_action_rejected(self):
        event = {"custodian_id": "operator-1", "action": "delete",
                 "timestamp": "2026-11-03T10:00:00Z", "note": "synthetic"}
        with self.assertRaises(RecordError):
            append_custody_event([], event, self.sha)


if __name__ == "__main__":
    unittest.main()
