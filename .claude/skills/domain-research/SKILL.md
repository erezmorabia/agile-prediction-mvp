---
name: domain-research
description: Aggregate-only XP conference evidence, manuscript generation, review, and sanitized release packaging. Use when modifying scripts/build_xp2027_*, scripts/package_xp2027_*, tests/test_xp2027_evidence.py, or submission/xp2027/.
---

# Domain: Research Submission

## Summary

The research domain converts the tested production `PolicyEngine` into a privacy-preserving, reproducible conference
submission. It freezes the estimand and comparisons before analysis, computes aggregate evidence without emitting team
identities, builds an eight-page preparation draft, and creates a scanned archive that excludes organizational source
data. It does not alter the production recommender.

## Data flows

- Evidence: reference workbook -> production data/ML components -> fixed case cohort -> selected blend and declared
  comparators -> team-cluster bootstrap -> aggregate JSON and Markdown.
- Paper: aggregate JSON + manuscript wording -> deterministic ReportLab build -> eight-page PDF -> page-count/text/render
  QA.
- Package: allowlisted manuscript, evidence, protocol, and artifact documentation -> confidentiality scan -> ZIP archive.

## Invariants

- Never write team names, row-level records, or raw workbook contents under `submission/` or `output/`.
- Use only information strictly available before each prediction baseline when scoring recommendations.
- The primary estimand is monthly macro Conditional Hit Rate@2 over complete global outcome windows.
- Preserve the frozen 121-case primary estimand; report the 120-case strict team-complete analysis as a post-freeze
  sensitivity, not as a replacement primary result.
- Describe team-cluster bootstrap intervals as conditional on the fitted monthly policies unless policy selection is
  explicitly repeated inside every resample.
- The paper must call the analysis retrospective and non-causal, identify the single-organization setting, and report the
  time-aware-popularity comparison alongside the random expectation.
- Evidence generation fails on drift from the canonical 121-case primary cohort and headline metrics.
- The package builder uses an allowlist; unresolved permission, ethics, authorship, and venue rules remain external gates.

## Commands

```bash
make xp2027-evidence
make xp2027-paper
make xp2027-check
make xp2027-package
```

## Cross-references

- `/domain-data` supplies validated maturity histories.
- `/domain-ml` owns policy selection and recommendation scoring.
- `/domain-validation` defines the leakage-safe cohort and ranking metrics.
- `submission/xp2027/RESEARCH_PROTOCOL.md` is the frozen analysis contract.
- `submission/xp2027/OPEN_ITEMS.md` is the external decision gate.
