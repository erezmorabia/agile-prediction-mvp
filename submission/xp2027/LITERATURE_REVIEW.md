# Focused Literature Review

Verified on 2026-09-12 from publisher, DOI, or institutional records. The review is deliberately focused rather than
systematic; it supports positioning and does not claim complete coverage.

## Agile improvement and maturity

Empirical agile research has long emphasized contextual evidence rather than universal prescriptions. Dybå and
Dingsøyr's review found a relatively small empirical base, while Dikert et al. synthesized recurring challenges and
success factors in large-scale transformations. Agile maturity-model reviews show that assessment frameworks are
numerous but often weakly validated. These findings motivate treating maturity observations as local signals for a
decision aid, not as proof of a universal adoption sequence.

## AI support and software-engineering recommendation

Recent XP and empirical-software-engineering research shows increasing interest in AI support for Scrum and agile
teamwork. Studies cover customized meeting assistants, practitioner expectations for Scrum support features, and how
agile practitioners understand human-AI collaboration. The evidence also emphasizes context, trust, and keeping people
responsible for socio-technical decisions. This study addresses a narrower decision: ranking possible next improvement
practices from organizational assessment histories. The method is a transparent statistical recommender rather than a
generative-AI system, and its output is intended for coach-team deliberation.

Recommendation systems for software engineering adapt ranking and information-retrieval ideas to development work.
Prior work has recommended artifacts, experts, and process models. We found no evaluated method in the focused review
that combines longitudinal team maturity assessments, peer trajectories, practice transitions, and prediction-time
popularity to rank a team's next observed practice change.

## Evaluation and temporal validity

Offline recommenders can look stronger when future interactions leak into model fitting, candidate construction, or
selection. Reproducibility research recommends explicit split and implementation details, while recent popularity-bias
research shows why a simple popularity strategy must be treated as a substantive comparator rather than a token
baseline. The study therefore uses walk-forward policy selection, learns every component only from snapshots before the
target baseline, keeps the evaluated cohort independent of the policy being scored, and retains whole team histories
during bootstrap resampling. Hit Rate@2 is primary because the operational output contains two suggestions; precision,
recall, MRR, coverage, all predeclared ablations, per-month results, and sensitivity analyses provide context.

## Positioning gap

The contribution is not a new maturity model, a generative-AI technique, or causal evidence for transformation. It is an
auditable retrospective evaluation showing both that organizational histories contain ranking signal and that most of
this signal is recovered by time-aware popularity. The negative incremental result is relevant to AI-era agile tooling:
added algorithmic complexity should earn its place against a strong, transparent baseline before influencing teams.
