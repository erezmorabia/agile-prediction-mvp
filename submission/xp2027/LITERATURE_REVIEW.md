# Structured Literature-Gap Review

## Scope and method

Search performed on 2026-09-13. This is a structured scoping search to test the manuscript's positioning, not a
systematic literature review or evidence synthesis.

Sources:

- Crossref Works metadata for discovery and DOI verification.
- OpenAlex abstract and availability records for screening shortlisted works.
- Publisher/DOI metadata for bibliographic verification.
- The XP 2025 and XP 2026 proceedings and calls previously reviewed for venue positioning.

Four query families were used, with the first 20 Crossref results screened for each (80 returned records before
deduplication):

1. `"agile practice" recommender`
2. `"agile maturity" recommendation`
3. `"software process" recommendation method`
4. `"agile transformation" sequence mining`

Records were retained when their title or abstract addressed agile maturity/improvement or a recommendation mechanism
for software-process improvement or selection. General transformation commentary, non-software recommenders,
artifact/API recommendation, and papers without an improvement or process-selection target were excluded. DBLP was
attempted as a cross-check but returned a non-JSON service response and was not used. Several shortlisted publications
are paywalled; comparison for those works is limited to verified bibliographic metadata and indexed abstracts. Absence
of a feature below therefore means it was not reported in the screened title/abstract, not proof that it is absent from
the full text.

## Closest prior work

- Packlick's Agile Maturity Map [12] provides a goal-oriented approach intended to help teams move beyond an agile
  adoption plateau. It guides improvement but does not report data-driven next-event ranking in the screened abstract.
- Choi et al.'s ReMo [13] develops recommendations from capability-based process assessments and evaluates the method
  with industrial assessment data. The screened abstract does not report longitudinal team trajectories, next-practice
  event ranking, or walk-forward comparison with a temporal baseline.
- Raza et al.'s WebProcessPAIR [14] ranks improvement actions for individual developers using performance data and
  crowdsourced root-cause actions; its report illustrates usage through a case study rather than longitudinal team
  next-practice prediction.
- Song et al. [11] use project attributes to recommend a software process model. Their target is process-model
  selection, not the next observed practice change within a longitudinal team assessment.

## Agile improvement and maturity

Empirical agile research emphasizes contextual evidence rather than universal prescriptions. Dybå and Dingsøyr review
the empirical agile base, while Dikert et al. synthesize recurring challenges and success factors in large-scale
transformations. Agile maturity-model reviews show that assessment frameworks are numerous but often weakly validated.
These findings motivate treating maturity observations as local signals for a decision aid, not as proof of a universal
adoption sequence.

## AI support and software-engineering recommendation

A systematic review of intelligent techniques in agile software development [5] finds that decision support is a central
purpose while empirical evaluation remains limited. Recent XP and empirical-software-engineering research shows growing
interest in AI support for Scrum and agile teamwork. Studies cover customized meeting assistants, practitioner
expectations for Scrum support features, and how agile practitioners understand human-AI collaboration. The evidence
emphasizes context, trust, and keeping people responsible for socio-technical decisions. This study addresses a narrower
decision: ranking possible next improvement practices from organizational assessment histories. The method is a
transparent statistical recommender rather than a generative-AI system, and its output is intended for coach-team
deliberation.

The systematic review of recommendation systems for software engineering [10] shows that prior systems predominantly
recommend source-code artifacts and use limited context. Other work recommends process models, process-improvement
actions, and maturity-guided change. Across the four closest studies, the screened reports do not combine longitudinal
team maturity vectors, peer trajectories, practice transitions, next-event ranking, walk-forward selection, and a
time-aware popularity comparator.

## Evaluation and temporal validity

Offline recommenders can look stronger when future interactions leak into model fitting, candidate construction, or
selection. Reproducibility research recommends explicit splits and implementation details, while popularity-bias
research shows why a simple popularity strategy must be treated as a substantive comparator rather than a token
baseline. The study therefore uses walk-forward policy selection, learns every component only from snapshots before the
target baseline, keeps the evaluated cohort independent of the policy being scored, and retains whole team histories
during bootstrap resampling. Hit Rate@2 is primary because the operational output contains two suggestions; precision,
recall, MRR, coverage, all predeclared ablations, per-month results, and sensitivity analyses provide context.

## Positioning gap

The contribution is not a new maturity model, a generative-AI technique, or causal evidence for transformation. It is
an auditable retrospective evaluation showing both that organizational histories contain ranking signal and that most
of this signal is recovered by time-aware popularity. The structured gap check supports a narrower novelty claim: no
screened near-neighbor reports the same combination of longitudinal team-level next-practice ranking and leakage-aware
evaluation against an independently selected temporal popularity baseline. This claim remains bounded by the search
sources, query families, and abstract-level screening described above.
