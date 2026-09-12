# Do Complex Recommenders Beat Popularity for Agile Practice Sequencing?

## A Leakage-Conscious Retrospective Study of 87 Teams

**Erez Morabia**
The Open University of Israel, Ra'anana, Israel

## Abstract

AI-enabled agile tools increasingly promise context-aware process guidance, but added algorithmic complexity should be
tested against transparent baselines. We study whether longitudinal maturity assessments can rank two practices
associated with a team's next recorded improvements, and whether peer similarity and practice transitions add value
beyond time-aware organizational popularity. The retrospective dataset contains 654 unique team-month observations from
87 teams, 30 retained practices, and ten organization-wide snapshots between January and November 2020. A global policy
is selected for each prediction month using only earlier outcomes whose windows have closed. The prespecified primary
cohort contains 121 outcome-bearing cases from 42 teams over five prediction months. The selected blend obtained 58.0%
monthly macro Conditional Hit Rate@2 (95% team-cluster bootstrap interval 47.1%-68.2%), versus 30.6% for an exact
candidate-aware random expectation. However, independently selected time-aware popularity obtained 55.7%; the paired
gap was only 2.3 percentage points (0.0-5.2), and the arms were identical in three of five months. A stricter
team-complete sensitivity removed one case and yielded 57.3% versus 54.9%. Thus, organizational history contains ranking
signal, but this study does not establish incremental value from the more complex model. The contribution is an
auditable evaluation protocol and a caution for human-centered AI decision support: simple temporal baselines should be
visible before algorithmic recommendations influence agile improvement choices.

**Keywords:** agile software development; artificial intelligence; maturity assessment; recommender systems; temporal
validation; decision support

## 1 Introduction

Agile assessments can expose many practices below a target maturity level without resolving a recurring coaching
decision: what should this team consider next? Static roadmaps ignore local trajectories, while an adaptive recommender
could combine experience from similar teams, typical practice sequences, and recent organizational movement. In an era
of AI-assisted software work, such guidance may appear attractive because it is personalized and data-driven. Yet a
complex score is not automatically more useful than a simple, inspectable frequency rule.

We formulate next-practice guidance as top-two ranking over practices not already at maximum maturity. The intended
output is a hypothesis for coach-team deliberation, not an automated prescription. An observed maturity-score increase
is treated as the event to rank; it is not assumed to represent a durable capability change or an effect caused by a
recommendation.

The study asks:

- **RQ1:** How effectively can organization-specific maturity histories identify practices associated with a team's
  next recorded improvement under walk-forward evaluation?
- **RQ2:** What incremental value and stability do peer similarity and practice-transition evidence provide beyond
  time-aware organizational popularity?

We contribute: (1) a transparent three-signal ranking method; (2) a prediction-time evaluation in which evidence,
candidate construction, and policy selection respect temporal boundaries; and (3) a result that is useful precisely
because it is not a model-success story: the blend clearly exceeds random ranking but does not convincingly beat a
strong popularity comparator.

## 2 Background and Related Work

### 2.1 Agile improvement and maturity

Agile research emphasizes contextual evidence rather than universal transformation recipes [1,2]. Maturity models can
structure reflection, but reviews find heterogeneous instruments and limited validation [3,4]. We therefore use maturity
scores as longitudinal organizational observations, not validated measures of delivery performance.

### 2.2 AI support for agile work

Recent studies show growing interest in AI support for Scrum and agile teamwork. Practitioner research prioritizes
context-aware support for requirements, communication, and Scrum processes [5]. XP studies examine AI's role in teamwork
[6], customized meeting assistants [7], and practitioners' expectations about human-AI collaboration [8]. These studies
also reinforce a socio-technical boundary: AI may inform planning and reflection, but people remain accountable for
context, trust, feasibility, and value.

Our method is not a generative-AI system. It is a transparent statistical recommender situated within this broader class
of AI-enabled decision support. Its relevance lies in testing whether historical patterns justify personalized process
guidance before such guidance is presented to teams.

### 2.3 Recommendation and evaluation

Recommendation systems for software engineering have supported artifacts, experts, tools, and engineering decisions
[9]. Process-model recommendation shows that project attributes can inform method selection [10]. We found no evaluated
approach in the focused review that combines longitudinal team maturity vectors, peer trajectories, practice
transitions, and prediction-time popularity to rank the next observed agile-practice changes.

Evaluation choices can dominate recommender results. Reproducibility work calls for explicit data splits, candidate
sets, and implementation details [11]. Popularity is both a competitive strategy and a possible source of narrowing or
reinforcement, so it requires application-specific interpretation [12]. Offline metrics must match the intended ranking
task [13], and time-ordered settings must not train on future observations [14]. These concerns motivate our
walk-forward design and the treatment of popularity as the principal comparator rather than a token baseline.

An earlier public, unpublished MSc project report describes the prototype and headline backtest [16]. This paper extends
that work with team-cluster uncertainty, fixed ablations, a frozen protocol, current literature positioning, and a
conference-focused research argument.

## 3 Study Design

### 3.1 Setting and observations

The source is a repeated maturity assessment from one multinational telecommunications organization. It contains 655
rows and 654 unique team-month observations after deterministically retaining the final occurrence of one duplicate.
There are 87 teams and ten dated organization-wide snapshots from 7 January to 4 November 2020. Thirty-five practice
columns use a 0-3 scale; practices with more than 90% missing values are excluded, leaving 30, and retained scores are
normalized to 0-1. Three teams have only one observation. Team identities are used only to retain longitudinal clusters
and never appear in the evidence package.

The XP materials do not expose the assessment instrument, practice labels, team aliases, or raw data. This protects
confidentiality but limits construct assessment and independent empirical reproduction. The released artifact contains
analysis code, aggregate results, deterministic tests, and a schema-compatible synthetic example; organizational data
are excluded from its Apache-2.0 license.

### 3.2 Prediction cases and estimand

For prediction month *m*, the baseline is a team's latest recorded snapshot strictly before *m*. A case is recommendable
when a baseline exists and at least two practices are below maximum. The eligible candidate set is fixed before scoring.
The outcome is the union of eligible practices whose score increases within up to the next three recorded team
snapshots. A case enters the primary ranking cohort only when this set is nonempty.

The prespecified primary scope uses five prediction months whose three-snapshot horizon is globally observable. It
contains 121 outcome-bearing cases from 42 of the 87 teams. The estimand is therefore conditional ranking alignment: if
an eligible practice later increases, does either recommendation identify one? It does not estimate whether a team will
improve or whether advice causes change.

A stricter audit found 298 recommendable cases with exactly three subsequent team snapshots. Of these, 120 (40.3%) had
an eligible increase and 178 (59.7%) did not. The strict outcome-bearing sensitivity therefore contains 120 cases from
41 teams; it was added after protocol freeze and cannot replace the primary result based on favorability.

### 3.3 Temporal boundary

All features are evaluated at the target baseline. Peer outcomes are capped at that baseline; practice transitions and
popularity use only earlier organizational changes. A previous prediction month can tune a policy only after its full
outcome window closes before the target month. The same precomputed cohort is scored by every method.

## 4 Recommendation and Policy Selection

### 4.1 Evidence signals

**Peer similarity.** Cosine similarity compares the target baseline with historical snapshots from other teams. For a
candidate practice, an eligible peer contributes its similarity multiplied by the peer's largest increase during its
next two snapshots, provided neither snapshot occurs after the target baseline. Duplicate peers are removed before the
top *k* are retained.

**Practice transitions.** Directed transitions are learned from consecutive improvement-bearing steps. Practices that
increased in the target team's two preceding snapshots trigger empirical probabilities for typical successors.
Simultaneous increases do not create directed edges.

**Popularity.** Historical popularity counts all practice increases observed before the baseline. Recent popularity
uses only the organizational transition immediately preceding the baseline. A recency parameter mixes the two.

For candidate *p*, the final score is `score(p) = w_s S(p) + w_t T(p) + w_p P(p)`, where nonnegative weights sum to one
and `P(p) = r P_recent(p) + (1-r) P_historical(p)`. Components are normalized in their documented scopes. The two
highest candidates are returned, using practice name as the final deterministic tie-break.

### 4.2 Walk-forward selection and comparators

The policy grid contains 675 combinations: peer count in {5,10,19}; minimum similarity in {0,0.5,0.75}; 15 three-factor
weight triples on a 0.25 grid; and recency in {0,0.25,0.5,0.75,1}. One global policy is selected each month by mean
Hit Rate@2 on completed prior months. Before any outcome window has closed, a fixed policy uses popularity alone with
`r=0.5`.

The strongest comparator independently selects among five pure-popularity policies using the same temporal rule. An
exact candidate-aware random expectation controls for the number of eligible and improved practices. Eight fixed,
untuned ablations isolate historical popularity, recent popularity, similarity, transitions, the equal three-factor
blend, and the three equal-weight signal pairs.

## 5 Evaluation

Hit Rate@2 is one when either recommendation is in the actual-positive set. Cases are averaged within prediction month,
then the five month-level values receive equal weight. Supporting metrics are Precision@2, Recall@2, mean reciprocal
rank (MRR), practice coverage, and pooled descriptive Hit Rate@2.

For candidate count *n*, improved-candidate count *k*, and recommendation depth `d=min(2,n)`, exact random Hit Rate is
`1 - C(n-k,d)/C(n,d)`. This case-level expectation is aggregated identically to the observed methods.

Uncertainty uses 10,000 paired team-cluster bootstrap replicates with seed 22997 [15]. A replicate samples team
identities with replacement, retains all selected cases for each sampled team, and recomputes monthly macro means.
These percentile intervals are conditional on the monthly policies fitted to the observed histories: policy selection
is not repeated inside each replicate. They describe within-organization team-sampling instability, not uncertainty from
having only five months, model selection, measurement error, or transport to another company.

The research questions, primary scope, metrics, comparators, and fixed ablations were frozen before the extended evidence
build. Automated tests pin cohort counts, temporal boundaries, deterministic bootstrap output, and the absence of team
identifiers from aggregate evidence.

## 6 Results

The selected blend reached 58.0% monthly macro Conditional Hit Rate@2 (47.1%-68.2%) and 58.7% pooled Hit Rate@2.
Time-aware popularity reached 55.7% (45.2%-65.6%). Their paired gap was 2.3 points (0.0-5.2). The arms were identical
in the first three months because neither had a completed prior window; the only differentiated months favored the blend
by 4.2 and 7.4 points. Thus the data do not establish a reliable practical advantage for complexity.

The exact random expectation was 30.6% (25.0%-36.7%), producing a paired blend gap of 27.4 points (17.5-36.5).
Supporting blend results were Precision@2 35.6%, Recall@2 17.6%, MRR 45.9%, and practice coverage 53.3%.

All fixed ablations are reported. Transitions plus popularity was strongest at 51.9%, followed by the equal blend at
49.5%, similarity plus transitions at 45.3%, similarity plus popularity at 45.1%, historical popularity at 42.8%,
similarity alone at 42.4%, recent popularity at 40.1%, and transitions alone at 15.7%. Several paired intervals against
the selected blend include zero; ablations are descriptive rather than proof of component effects.

The 120-case strict team-complete sensitivity yielded 57.3% for the blend, 54.9% for time-aware popularity, and 30.3%
for random expectation. The all-month sensitivity, which includes two right-censored prediction months, contained 151
cases over seven months and yielded 50.9%, 47.5%, and 28.0%, respectively. Neither sensitivity changes the conclusion.

## 7 Discussion and Threats to Validity

The study answers RQ1 positively but narrowly: past organizational behavior contains signal for ranking later recorded
practice increases. RQ2 receives a mostly negative answer. Similarity and transition signals did not demonstrate stable
incremental value beyond a carefully selected popularity strategy. With only two differentiated months, the 2.3-point
gain is not a sound basis for deploying extra complexity.

This result matters for AI-era agile tooling. A system can appear personalized while mainly reproducing common
organizational behavior. Popularity should therefore be displayed as an explicit comparator and possible explanation,
not hidden inside a blended score. Coaches and teams should see the source of each suggestion and retain authority over
whether it is feasible or valuable. A prospective study should measure perceived explanation quality, decision changes,
practice adoption, and delivery outcomes, including potential reinforcement of already popular practices.

**Construct validity.** Score increases may reflect rater changes, measurement noise, or reassessment rather than durable
capability. Practice labels and instrument validity cannot yet be independently inspected. A three-snapshot union ranks
near-term change, not necessarily the single next action.

**Internal and conclusion validity.** Unobserved organizational initiatives may drive both popularity and team changes.
The 675-policy search operates on at most two completed training months for the differentiated primary predictions. The
bootstrap does not refit that selection. Five primary months provide little temporal variation.

**Selection and use validity.** The conditional cohort excludes 178 of 298 complete-window recommendable cases with no
recorded increase. Consequently, 58.0% must not be read as an unconditional success probability. Retrospective alignment
cannot show that presenting a recommendation would cause adoption or better outcomes.

**External and reproducibility validity.** One organization, one 2020 assessment vocabulary, and 42 primary-cohort teams
limit transportability. Code and aggregate evidence are reproducible, but the private data prevent independent
replication. The submission relies on the reported verbal approval described below and on a stricter aggregate-only XP
release policy.

## 8 Conclusion

The three-signal recommender aligned one of two suggestions with a later recorded increase in 58.0% of conditional cases
and substantially exceeded random expectation. However, time-aware popularity achieved 55.7%, and the richer approach
was meaningfully different in only two months. The defensible contribution is therefore not a claim of superior AI. It
is an auditable temporal evaluation and a practical warning: before algorithmic guidance influences agile improvement,
its complexity should outperform a transparent baseline and its limits should be visible to the people making the
decision.

## Data Availability and Disclosures

The organizational dataset is not included. No formal ethics approval was required for this retrospective analysis; XP
materials contain aggregate results, use an unnamed organizational description, and omit team identifiers. The author
created and maintained the workbooks and reports that the responsible manager verbally approved their use for the degree
project; no written record exists. Erez Morabia is the sole and corresponding author, affiliated with The Open University
of Israel. This research received no external funding. The author was formerly employed by the source organization and
participated in data collection in that professional role; the employment ended more than five years ago, the project
was developed years later, and the author reports no current competing interests. Software and original documentation
are Apache-2.0 licensed; organizational data are excluded. The unpublished public MSc report [16] is prior work.
Generative AI assistance used for planning, language refinement, and methodological checks will be disclosed under the
final venue rule; the author verified and remains accountable for the work.

## Acknowledgments

The author thanks Prof. Shmuel Tyszberowicz for supervising the MSc project and reviewing the work.

## References

1. Dybå, T., Dingsøyr, T.: Empirical studies of agile software development: a systematic review. Information and Software Technology 50, 833-859 (2008). doi:10.1016/j.infsof.2008.01.006
2. Dikert, K., Paasivaara, M., Lassenius, C.: Challenges and success factors for large-scale agile transformations. Journal of Systems and Software 119, 87-108 (2016). doi:10.1016/j.jss.2016.06.013
3. Henriques, V., Tanner, M.: A systematic literature review of agile and maturity model research. IJIKM 12, 53-73 (2017). doi:10.28945/3666
4. Selleri Silva, F. et al.: Using CMMI together with agile software development: a systematic review. Information and Software Technology 58, 20-43 (2015). doi:10.1016/j.infsof.2014.09.012
5. Fujs, D., Kochovski, P., Stankovski, V., Vavpotič, D.: Key AI features to support Scrum software engineering. Empirical Software Engineering 31, 138 (2026). doi:10.1007/s10664-026-10876-6
6. Kwok, Y.T.C., Adil, M.: AI and teamwork in agile software development: a systematic mapping study. LNBIP 561 (2026). doi:10.1007/978-3-032-05799-0_4
7. Cabrero-Daniel, B., Herda, T., Pichler, V., Eder, M.: Exploring human-AI collaboration in agile: customised LLM meeting assistants. LNBIP 512, 163-178 (2024). doi:10.1007/978-3-031-61154-4_11
8. Planötscher, D., Wang, X., Adil, M., Gregory, P., Larimian, S.: Human-AI collaboration in software development activities. LNBIP 578 (2026). doi:10.1007/978-3-032-22375-3_17
9. Robillard, M.P., Walker, R., Zimmermann, T.: Recommendation systems for software engineering. IEEE Software 27(4), 80-86 (2010). doi:10.1109/MS.2009.161
10. Song, Q. et al.: A machine learning based software process model recommendation method. Journal of Systems and Software 118, 85-100 (2016). doi:10.1016/j.jss.2016.05.002
11. Bellogín, A., Said, A.: Improving accountability in recommender systems research through reproducibility. User Modeling and User-Adapted Interaction 31, 941-977 (2021). doi:10.1007/s11257-021-09302-x
12. Klimashevskaia, A., Jannach, D., Elahi, M., Trattner, C.: A survey on popularity bias in recommender systems. User Modeling and User-Adapted Interaction 34, 1777-1834 (2024). doi:10.1007/s11257-024-09406-0
13. Herlocker, J.L., Konstan, J.A., Terveen, L.G., Riedl, J.T.: Evaluating collaborative filtering recommender systems. ACM TOIS 22(1), 5-53 (2004). doi:10.1145/963770.963772
14. Bergmeir, C., Hyndman, R.J., Koo, B.: A note on the validity of cross-validation for evaluating autoregressive time series prediction. CSDA 120, 70-83 (2018). doi:10.1016/j.csda.2017.11.003
15. Efron, B.: Bootstrap methods: another look at the jackknife. Annals of Statistics 7(1), 1-26 (1979). doi:10.1214/aos/1176344552
16. Morabia, E.: Agile Practice Recommendation MVP. Unpublished MSc advanced-project report, The Open University of Israel (2026). https://github.com/erezmorabia/agile-prediction-mvp
