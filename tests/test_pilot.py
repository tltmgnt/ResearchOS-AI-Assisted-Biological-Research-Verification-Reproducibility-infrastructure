import copy
import unittest

from researchos_bio.core import RecordError, sha256_data
from researchos_bio.pilot import assess_pilot


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"schema_version": "1.0", "minimum_claims": 1,
                       "minimum_packet_completion_rate": 1.0}
        payload = {"report_version": "1.0", "record_sha256": "synthetic-record",
                   "claims": [{"claim_id": "c1", "assurance_packet_complete": True,
                               "scientific_claim_validated": False}]}
        self.packet = {**payload, "report_sha256": sha256_data(payload)}

    def check(self):
        return assess_pilot([self.packet], self.policy)

    def test_pass_is_not_scientific_validation(self):
        result = self.check()
        self.assertTrue(result["software_pilot_gate_passed"])
        self.assertFalse(result["scientific_pilot_validated"])
        self.assertEqual(result, self.check())

    def test_incomplete_packet_fails(self):
        self.packet["claims"][0]["assurance_packet_complete"] = False
        self.packet["report_sha256"] = sha256_data({k:v for k,v in self.packet.items() if k!="report_sha256"})
        self.assertFalse(self.check()["software_pilot_gate_passed"])

    def test_tampered_packet_rejected(self):
        self.packet["claims"][0]["assurance_packet_complete"] = False
        with self.assertRaises(RecordError):
            self.check()

    def test_duplicate_packet_rejected(self):
        with self.assertRaises(RecordError):
            assess_pilot([self.packet, copy.deepcopy(self.packet)], self.policy)

    def test_minimum_claims(self):
        self.policy["minimum_claims"] = 2
        self.assertFalse(self.check()["software_pilot_gate_passed"])

    def test_invalid_threshold(self):
        self.policy["minimum_packet_completion_rate"] = 1.5
        with self.assertRaises(RecordError):
            self.check()

    def test_claim_cannot_be_certified(self):
        self.packet["claims"][0]["scientific_claim_validated"] = True
        self.packet["report_sha256"] = sha256_data({k:v for k,v in self.packet.items() if k!="report_sha256"})
        with self.assertRaises(RecordError):
            self.check()


if __name__ == "__main__":
    unittest.main()
