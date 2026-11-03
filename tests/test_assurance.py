"""Synthetic adversarial tests. These do not verify biological experiments."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from researchos_bio.assurance import assess_assurance
from researchos_bio.attestations import attestation_payload
from researchos_bio.core import RecordError, sha256_data

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_record.json"


class AssuranceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.record = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        artifacts = []
        for index, evidence in enumerate(self.record["evidence"]):
            path = f"artifact-{index}.txt"
            content = f"illustrative bytes {index}".encode()
            (self.root / path).write_bytes(content)
            evidence["artifact_sha256"] = hashlib.sha256(content).hexdigest()
            artifacts.append({"evidence_id": evidence["evidence_id"], "path": path})
        self.manifest = {
            "schema_version": "1.0", "protocol_id": "synthetic-control-check-v1",
            "protocol_version": "pilot-1", "software_version": "0.1.0",
            "environment": {"python": "3.11"}, "random_seed": 19,
            "artifacts": artifacts,
        }
        self.review = {
            "review_id": "review-1", "claim_id": "claim-synthetic-1",
            "reviewer_id": "reviewer-1", "organization_id": "synthetic-reviewer",
            "reviewed_at": "2026-11-03T12:00:00Z", "decision": "confirm",
            "reproduction_method": "illustrative comparison only",
            "protocol_id": "synthetic-control-check-v1", "evidence_ids": ["ev-01"],
            "independent_of_original_team": True, "raw_data_available": True,
            "protocol_followed": True, "conflicts_of_interest": [],
        }
        self.bundle = {"schema_version": "1.0", "record_sha256": sha256_data(self.record),
                       "reviews": [self.review]}
        key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.registry = {"schema_version": "1.0", "keys": [{
            "key_id": "key-1", "reviewer_id": "reviewer-1",
            "public_key_b64": base64.b64encode(pub).decode("ascii"),
        }]}
        self.signatures = {"schema_version": "1.0", "signatures": [{
            "review_id": "review-1", "key_id": "key-1",
            "signature_b64": base64.b64encode(key.sign(
                attestation_payload(self.record, self.review))).decode("ascii"),
        }]}

    def assess(self):
        return assess_assurance(self.record, self.manifest, self.root, self.bundle,
                                self.registry, self.signatures)

    def test_ready_remains_advisory_and_deterministic(self):
        result = self.assess()
        self.assertEqual(result, self.assess())
        item = result["claims"][0]
        self.assertEqual(item["advisory_gate"], "ready_for_manual_adjudication")
        self.assertEqual(item["current_status"], "unverified")
        for flag in ("biological_validity_verified", "independence_verified",
                     "independent_replication_verified", "automatic_status_promotion_permitted"):
            self.assertFalse(item[flag])

    def test_unsigned_review_blocks(self):
        self.signatures["signatures"] = []
        self.assertEqual(self.assess()["claims"][0]["advisory_gate"], "needs_review")

    def test_invalid_signature_blocks(self):
        self.signatures["signatures"][0]["signature_b64"] = base64.b64encode(b"x" * 64).decode()
        self.assertEqual(self.assess()["claims"][0]["advisory_gate"], "needs_review")

    def test_local_artifact_tampering_blocks(self):
        (self.root / "artifact-1.txt").write_text("tampered")
        self.assertEqual(self.assess()["claims"][0]["advisory_gate"], "needs_evidence")

    def test_recorded_failure_contests(self):
        self.record["evidence"][1]["verdict"] = "fail"
        self.bundle["record_sha256"] = sha256_data(self.record)
        self.assertEqual(self.assess()["claims"][0]["advisory_gate"], "contested")

    def test_unsigned_challenge_still_requires_adjudication(self):
        self.review["decision"] = "challenge"
        item = self.assess()["claims"][0]
        self.assertEqual(item["advisory_gate"], "contested")
        self.assertEqual(item["challenge_review_ids"], ["review-1"])

    def test_same_operator_cannot_pass_review_gate(self):
        self.review["reviewer_id"] = "demo-operator"
        self.registry["keys"][0]["reviewer_id"] = "demo-operator"
        result = self.assess()["claims"][0]
        self.assertEqual(result["advisory_gate"], "needs_review")
        self.assertEqual(result["shared_operator_review_ids"], ["review-1"])

    def test_conflict_disclosure_blocks(self):
        self.review["conflicts_of_interest"] = ["prior collaboration"]
        self.assertEqual(self.assess()["claims"][0]["advisory_gate"], "needs_review")

    def test_protocol_mismatch_rejected(self):
        self.manifest["protocol_id"] = "different"
        with self.assertRaises(RecordError):
            self.assess()

    def test_record_binding_rejected(self):
        self.record["claims"][0]["statement"] = "altered"
        with self.assertRaises(RecordError):
            self.assess()


if __name__ == "__main__":
    unittest.main()
