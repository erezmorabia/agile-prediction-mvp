# Reproducibility Manifest

## Canonical input

- Authorized source workbook (never included in the sanitized XP package; separately tracked in the broader
  prior-project repository under the governance statement in the paper).
- SHA-256: `6e70b02d98da2958540892a1fc228bca35f192b80b78171d63d4be061a04bb35`.
- Dimensions after validation: 655 source rows, 654 unique team-month observations, 87 teams, ten snapshots, and 30
  retained practices from 35 raw practice columns.

## Deterministic analysis

- Production implementation: `src/ml/policy.py` and its data/validation dependencies.
- Research adapter: `scripts/build_xp2027_evidence.py`.
- Canonical manuscript: `manuscript/PAPER.md`; the PDF builder reads this file rather than duplicating its prose.
- Bibliography guard: the build verifies entry counts, DOIs, and URLs against `manuscript/references.bib`.
- Team-cluster bootstrap: 10,000 replicates, seed 22997; exploratory all-recommendable intervals use seed 22998; the
  selection-refit robustness analysis uses seed 22999.
- Generated evidence: `evidence/metrics.json` and `evidence/PRIMARY_RESULTS.md`.
- Drift guards: 121 primary cases, 58.0% selected-blend monthly macro HR@2, 55.7% time-aware popularity,
  30.6% random expectation, strict-window counts 298/120/178, and strict team-complete sensitivity values of
  57.3%/54.9%/30.3% for blend/popularity/random. The exploratory all-recommendable analysis is pinned at
  23.1%/22.2%/12.2% across 298 complete-window cases. The selection-refit paired gap interval is pinned at
  -4.4% to 12.5%, with 15 and 31 distinct blend policies selected in the two adaptive primary months.
- Team-cluster bootstrap intervals condition on the policies fitted to the observed histories; selection is not refitted
  inside each resample. A separately labeled robustness analysis does refit selection inside every resample.

## Rebuild

```bash
python3 -m venv .research-venv
.research-venv/bin/pip install -r requirements.txt -r requirements-dev.txt
make xp2027-evidence
make xp2027-paper
make xp2027-check
make xp2027-package
```

`make xp2027-check` validates source quality, the aggregate evidence tests, the existing canonical model reproduction,
temporal-boundary guards, the five-to-eight-page preparation PDF, and a temporary sanitized archive. The distributable archive is generated
from an explicit allowlist and receives a fixed ZIP timestamp for byte-stable rebuilds when its inputs are unchanged.
