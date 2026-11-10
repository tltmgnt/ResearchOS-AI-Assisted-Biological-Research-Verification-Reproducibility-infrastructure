# Topology compatibility and curriculum v2 — ResearchOS-AI-Assisted-Biological-Research-Verification-Reproducibility-infrastructure

Version 2 adapts the explicit-molecular-graph teaching pattern to this repository's actual role. This is documentation and a learning/decision framework; it introduces no mathematical engine, runtime dependency or operational permission.

## Repository decision

| Question | Repository-specific answer |
| --- | --- |
| Architectural role | application research |
| Minimum useful mathematics | Typed provenance/dependency graphs |
| Relationships to preserve | Claims, protocols, artifacts and version-bound review evidence |
| Concrete operation / capstone | Alter one synthetic artifact and trace the impact on its record and review binding |
| Necessity and scope boundary | Content integrity and supplied reviewer declarations do not establish experimental reproduction |

The decision is a source-based recommendation, not measured proof that a new specialty improves this repository. Start with the existing implementation and compare any proposed abstraction against a simpler alternative.

## Six-criterion compatibility scorecard

Complete one scorecard per proposed candidate and per concrete operation. Leave unmeasured entries unknown. Scores are human judgments from 0 (no fit) to 5 (strong evidenced fit); unknown is not zero. Do not sum an incomplete card. A total out of 30 is a heuristic, not adoption approval, and feasibility or necessity can veto a high total.

| Criterion | Score | Required evidence |
| --- | --- | --- |
| Structural compatibility | Not yet scored | Map the repository objects and the relationships above without losing direction, labels, units or missingness. |
| Transformation support | Not yet scored | Demonstrate the capstone operation on accepted and rejected inputs. |
| Invariant preservation | Not yet scored | State the property preserved and supply a counterexample or perturbation. |
| Computational feasibility | Not yet scored | Measure size, time and memory on bounded fixtures; record limits. |
| Integration compatibility | Not yet scored | Verify existing schemas, APIs and neighboring contracts remain compatible. |
| Mathematical necessity | Not yet scored | Compare with typed provenance/dependency graphs and explain the additional capability, if any. |

## Curriculum

Prerequisites: basic programming, sets, functions and graph vocabulary. Work in six competency-gated sessions, approximately 60–90 minutes each; empirical evaluation is a separate research activity.

| Session | Learning objective | Exercise | Completion evidence |
| --- | --- | --- | --- |
| 1. Model | Identify claims, protocols, artifacts and version-bound review evidence. | Draw a minimal valid example and one excluded relationship. | Annotated object/relation inventory with explicit assumptions. |
| 2. Contract | Distinguish schema validity from substantive correctness. | Trace validation and propose malformed, missing and boundary inputs. | Input-to-rejection table grounded in current source. |
| 3. Operation | Explain typed provenance/dependency graphs. | Alter one synthetic artifact and trace the impact on its record and review binding. | Hand trace compared with existing software, or a clearly labeled specification when no runtime exists. |
| 4. Preservation | State what a transformation must preserve. | Rename identifiers, reorder records, then alter one meaningful relation; predict each effect under the actual contract. | Separate invariant, expected change and unsupported transformation. |
| 5. Comparison | Justify mathematical necessity and cost. | Complete the six-criterion card for the existing approach and one proposed alternative; record unknowns honestly. | Evidence-backed recommendation with baseline and explicit veto conditions. |
| 6. Reproduction | Communicate the bounded result. | Reproduce the capstone using existing offline fixtures and record software version, inputs, outputs and limitations. | Reviewable notebook or report distinguishing computation, replay, independent evaluation and authorization. |

## Source-linked reading laboratory

The table is a guided selection of source lines, not an assertion that the whole repository is covered. Line numbers refer to the inspected source blob `46da339487a2ad3eb7a6c31850e6038a60a23102` in [researchos_bio/core.py](../../researchos_bio/core.py). Recheck anchors after source changes.

| Line | Statement | Learning check |
| --- | --- | --- |
| [20](../../researchos_bio/core.py#L20) | `class RecordError(ValueError):` | State the input/output contract and trace one normal and one failing case. |
| [24](../../researchos_bio/core.py#L24) | `def canonical_bytes(value: Any) -> bytes:` | State the input/output contract and trace one normal and one failing case. |
| [26](../../researchos_bio/core.py#L26) | `return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")` | Predict the returned value and distinguish a computed result from authorization. |
| [28](../../researchos_bio/core.py#L28) | `raise RecordError("Record is not canonically serializable") from exc` | Construct the triggering input and explain why rejection preserves the contract. |
| [31](../../researchos_bio/core.py#L31) | `def sha256_data(value: Any) -> str:` | State the input/output contract and trace one normal and one failing case. |
| [32](../../researchos_bio/core.py#L32) | `return hashlib.sha256(canonical_bytes(value)).hexdigest()` | Explain the exact bytes bound by the digest and why hashing does not authenticate the source. |
| [35](../../researchos_bio/core.py#L35) | `def _nonempty(value: Any, name: str) -> str:` | State the input/output contract and trace one normal and one failing case. |
| [37](../../researchos_bio/core.py#L37) | `raise RecordError(f"{name} must be a nonempty string")` | Construct the triggering input and explain why rejection preserves the contract. |
| [38](../../researchos_bio/core.py#L38) | `return value` | Predict the returned value and distinguish a computed result from authorization. |
| [41](../../researchos_bio/core.py#L41) | `def _id_sequence(items: Any, label: str) -> tuple[str, ...]:` | State the input/output contract and trace one normal and one failing case. |
| [43](../../researchos_bio/core.py#L43) | `raise RecordError(f"{label} must be a list of nonempty strings")` | Construct the triggering input and explain why rejection preserves the contract. |
| [45](../../researchos_bio/core.py#L45) | `raise RecordError(f"{label} must not contain duplicates")` | Construct the triggering input and explain why rejection preserves the contract. |
| [46](../../researchos_bio/core.py#L46) | `return tuple(items)` | Predict the returned value and distinguish a computed result from authorization. |
| [49](../../researchos_bio/core.py#L49) | `def _iso_time(value: Any, name: str) -> str:` | State the input/output contract and trace one normal and one failing case. |
| [54](../../researchos_bio/core.py#L54) | `raise RecordError(f"{name} must be ISO-8601") from exc` | Construct the triggering input and explain why rejection preserves the contract. |
| [56](../../researchos_bio/core.py#L56) | `raise RecordError(f"{name} must include a timezone offset")` | Construct the triggering input and explain why rejection preserves the contract. |
| [57](../../researchos_bio/core.py#L57) | `return value` | Predict the returned value and distinguish a computed result from authorization. |
| [61](../../researchos_bio/core.py#L61) | `class Evidence:` | State the input/output contract and trace one normal and one failing case. |
| [74](../../researchos_bio/core.py#L74) | `def parse(cls, data: dict[str, Any]) -> "Evidence":` | State the input/output contract and trace one normal and one failing case. |
| [76](../../researchos_bio/core.py#L76) | `raise RecordError("evidence item must be an object")` | Construct the triggering input and explain why rejection preserves the contract. |
| [81](../../researchos_bio/core.py#L81) | `raise RecordError("artifact_sha256 must be a lowercase SHA-256 hex digest")` | Construct the triggering input and explain why rejection preserves the contract. |
| [84](../../researchos_bio/core.py#L84) | `raise RecordError("evidence verdict must be pass, fail or uncertain")` | Construct the triggering input and explain why rejection preserves the contract. |
| [88](../../researchos_bio/core.py#L88) | `raise RecordError("evidence cannot claim independence from itself")` | Construct the triggering input and explain why rejection preserves the contract. |
| [91](../../researchos_bio/core.py#L91) | `raise RecordError("notes must be a string")` | Construct the triggering input and explain why rejection preserves the contract. |
## Assessment and verification

A learner must explain the model, trace the capstone, identify a counterexample and state the scope boundary. Assess these four competencies equally; a numerical score cannot compensate for an unsupported scientific or operational claim.

Relevant existing checks:

- [tests/test_artifacts.py](../../tests/test_artifacts.py)
- [tests/test_assurance.py](../../tests/test_assurance.py)
- [tests/test_attestations.py](../../tests/test_attestations.py)

Follow [README](../../README.md) for environment and installed-package instructions. Read scripts before execution; source-reading exercises do not authorize provider calls, model downloads, live orders, hardware actions or messages. Synthetic fixtures establish software behavior only. This documentation change does not report those exercises as already executed.

## Interoperability and adoption gate

Retain explicit domain contracts. Shared assurance records should refer to domain evidence and its assumptions rather than relabeling graph reachability, homology, statistical calibration and epistemic acceptance as interchangeable quantities. The canonical ResearchOs controller remains owned by ResearchOs; this curriculum does not create another controller fork.

Adopt additional mathematics only after a versioned experiment demonstrates a useful operation, the scorecard has evidence, the simpler baseline is inadequate and existing conformance checks remain satisfied. Content integrity and supplied reviewer declarations do not establish experimental reproduction.
