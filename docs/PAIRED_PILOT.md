# Phase 12 — Paired Pilot Evaluation Protocol

## Goal

Measure **audit reconstruction time** for the same administrative research cases using a documented baseline workflow and ResearchOS. This is a software-process performance metric, not an independent biological replication rate.

## Preregistration

Before observing results, freeze and archive a plan with:
- protocol ID, registration timestamp and SHA-256;
- paired comparison design and minimum number of paired cases;
- a fixed start/stop definition for audit reconstruction minutes;
- allocation/crossover order, evaluator training, handling of timeouts and missing cases;
- the baseline procedure and ResearchOS commit/environment;
- the full case set and exclusion rules.

Use a prospective, independent evaluator cohort where possible. Randomize baseline/ResearchOS order across cases and counterbalance to reduce learning effects. Store independent evidence for evaluator identity and session timestamps outside ResearchOS.

## Input schema

Plan:

```json
{"schema_version":"1.0","protocol_id":"pilot-audit-timing-v1","registered_at":"2026-11-03T09:00:00Z","comparison_design":"paired","metric":"audit_reconstruction_minutes","minimum_pairs":10}
```

Observations:

```json
{"schema_version":"1.0","plan_sha256":"<canonical SHA-256 of plan>","pairs":[{"case_id":"case-1","evaluator_id":"evaluator-1","baseline_minutes":35,"researchos_minutes":21}]}
```

Use the same `case_id` for baseline and ResearchOS measurements. All times must be positive finite numbers. Duplicate case IDs are rejected.

```sh
python -m researchos_bio compare-pilot plan.json observations.json --output comparison.json
```

## Reported metrics

- Number of paired cases and whether the preregistered minimum sample size is met.
- Total baseline and ResearchOS minutes.
- Descriptive observed fractional reduction: `(sum baseline - sum ResearchOS) / sum baseline`.
- Median within-case time difference.
- Case-level times and differences, with deterministic report fingerprints.

**No inferential significance test, confidence interval, randomized causal claim or independently verified evaluator identity is implemented.** A positive observed reduction in synthetic or uncontrolled data is not an achieved real-world performance improvement.

## External evaluation acceptance

An independent evaluator should verify session timing evidence, case matching, completeness, protocol compliance, baseline comparability, exclusions, and order effects. A prospective study must define the statistical analysis plan before collecting outcomes. Archive raw timing evidence and any deviations. Do not infer biological validity from shorter audit time.
