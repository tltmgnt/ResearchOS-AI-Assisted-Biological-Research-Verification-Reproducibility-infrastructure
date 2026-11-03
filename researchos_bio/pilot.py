"""Phase 9 pilot-readiness assessment: software metrics, not scientific claims."""
from __future__ import annotations

from typing import Any

from .core import RecordError, sha256_data


def assess_pilot(packets: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    """Score complete synthetic/real administrative packets without certifying science."""
    if not isinstance(packets, list) or not packets:
        raise RecordError("packets must be a nonempty list")
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0":
        raise RecordError("pilot policy schema_version must be 1.0")
    threshold = policy.get("minimum_packet_completion_rate")
    min_claims = policy.get("minimum_claims")
    if type(threshold) not in (float, int) or not 0 <= threshold <= 1:
        raise RecordError("minimum_packet_completion_rate must be between 0 and 1")
    if type(min_claims) is not int or min_claims < 1:
        raise RecordError("minimum_claims must be a positive integer")
    seen = set()
    results = []
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("report_version") != "1.0":
            raise RecordError("each packet must be a versioned assurance report")
        if packet.get("report_sha256") != sha256_data({k: v for k, v in packet.items() if k != "report_sha256"}):
            raise RecordError("packet report fingerprint does not match contents")
        claims = packet.get("claims")
        if not isinstance(claims, list):
            raise RecordError("packet claims must be a list")
        for item in claims:
            if not isinstance(item, dict) or not isinstance(item.get("claim_id"), str):
                raise RecordError("claim item must have claim_id")
            key = (packet.get("record_sha256"), item["claim_id"])
            if key in seen:
                raise RecordError("duplicate record/claim in pilot")
            seen.add(key)
            if type(item.get("assurance_packet_complete")) is not bool:
                raise RecordError("assurance_packet_complete must be boolean")
            if item.get("scientific_claim_validated") is not False:
                raise RecordError("pilot cannot certify scientific validity")
            results.append({"record_sha256": packet.get("record_sha256"),
                            "claim_id": item["claim_id"],
                            "assurance_packet_complete": item["assurance_packet_complete"]})
    total = len(results)
    complete = sum(item["assurance_packet_complete"] for item in results)
    rate = complete / total if total else 0.0
    ready = total >= min_claims and rate >= threshold
    payload = {
        "report_version": "1.0", "pilot_policy_sha256": sha256_data(policy),
        "packet_report_sha256s": [x["report_sha256"] for x in packets],
        "claims_assessed": total, "complete_packets": complete,
        "completion_rate": rate, "minimum_claims": min_claims,
        "minimum_packet_completion_rate": float(threshold),
        "software_pilot_gate_passed": ready,
        "scientific_pilot_validated": False,
        "disclaimer": "Software pilot readiness only. Hashes are integrity checks, not authentication of upstream data or scientific evidence.",
    }
    return {**payload, "report_sha256": sha256_data(payload)}
