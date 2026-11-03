"""CLI: python -m researchos_bio evaluate RECORD.json --output REPORT.json"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .core import RecordError, evaluate_record, verify_report
from .artifacts import verify_artifacts
from .reviews import evaluate_reviews, verify_review_report


def _read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="researchos_bio")
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate", help="validate and describe a claim/evidence record")
    ev.add_argument("record")
    ev.add_argument("--output", help="write canonical JSON report to this path")
    verify = sub.add_parser("verify", help="recompute and verify an evaluation report")
    verify.add_argument("record")
    verify.add_argument("report")
    art = sub.add_parser("verify-artifacts", help="verify local evidence files against SHA-256 manifest")
    art.add_argument("record")
    art.add_argument("manifest")
    art.add_argument("--root", required=True, help="directory containing local artifacts")
    art.add_argument("--output", help="write JSON integrity report")
    review = sub.add_parser("review", help="assess self-declared independent reviews")
    review.add_argument("record")
    review.add_argument("bundle")
    review.add_argument("--output", help="write JSON review report")
    review_verify = sub.add_parser("verify-review", help="recompute review report")
    review_verify.add_argument("record")
    review_verify.add_argument("bundle")
    review_verify.add_argument("report")
    args = parser.parse_args(argv)
    try:
        record = _read_json(args.record)
        if args.command == "evaluate":
            result = evaluate_record(record)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
        elif args.command == "review":
            result = evaluate_reviews(record, _read_json(args.bundle))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
        elif args.command == "verify-review":
            if not verify_review_report(record, _read_json(args.bundle), _read_json(args.report)):
                raise RecordError("review report does not match recomputed evaluation")
            print("Review report verified against record and bundle")
        elif args.command == "verify-artifacts":
            result = verify_artifacts(record, _read_json(args.manifest), args.root)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_artifacts_verified"] else 2
        else:
            report = _read_json(args.report)
            if not verify_report(record, report):
                raise RecordError("report does not match recomputed evaluation")
            print("Report verified against record")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
