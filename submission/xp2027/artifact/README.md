# Aggregate Reproducibility Artifact

This preparation artifact intentionally contains no raw organizational data and no team-level output.

## Reproduce with authorized local data

1. Place the authorized workbook at `data/raw/combined_dataset.xlsx`.
2. Install project and development requirements.
3. Run `make xp2027-evidence` and `make xp2027-check`.

The evidence build validates the canonical input digest, cohort sizes, strict-window audit, and headline metrics. It
emits aggregate JSON and Markdown only. The submitted public artifact must not contain the source workbook unless the
data owner explicitly authorizes redistribution.

## Contents safe to distribute

- Frozen research protocol and focused literature synthesis.
- Aggregate method metrics and team-cluster bootstrap intervals.
- Analysis and paper-build source code.
- Tests for temporal reproduction, cohort stability, determinism, and absence of team names in aggregate evidence.
- Apache-2.0 license for the software and original project documentation.

## Not yet distributable

- Raw or transformed organizational observations.
- Real team names, reversible pseudonyms, screenshots, or row-level prediction records.
- Any license grant for the organizational workbooks or derived datasets.
