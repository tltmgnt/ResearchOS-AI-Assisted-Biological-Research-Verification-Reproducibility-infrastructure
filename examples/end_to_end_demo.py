"""Executable end-to-end synthetic ResearchOS demonstration.

No biological material or real human reviewer identity is involved.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from researchos_bio.assurance import assemble_assurance
from researchos_bio.attestations import attestation_payload
from researchos_bio.core import sha256_data


def synthetic_case(root: Path) -> dict:
    """Build deterministic evidence inputs; demo signing keys are ephemeral."""
    original = Path(__file__).with_name("synthetic_record.json")
    record = json.loads(original.read_text(encoding="utf-8"))
    root.mkdir(parents=True, exist_ok=True)
    mapping = []
    for i, evidence in enumerate(record["evidence"]):
        name = f"synthetic-control-{i+1}.txt"
        data = f"SYNTHETIC CONTROL {i+1}: value={100+i}\n".encode()
        (root / name).write_bytes(data)
        evidence["artifact_sha256"] = hashlib.sha256(data).hexdigest()
        mapping.append({"evidence_id": evidence["evidence_id"], "path": name})
    manifest = {
        "schema_version": "1.0", "protocol_id": "synthetic-control-check-v1",
        "protocol_version": record["protocol_version"],
        "software_version": record["software_version"],
        "environment": {"platform": "synthetic", "language": "Python"},
        "random_seed": 0, "artifacts": mapping,
    }
    reviews = []
    trusted = []
    signatures = []
    enrolled = []
    for i in range(2):
        reviewer, org, rid, kid = f"synthetic-reviewer-{i+1}", f"synthetic-lab-{i+1}", f"review-{i+1}", f"key-{i+1}"
        review = {
            "review_id": rid, "claim_id": "claim-synthetic-1",
            "reviewer_id": reviewer, "organization_id": org,
            "reviewed_at": "2026-11-03T12:00:00Z", "decision": "confirm",
            "reproduction_method": "illustrative synthetic comparison",
            "protocol_id": "synthetic-control-check-v1",
            "evidence_ids": ["ev-01", "ev-02"],
            "independent_of_original_team": True,
            "raw_data_available": True, "protocol_followed": True,
            "conflicts_of_interest": [],
        }
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        trusted.append({"key_id": kid, "reviewer_id": reviewer,
                        "public_key_b64": base64.b64encode(public).decode()})
        signatures.append({"review_id": rid, "key_id": kid,
                           "signature_b64": base64.b64encode(
                               key.sign(attestation_payload(record, review))).decode()})
        enrolled.append({"reviewer_id": reviewer, "organization_id": org, "approved": True})
        reviews.append(review)
    bundle = {"schema_version": "1.0", "record_sha256": sha256_data(record), "reviews": reviews}
    registry = {"schema_version": "1.0", "keys": trusted}
    attestations = {"schema_version": "1.0", "signatures": signatures}
    policy = {"schema_version": "1.0", "minimum_distinct_organizations": 2,
              "revoked_key_ids": [], "enrolled_reviewers": enrolled}
    plan = {
        "schema_version": "1.0", "record_sha256": sha256_data(record),
        "registered_at": "2026-11-03T09:00:00Z",
        "comparisons": [{
            "claim_id": "claim-synthetic-1", "protocol_id": "synthetic-control-check-v1",
            "metric": "synthetic_signal", "unit": "arbitrary_units",
            "analysis_method": "absolute_difference",
            "reference_value": 100.0, "absolute_tolerance": 5.0,
        }],
    }
    outcomes = {"schema_version": "1.0", "plan_sha256": sha256_data(plan), "results": [{
        "claim_id": "claim-synthetic-1", "run_id": "synthetic-run-1",
        "operator_id": "synthetic-operator", "organization_id": "synthetic-lab-1",
        "artifact_evidence_id": "ev-01", "observed_at": "2026-11-03T13:00:00Z",
        "observed_value": 103.0,
    }]}
    return {"record": record, "manifest": manifest, "root": str(root), "bundle": bundle,\n            "registry": registry, "attestations": attestations, "policy": policy,\n            "plan": plan, "outcomes": outcomes}


def run(case: dict) -> dict:
    return assemble_assurance(
        case["record"], case["manifest"], case["root"],
        case["bundle"], case["registry"], case["attestations"],
        case["policy"], case["plan"], case["outcomes"],
    )


def main() -> None:
    with TemporaryDirectory(prefix="researchos-synthetic-") as tmp:
        case = synthetic_case(Path(tmp))
        positive = run(case)
        assert positive["all_assurance_packets_complete"]
        assert not positive["scientific_validation_performed"]
        negative = copy.deepcopy(case)
        negative["policy"]["revoked_key_ids"] = ["key-2"]
        revoked = run(negative)
        assert not revoked["all_assurance_packets_complete"]
        (Path(case["root"]) / "synthetic-control-1.txt").write_text("TAMPERED")
        tampered = run(case)
        assert not tampered["all_assurance_packets_complete"]
        print(json.dumps({
            "scenario": "synthetic-only", "complete_case": positive,
            "revoked_key_case": revoked, "tampered_artifact_case": tampered,
        }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
