# Phase 13 — Pilot Results Integrity and Statistical Reporting

## Scope

This phase reconciles a preregistered **case accounting frame** against observed paired audit-reconstruction times, explicitly reports missing and excluded cases, and computes a descriptive normal-approximation interval for the mean paired time difference.

## Inputs and usage

Use the same `plan.json` and `observations.json` from Phase 12, plus `accounting.json`:

```json
{
  "schema_version": "1.0",
  "plan_sha256": "<canonical SHA-256 of plan.json>",
  "cases": [
    {"case_id": "case-1", "status": "completed"},
    {"case_id": "case-2", "status": "missing", "reason": "evaluator did not submit times"},
    {"case_id": "case-3", "status": "excluded", "reason": "preregistered exclusion criterion"}
  ]
}
```

```sh
python -m researchos_bio pilot-statistics plan.json observations.json accounting.json --output statistics.json
```

Every completed case must have exactly one paired observation, and no observation may lack a completed case entry. Missing and excluded cases require explicit reasons. All three inputs are fingerprinted in the report.

## Interpretation

The report includes case counts, completion fraction, minimum sample size gate, mean and sample standard deviation of paired differences, standard error and a **normal-approximation 95% interval** computed as mean ± 1.96 × standard error. It does not use a Student t critical value or a small-sample exact method, and does not handle clustering or repeated measures by evaluator. No interval is produced for fewer than two complete pairs.

This is an *illustrative descriptive interval*, not a confirmatory confidence interval suitable for regulatory or scientific claims. It assumes independent, representative paired differences, which the software cannot verify. Selective missingness, exclusions, evaluator learning, and small sample sizes can make the interval misleading. No p-value, causal claim, or external evaluator identity verification is implemented.

## Independent review requirements

- Verify the full predeclared case list against source records, not only submitted observations.
- Review all missing and excluded cases and compare results under plausible missingness assumptions.
- Check timing start/stop rules, evaluator independence, order allocation, baseline comparability and protocol deviations.
- Predefine appropriate inference methods (e.g., clustered or paired bootstrap with externally justified design) before collecting real pilot data.
- Preserve raw observations, provenance, original preregistration timestamps, and external evaluator sign-off.

A passing software sample-size gate is **not** scientific replication, proof of independence, or demonstrated real-world performance improvement.
