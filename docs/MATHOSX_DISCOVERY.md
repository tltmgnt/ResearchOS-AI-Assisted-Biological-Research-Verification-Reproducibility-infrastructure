# MathOS × local discovery — ResearchOS-AI-Assisted-Biological-Research-Verification-Reproducibility-infrastructure

This optional offline research adapter copies the bounded [MathOS × discovery engine](https://github.com/tltmgnt/MathOS/pull/39). It explores **56 generic mathematical questions** (seven frontiers, four directions, two depths) and tests exact finite causal abstraction and GF(2) contradiction examples. It does **not** verify domain scientific/medical/operational effects, new mathematics, or theorem proofs. All outputs remain NOT_CERTIFIED.

`python -m unittest discover -s tests -p 'test_mathosx_discovery.py' -v`

`python -m mathosx.discovery --limit 16`

A human reviewer can adjust research priorities via `python -m mathosx.discovery --rate-question causal-abstraction:invent:research --outcome useful --evidence-ref review/example-1 --reviewer reviewer-id`, then review/commit `mathosx/feedback.v1.json`. The score is a heuristic for question usefulness—not mathematical correctness. The workflow is PR/manual-only, read-only, with no secrets, external model calls, automatic code modification, merges, or physical decisions. Adapt and validate mathematical examples before asserting relevance to ResearchOS-AI-Assisted-Biological-Research-Verification-Reproducibility-infrastructure.
