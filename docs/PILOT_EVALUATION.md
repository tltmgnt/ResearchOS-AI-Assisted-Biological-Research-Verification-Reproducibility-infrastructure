# Phase 9 — External Pilot Evaluation Protocol

## Scope

This is a **software assurance pilot**, not a biological or clinical validation study. Use synthetic or properly authorized non-sensitive datasets. External evaluators must review the underlying protocols and provenance separately.

## Preregister before the pilot

1. Freeze the ResearchOS commit, dependency versions, benchmark plans, reviewer governance policy, and test cases.
2. Record the number of claims and a completion-rate threshold in a versioned pilot policy.
3. Define pass/fail cases before running them: intact artifacts, modified artifacts, revoked signing keys, disputed reviews, missing outcomes, and outside-tolerance results.
4. Assign external evaluators and establish independent identity and protocol checks outside this repository.

## Reproducible execution

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python examples/end_to_end_demo.py
python -m researchos_bio assess-pilot assurance-packets.json pilot-policy.json --output pilot-report.json
```

Pilot policy example:

```json
{"schema_version":"1.0","minimum_claims":10,"minimum_packet_completion_rate":0.95}
```

`assurance-packets.json` is a JSON array of complete Phase 7 assurance report objects (each with its own `report_sha256`). These are *administrative* packets.

## Acceptance gates

- All planned tests run with archived stdout, stderr, tool versions and git commit.
- The pilot software gate meets the preregistered minimum number of claims and completion rate.
- Negative controls fail closed; modified artifacts, revoked keys, missing signatures, challenges, and out-of-tolerance outcomes cannot produce complete assurance packets.
- Independent evaluators inspect a sample of input files, reviewer identity evidence, signatures, timestamps, and protocol adherence.
- Report failures and exclusions, not just successful cases.

## Metrics and limitations

The implemented metric is **administrative assurance-packet completion rate**. The system does not yet measure independently validated scientific discoveries, reproduction rates, reduction in audit reconstruction time, or discovery throughput. These require an externally designed empirical study with baseline comparison and adequate sample size. A passing software gate is **not** proof of biological validity or DARPA endorsement.
