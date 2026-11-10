"""Offline curriculum answer key. Synthetic checks, never operational approval."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for base in (ROOT, ROOT / "src", ROOT / "layer-b"):
    sys.path.insert(0, str(base))
CASES = []

def check(name, actual, expected):
    passed = actual == expected
    CASES.append({"case": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")

def rejects(name, call, error=ValueError):
    try:
        call()
    except error:
        check(name, error.__name__, error.__name__)
    else:
        raise AssertionError(f"{name}: expected {error.__name__}")

def sample(path):
    return json.loads((ROOT / path).read_text())



def run():
    from researchos_bio.core import evaluate_record, verify_report, RecordError
    data = sample("examples/synthetic_record.json")
    r = evaluate_record(data)
    check("exact report replays", verify_report(data,r), True)
    check("independent reproduction never inferred", all(x["independent_replication_verified"] is False for x in r["decisions"]), True)
    changed = copy.deepcopy(r); changed["report_sha256"] = "0"*64
    check("edited report rejected", verify_report(data,changed), False)
    bad = copy.deepcopy(data); bad["claims"][0]["evidence_ids"].append("missing")
    rejects("foreign evidence link rejected", lambda: evaluate_record(bad), RecordError)
    check("metadata does not promote declared statuses", [x["current_status"] for x in r["decisions"]], [x["status"] for x in data["claims"]])

if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--verify"]):
        raise SystemExit("Usage: python curriculum/lab.py [--verify]")
    run()
    report = {"schema_version": 1, "status": "PASS", "case_count": len(CASES),
              "cases": CASES, "scope": "Synthetic curriculum checks only"}
    if sys.argv[1:] == ["--verify"]:
        expected = json.loads((Path(__file__).parent / "expected.json").read_text())
        if report != expected:
            raise AssertionError("Observed answers differ from curriculum/expected.json")
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
