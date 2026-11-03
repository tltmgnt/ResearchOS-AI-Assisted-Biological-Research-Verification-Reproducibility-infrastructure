# ResearchOS Release Candidate — Operational Readiness

## Scope and status

Release-candidate checks cover **software packaging, regression tests, deterministic reports, CLI compatibility, and synthetic end-to-end behavior**. They do not certify biological science, independently verify reviewer identities, or guarantee supply-chain integrity.

## Required release gates

1. Confirm Phase 6–10 dependency pull requests have been merged or explicitly approved for a release branch; never release a stacked feature branch as if it were main.
2. Verify both GitHub Actions workflows pass on the **exact intended release commit**, including Python 3.11, 3.12 and 3.13.
3. Build source and wheel distributions, run `twine check`, and install the wheel in a clean environment.
4. Execute `python -m unittest discover -s tests -v` and `python examples/end_to_end_demo.py`.
5. Verify CLI entry points `evaluate`, `verify-artifacts`, `review`, `verify-attestations`, `evaluate-governance`, `evaluate-benchmark`, `assemble-assurance`, `assess-pilot`, and `verify-external-audit`.
6. Archive commit SHA, wheel/sdist SHA-256, Python version, dependency lock or resolved package versions, test logs, and negative-control outcomes.
7. Obtain external security review of input size limits, symlink/TOCTOU handling, trust-registry provenance, key revocation timing, and audit log retention before deployment.

## Operational controls

- Keep private signing keys outside the repository and CI logs. Use approved key custody and rotation procedures.
- Treat all submitted JSON, artifacts, manifests and reviewer declarations as untrusted. Restrict file access and runtime permissions; do not process sensitive data in the synthetic demo.
- Pin dependencies and review transitive dependency changes for production. The prototype currently specifies a bounded cryptography version range, **not** a fully locked dependency graph.
- Record trust registry approvals and revocations in an externally controlled, access-restricted audit system.
- Protect release branches and require independent code review; use signed provenance attestations for published artifacts if deployment requires them.
- Do not interpret SHA-256 checks, cryptographic signatures, synthetic benchmark success, or an administrative audit quorum as verified scientific reproduction.

## Publication decision

A release candidate is ready for **external software evaluation** only when the exact release commit has green CI, reproducible installation, reviewed dependencies, and documented known limitations. Production readiness and independent biological validation are separate decisions.
