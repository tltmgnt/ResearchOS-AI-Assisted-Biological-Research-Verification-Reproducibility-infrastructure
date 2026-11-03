"""CLI: python -m researchos_bio evaluate RECORD.json --output REPORT.json"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .core import RecordError, evaluate_record, verify_report
from .artifacts import verify_artifacts
from .reviews import evaluate_reviews, verify_review_report
from .attestations import verify_attestations
from .governance import evaluate_governance
from .benchmarks import evaluate_benchmark
from .assurance import assemble_assurance
from .pilot import assess_pilot
from .external_audit import verify_external_audit
from .pilot_comparison import evaluate_pilot_comparison
from .pilot_statistics import evaluate_pilot_statistics
from .evaluation_dossier import assemble_evaluation_dossier
from .audit_export import export_verified_audit_package
from .audit_verify import verify_audit_package, append_custody_event
from .signed_custody import verify_signed_custody
from .registry_lifecycle import verify_registry_lifecycle


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
    att = sub.add_parser("verify-attestations", help="verify signed reviews against trusted public keys")
    att.add_argument("record")
    att.add_argument("bundle")
    att.add_argument("trust_registry")
    att.add_argument("attestations")
    att.add_argument("--output", help="write JSON signature verification report")
    gov = sub.add_parser("evaluate-governance", help="evaluate enrolled signed-review quorum")
    gov.add_argument("record")
    gov.add_argument("bundle")
    gov.add_argument("trust_registry")
    gov.add_argument("attestations")
    gov.add_argument("policy")
    gov.add_argument("--output", help="write JSON governance report")
    benchmark = sub.add_parser("evaluate-benchmark", help="evaluate preregistered numeric comparisons")
    benchmark.add_argument("record")
    benchmark.add_argument("plan")
    benchmark.add_argument("outcomes")
    benchmark.add_argument("--output", help="write JSON benchmark report")
    assurance = sub.add_parser("assemble-assurance", help="recompute cross-layer assurance packet")
    assurance.add_argument("record")
    assurance.add_argument("manifest")
    assurance.add_argument("artifact_root")
    assurance.add_argument("bundle")
    assurance.add_argument("trust_registry")
    assurance.add_argument("attestations")
    assurance.add_argument("policy")
    assurance.add_argument("plan")
    assurance.add_argument("outcomes")
    assurance.add_argument("--output", help="write JSON assurance packet")
    pilot = sub.add_parser("assess-pilot", help="score assurance packet completion for a pilot")
    pilot.add_argument("packets", help="JSON array of assurance reports")
    pilot.add_argument("policy", help="JSON pilot readiness policy")
    pilot.add_argument("--output", help="write JSON pilot report")
    external = sub.add_parser("verify-external-audit", help="verify signed external evaluator decisions")
    external.add_argument("pilot_report")
    external.add_argument("audit_trust_registry")
    external.add_argument("audit_bundle")
    external.add_argument("--minimum-organizations", type=int, default=2)
    external.add_argument("--output", help="write JSON external audit report")
    compare = sub.add_parser("compare-pilot", help="describe paired audit reconstruction times")
    compare.add_argument("plan")
    compare.add_argument("observations")
    compare.add_argument("--output", help="write JSON paired comparison report")
    stats = sub.add_parser("pilot-statistics", help="reconcile missing cases and describe paired uncertainty")
    stats.add_argument("plan")
    stats.add_argument("observations")
    stats.add_argument("accounting")
    stats.add_argument("--output", help="write JSON pilot statistics report")
    dossier = sub.add_parser("assemble-evaluation-dossier", help="link pilot, comparison, statistics and audit reports")
    dossier.add_argument("pilot_report")
    dossier.add_argument("comparison_report")
    dossier.add_argument("statistics_report")
    dossier.add_argument("audit_report")
    dossier.add_argument("source_evidence")
    dossier.add_argument("--output", help="write JSON evaluation dossier")
    audit_export = sub.add_parser("export-audit-package", help="verify source files and create portable audit ZIP")
    audit_export.add_argument("dossier")
    audit_export.add_argument("source_root")
    audit_export.add_argument("artifact_paths", help="JSON map of evidence IDs to relative source paths")
    audit_export.add_argument("destination", help="new ZIP file; existing files are not overwritten")
    audit_export.add_argument("--max-file-bytes", type=int, default=100000000)
    verify_zip = sub.add_parser("verify-audit-package", help="independently verify a portable audit ZIP")
    verify_zip.add_argument("package")
    verify_zip.add_argument("expected_sha256")
    verify_zip.add_argument("--max-total-bytes", type=int, default=500000000)
    verify_zip.add_argument("--output", help="write JSON verification report")
    custody = sub.add_parser("append-custody-event", help="append a hash-linked custody declaration")
    custody.add_argument("events", help="existing JSON array of events")
    custody.add_argument("event", help="JSON event declaration")
    custody.add_argument("package_sha256")
    custody.add_argument("--output", required=True, help="write new JSON custody event array")
    signed = sub.add_parser("verify-signed-custody", help="verify Ed25519 custody signatures and chain anchor")
    signed.add_argument("events")
    signed.add_argument("signatures")
    signed.add_argument("registry")
    signed.add_argument("package_sha256")
    signed.add_argument("anchor")
    signed.add_argument("--output", help="write JSON signature verification report")
    lifecycle = sub.add_parser("verify-registry-lifecycle", help="verify historical custody key policy and registry checkpoints")
    lifecycle.add_argument("snapshots")
    lifecycle.add_argument("events")
    lifecycle.add_argument("signatures")
    lifecycle.add_argument("package_sha256")
    lifecycle.add_argument("custody_anchor")
    lifecycle.add_argument("assignments")
    lifecycle.add_argument("pinned_registry_head_sha256")
    lifecycle.add_argument("--output", help="write JSON registry lifecycle report")
    args = parser.parse_args(argv)
    try:
        record = _read_json(args.record) if hasattr(args, "record") else None
        if args.command == "evaluate":
            result = evaluate_record(record)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
        elif args.command == "verify-registry-lifecycle":
            result = verify_registry_lifecycle(
                _read_json(args.snapshots), _read_json(args.events),
                _read_json(args.signatures), args.package_sha256,
                _read_json(args.custody_anchor), _read_json(args.assignments),
                args.pinned_registry_head_sha256)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_assigned_signatures_valid"] else 2
        elif args.command == "verify-signed-custody":
            result = verify_signed_custody(
                _read_json(args.events), _read_json(args.signatures),
                _read_json(args.registry), args.package_sha256,
                _read_json(args.anchor))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_events_cryptographically_signed"] else 2
        elif args.command == "verify-audit-package":
            result = verify_audit_package(args.package, args.expected_sha256,
                                          max_total_bytes=args.max_total_bytes)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0
        elif args.command == "append-custody-event":
            result = append_custody_event(_read_json(args.events), _read_json(args.event),
                                          args.package_sha256)
            Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                                         encoding="utf-8")
            return 0
        elif args.command == "export-audit-package":
            result = export_verified_audit_package(
                _read_json(args.dossier), args.source_root,
                _read_json(args.artifact_paths), args.destination,
                max_file_bytes=args.max_file_bytes)
            print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
            return 0
        elif args.command == "assemble-evaluation-dossier":
            result = assemble_evaluation_dossier(
                _read_json(args.pilot_report), _read_json(args.comparison_report),
                _read_json(args.statistics_report), _read_json(args.audit_report),
                _read_json(args.source_evidence))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["administrative_dossier_complete"] else 2
        elif args.command == "pilot-statistics":
            result = evaluate_pilot_statistics(
                _read_json(args.plan), _read_json(args.observations),
                _read_json(args.accounting))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["minimum_sample_size_met"] else 2
        elif args.command == "compare-pilot":
            result = evaluate_pilot_comparison(_read_json(args.plan), _read_json(args.observations))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["minimum_sample_size_met"] else 2
        elif args.command == "verify-external-audit":
            result = verify_external_audit(
                _read_json(args.pilot_report), _read_json(args.audit_trust_registry),
                _read_json(args.audit_bundle), args.minimum_organizations)
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["administrative_external_audit_accepted"] else 2
        elif args.command == "assess-pilot":
            result = assess_pilot(_read_json(args.packets), _read_json(args.policy))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["software_pilot_gate_passed"] else 2
        elif args.command == "assemble-assurance":
            result = assemble_assurance(
                record, _read_json(args.manifest), args.artifact_root,
                _read_json(args.bundle), _read_json(args.trust_registry),
                _read_json(args.attestations), _read_json(args.policy),
                _read_json(args.plan), _read_json(args.outcomes))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_assurance_packets_complete"] else 2
        elif args.command == "evaluate-benchmark":
            result = evaluate_benchmark(record, _read_json(args.plan), _read_json(args.outcomes))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_reported_results_within_tolerance"] else 2
        elif args.command == "evaluate-governance":
            result = evaluate_governance(record, _read_json(args.bundle),
                                         _read_json(args.trust_registry),
                                         _read_json(args.attestations), _read_json(args.policy))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
        elif args.command == "verify-attestations":
            result = verify_attestations(record, _read_json(args.bundle),
                                         _read_json(args.trust_registry), _read_json(args.attestations))
            output = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
            else:
                print(output, end="")
            return 0 if result["all_reviews_signed"] else 2
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
