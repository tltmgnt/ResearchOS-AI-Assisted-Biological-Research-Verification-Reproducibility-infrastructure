import base64
import copy
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from researchos_bio.audit_verify import append_custody_event
from researchos_bio.core import RecordError, sha256_data
from researchos_bio.registry_lifecycle import verify_registry_lifecycle
from researchos_bio.signed_custody import custody_signature_payload


def snapshot(revision, previous, keys):
    payload = {"schema_version": "1.0", "revision": revision,
               "previous_snapshot_sha256": previous,
               "effective_at": f"2026-11-0{revision}T10:00:00Z",
               "change_reason": "synthetic key lifecycle",
               "registry": {"schema_version": "1.0", "keys": keys}}
    return {**payload, "snapshot_sha256": sha256_data(payload)}


class RegistryLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.package = "a" * 64
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.key = {"key_id": "key-1", "custodian_id": "operator-1",
                    "approved": True, "revoked": False,
                    "public_key_b64": base64.b64encode(public).decode()}
        self.snapshots = [snapshot(1, "0" * 64, [self.key])]
        event = {"custodian_id": "operator-1", "action": "created",
                 "timestamp": "2026-11-03T10:00:00Z", "note": "synthetic"}
        self.events = append_custody_event([], event, self.package)
        self.signatures = [{"sequence": 1, "key_id": "key-1",
                            "signature_b64": base64.b64encode(
                                self.private.sign(custody_signature_payload(self.events[0]))
                            ).decode()}]
        self.assignments = [{"sequence": 1, "registry_revision": 1}]
        self.anchor = {"schema_version": "1.0", "package_sha256": self.package,
                       "sequence": 1, "event_sha256": self.events[0]["event_sha256"]}

    def check(self):
        return verify_registry_lifecycle(
            self.snapshots, self.events, self.signatures, self.package,
            self.anchor, self.assignments, self.snapshots[-1]["snapshot_sha256"])

    def add_revocation(self):
        key = {**self.key, "revoked": True}
        self.snapshots.append(snapshot(2, self.snapshots[-1]["snapshot_sha256"], [key]))

    def test_historical_signature_valid_before_revocation(self):
        self.add_revocation()
        report = self.check()
        self.assertTrue(report["all_assigned_signatures_valid"])
        self.assertFalse(report["external_registry_head_authenticated"])
        self.assertFalse(report["scientific_replication_verified"])

    def test_signature_invalid_under_revoked_revision(self):
        self.add_revocation()
        self.assignments[0]["registry_revision"] = 2
        self.assertEqual(self.check()["events"][0]["signature_status"], "revoked_key")

    def test_tampered_snapshot_rejected(self):
        self.snapshots[0]["change_reason"] = "tampered"
        with self.assertRaises(RecordError):
            self.check()

    def test_bad_registry_head_rejected(self):
        with self.assertRaises(RecordError):
            verify_registry_lifecycle(
                self.snapshots, self.events, self.signatures, self.package,
                self.anchor, self.assignments, "0" * 64)

    def test_duplicate_assignment_rejected(self):
        self.assignments.append(copy.deepcopy(self.assignments[0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_unknown_revision_rejected(self):
        self.assignments[0]["registry_revision"] = 99
        with self.assertRaises(RecordError):
            self.check()

    def test_reassigned_key_rejected(self):
        self.snapshots.append(snapshot(2, self.snapshots[0]["snapshot_sha256"],
                                       [{**self.key, "custodian_id": "impostor"}]))
        with self.assertRaises(RecordError):
            self.check()

    def test_revoked_key_cannot_be_reactivated(self):
        self.add_revocation()
        self.snapshots.append(snapshot(3, self.snapshots[-1]["snapshot_sha256"], [self.key]))
        with self.assertRaises(RecordError):
            self.check()

    def test_invalid_signature_fails_closed(self):
        self.signatures[0]["signature_b64"] = base64.b64encode(b"0" * 64).decode()
        self.assertFalse(self.check()["all_assigned_signatures_valid"])

    def test_missing_signature_fails_closed(self):
        self.signatures = []
        self.assertFalse(self.check()["all_assigned_signatures_valid"])

    def test_duplicate_signature_rejected(self):
        self.signatures.append(copy.deepcopy(self.signatures[0]))
        with self.assertRaises(RecordError):
            self.check()

    def test_anchor_mismatch_rejected(self):
        self.anchor["event_sha256"] = "0" * 64
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
