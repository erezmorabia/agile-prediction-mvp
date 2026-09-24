# Can Organizational History Inform What Agile Teams Improve Next?

## A Walk-Forward Study of 87 Teams

**Erez Morabia² (emorabia@gmail.com), Shmuel Tyszberowicz¹,² (ORCID 0000-0003-4937-8138; tyshbe@tauex.tau.ac.il)**
¹Afeka Academic College of Engineering, Tel Aviv, Israel; ²The Open University of Israel, Ra'anana, Israel

## Abstract

Agile maturity assessments record how teams change over time, but organizations rarely test whether this history can
inform what a team considers next. We study whether longitudinal assessments can rank two practices associated with a
team's next recorded improvements, and whether peer similarity and practice transitions add value beyond time-aware
organizational popularity. The retrospective dataset contains 654 unique team-month observations from
87 teams, 30 retained practices, and ten organization-wide snapshots between January and November 2020. A global policy
is selected for each prediction month using only earlier outcomes whose windows have closed. The prespecified primary
cohort contains 121 outcome-bearing cases from 42 teams over five prediction months. The selected blend obtained 58.0%
monthly macro Conditional Hit Rate@2 (95% team-cluster bootstrap interval 47.1%-68.2%), versus 30.6% for an exact
candidate-aware random expectation. However, independently selected time-aware popularity obtained 55.7%; the paired
gap was only 2.3 percentage points (0.0-5.2), and the arms were identical in three of five months. A stricter
team-complete sensitivity removed one case and yielded 57.3% versus 54.9%. Thus, organizational history contains ranking
signal, although most of it is recovered by a simple frequency baseline and the study does not establish incremental
value from peer and transition signals. An exploratory analysis of all 298 complete-window recommendable cases yielded
23.1% observed alignment for the blend and 22.2% for popularity. We contribute a reusable baseline-first protocol that
separates historical signal from incremental personalization. For human-centered AI decision support, longitudinal data can
provide hypotheses for coach-team deliberation, while added signals require stable, decision-relevant gains under
prediction-time evaluation.

**Keywords:** agile software development; artificial intelligence; maturity assessment; recommender systems; temporal
validation; decision support

## 1 Introduction

Agile assessments can expose many practices below a target maturity level without resolving a recurring coaching
decision: what should this team consider next? Such decisions often draw on local judgment or static roadmaps, while
longitudinal organizational histories offer another source of evidence. An adaptive recommender could combine experience
from similar teams, typical practice sequences, and recent organizational movement. In an era of AI-assisted software
work, the first question is whether these histories contain useful ranking signal; the second is whether personalization
adds information beyond an inspectable organization-wide frequency rule.

We formulate next-practice guidance as top-two ranking over practices not already at maximum maturity. The intended
output is a hypothesis for coach-team deliberation, not an automated prescription. An observed maturity-score increase
is treated as the event to rank; it is not assumed to represent a durable capability change or an effect caused by a
recommendation.

The study asks:

- **RQ1:** How effectively can organization-specific maturity histories identify practices associated with a team's
  next recorded improvement under walk-forward evaluation?
- **RQ2:** What incremental value and stability do peer similarity and practice-transition evidence provide beyond
  time-aware organizational popularity?

We contribute: (1) evidence that organization-specific maturity histories can inform next-practice ranking; (2) a
transparent three-signal method; and (3) a reusable baseline-first protocol that keeps feature evidence, candidate
construction, outcome closure, and policy selection on their correct sides of prediction time. Comparison with random
ranking tests whether organizational history contains signal, while time-aware popularity isolates the incremental
value of peer and transition evidence. Here the first condition holds and the second is not established.

## 2 Background and Related Work

### 2.1 Agile improvement and maturity

Agile research emphasizes contextual evidence rather than universal transformation recipes [1,2]. Maturity models can
structure reflection, but reviews find limited validation of agile maturity models and low-strength evidence on
combining agile development with CMMI [3,4]. We therefore use maturity scores as longitudinal organizational
observations, not validated measures of delivery performance.

### 2.2 AI support for agile work

A systematic review finds that intelligent techniques in agile software development primarily support decisions, while
empirical evaluation remains limited [5]. More recent practitioner research prioritizes context-aware support for
requirements, communication, and Scrum processes [6]. XP studies examine AI's role in teamwork [7], customized meeting
assistants [8], and practitioners' expectations about human-AI collaboration [9]. These studies also reinforce a
socio-technical boundary: AI may inform planning and reflection, but people remain accountable for context, trust,
feasibility, and value.

Our method is not a generative-AI system. It is a transparent statistical recommender situated within this broader class
of AI-enabled decision support. Its relevance lies in testing whether historical patterns can support process guidance
and how much additional information personalization contributes before such guidance is presented to teams.

### 2.3 Recommendation and evaluation

Recommendation systems for software engineering have supported artifacts, experts, tools, and engineering decisions
[10]. Process-model recommendation shows that project attributes can inform method selection [11]. Related work guides
agile improvement through a goal-oriented maturity map [12], constructs assessment-based software-process
recommendations [13], and recommends improvement actions from individual developer performance [14]. These targets
differ from ranking the next observed practice change in longitudinal team assessments.

Evaluation choices can dominate recommender results. Reproducibility work calls for explicit data splits, candidate
sets, and implementation details [15]. Popularity is both a competitive strategy and a possible source of narrowing or
reinforcement, so it requires application-specific interpretation [16]. Offline metrics must match the intended ranking
task [17], and temporal splits should predict later interactions from past evidence without training on future
information [15]. These concerns motivate our walk-forward design and the treatment of popularity as the principal
comparator rather than a token baseline.

An earlier public, unpublished MSc project report describes the prototype and headline backtest [18]. This paper extends
that work with team-cluster uncertainty, fixed ablations, a frozen protocol, current literature positioning, and a
conference-focused research argument.

On 13 September 2026, a structured scoping search screened the first 20 Crossref records for each of four query families:
`"agile practice" recommender`, `"agile maturity" recommendation`, `"software process" recommendation method`, and
`"agile transformation" sequence mining`. OpenAlex abstract and availability records supported shortlisting. Records
were included when they addressed agile maturity/improvement or software-process recommendation or selection; general
transformation commentary, non-software recommenders, and artifact/API recommendation were excluded. Table 1 compares
the four closest studies. NR means that a feature was not reported in the screened title or abstract, not that the full
text proves its absence. This scoping check sharpens but does not exhaustively establish the novelty claim.

### 2.4 Structured gap check

## 3 Study Design

### 3.1 Setting and observations

The source is a repeated maturity assessment from one multinational telecommunications organization. It contains 655
rows and 654 unique team-month observations after deterministically retaining the final occurrence of one duplicate.
There are 87 teams and ten dated organization-wide snapshots from 7 January to 4 November 2020. Thirty-five practice
columns use a 0-3 scale; practices with more than 90% missing values are excluded, leaving 30, and retained scores are
normalized to 0-1. Three teams have only one observation. Team identities are used only to retain longitudinal clusters
and never appear in the evidence package.

The sanitized XP submission package does not contain team aliases, row-level observations, or source workbooks. It
contains analysis code, aggregate results, deterministic tests, and a schema-compatible synthetic example;
organizational data are excluded from its Apache-2.0 license. The broader public repository associated with the prior
MSc project [18] remains separate and tracks the source workbooks and practice documentation under the reported verbal
authorization described in the disclosures. That separation limits independent reproduction from the conference
artifact and does not make the broader repository non-identifying or grant a data license.

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
41 teams; it was added after protocol freeze and cannot replace the primary result based on favorability. A separate
post-protocol analysis retains all 298 cases, assigns zero observed alignment when no eligible increase occurred, and
estimates retrospective alignment across recommendable cases rather than conditional ranking performance.

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

Uncertainty uses 10,000 paired team-cluster bootstrap replicates with seed 22997 [19,20]. A replicate samples team
identities with replacement, retains all selected cases for each sampled team, and recomputes monthly macro means.
These percentile intervals are conditional on the monthly policies fitted to the observed histories: policy selection
is not repeated inside each replicate. They describe within-organization team-sampling instability, not uncertainty from
having only five months, model selection, measurement error, or transport to another company.

A post-protocol robustness bootstrap repeats the full walk-forward policy choice within each team-cluster replicate,
using the unchanged 675-policy grid and the same outcome-closure boundary. It therefore incorporates variability in
which blend and popularity policies are selected. Months without a completed prior window retain the fixed bootstrap
policy. This analysis uses 10,000 replicates with seed 22999 and is reported separately from the prespecified intervals.

The research questions, primary scope, metrics, comparators, and fixed ablations were frozen before the extended evidence
build. Automated tests pin cohort counts, temporal boundaries, deterministic bootstrap output, and the absence of team
identifiers from aggregate evidence. The all-recommendable analysis was added after protocol freeze and is explicitly
exploratory; it cannot replace the primary estimand.

## 6 Results

The selected blend reached 58.0% monthly macro Conditional Hit Rate@2 (47.1%-68.2%) and 58.7% pooled Hit Rate@2.
Time-aware popularity reached 55.7% (45.2%-65.6%). Their paired gap was 2.3 points (0.0-5.2). The arms were identical
in the first three months because neither had a completed prior window; the only differentiated months favored the blend
by 4.2 and 7.4 points. Thus the data establish organizational ranking signal but not a reliable incremental advantage
from the peer and transition components.

The exact random expectation was 30.6% (25.0%-36.7%), producing a paired blend gap of 27.4 points (17.5-36.5).
Supporting blend results were Precision@2 35.6%, Recall@2 17.6%, MRR 45.9%, and practice coverage 53.3%.

All fixed ablations are reported. Transitions plus popularity was strongest at 51.9%, followed by the equal blend at
49.5%, similarity plus transitions at 45.3%, similarity plus popularity at 45.1%, historical popularity at 42.8%,
similarity alone at 42.4%, recent popularity at 40.1%, and transitions alone at 15.7%. Several paired intervals against
the selected blend include zero; ablations are descriptive rather than proof of component effects.

The 120-case strict team-complete sensitivity yielded 57.3% for the blend, 54.9% for time-aware popularity, and 30.3%
for random expectation. The all-month sensitivity, which includes two right-censored prediction months, contained 151
cases over seven months and yielded 50.9%, 47.5%, and 28.0%, respectively. Neither sensitivity changes the conclusion.

Across all 298 complete-window recommendable cases, including 178 without an eligible recorded increase, exploratory
monthly macro observed alignment was 23.1% for the blend (16.1%-30.4%), 22.2% for time-aware popularity
(15.4%-29.4%), and 12.2% for random expectation (8.8%-16.0%). The paired blend-popularity gap was 0.9 points
(0.0-2.2). This is not an improvement-occurrence forecast: a zero can mean either that no eligible practice increased or
that an observed increase was not ranked in the top two.

When policy selection was repeated inside each bootstrap replicate, the blend interval was 44.6%-65.7%, popularity was
40.7%-64.8%, and the paired gap widened to -4.4 to 12.5 points. In the two adaptive primary months, resampling selected 15
and 31 distinct blend policies; the observed-data policies were modal but appeared in only 32.6% and 21.0% of
replicates. Thus, limited prior outcome windows make the selected configuration unstable, reinforcing rather than
weakening the conclusion that incremental personalization is unestablished.

## 7 Discussion and Threats to Validity

The study answers RQ1 positively but narrowly: past organizational behavior contains signal for ranking later recorded
practice increases and can provide hypotheses for coach-team deliberation. RQ2 receives a mostly negative answer.
Similarity and transition signals did not demonstrate stable incremental value beyond a carefully selected popularity
strategy. With only two differentiated months, the 2.3-point gain does not establish their added decision value.

This result matters for AI-era agile tooling. A system can appear personalized while mainly reproducing common
organizational behavior. Popularity should therefore be displayed as an explicit comparator and possible explanation,
not hidden inside a blended score. Coaches and teams should see the source of each suggestion and retain authority over
whether it is feasible or valuable. A prospective study should measure perceived explanation quality, decision changes,
practice adoption, and delivery outcomes, including potential reinforcement of already popular practices.

### 7.1 A baseline-first evaluation and use gate

The protocol supports a four-question gate for an organization considering data-informed agile guidance: (G1) were all
features, candidates, tuning outcomes, and comparators available at prediction time; (G2) does personalization improve
on an independently tuned, time-aware simple baseline by a practically meaningful margin; (G3) is that gain stable
across prediction periods and sensitivity scopes; and (G4) can users inspect the baseline, added signal sources, and
uncertainty while retaining decision authority? Failing G1 invalidates the evaluation. Failing G2 or G3 means the
personalized components should not be presented as superior; organizational history may still provide useful baseline
evidence while more data are collected. G4 is required before prospective use, irrespective of offline accuracy.

Applied here, G1 is satisfied by construction, but G2 and G3 are not: the paired gain is 2.3 points with an interval
touching zero, and the methods differ in only two primary months. G4 is a design requirement rather than an evaluated
outcome. The evidence therefore supports continued baseline monitoring and a prospective human-centered evaluation, not
deployment of the blend as a proven improvement.

**Construct validity.** Score increases may reflect rater changes, measurement noise, or reassessment rather than durable
capability. Although practice documentation is available in the prior-project repository, the instrument's measurement
validity has not been independently established. A three-snapshot union ranks near-term change, not necessarily the
single next action.

**Internal and conclusion validity.** Unobserved organizational initiatives may drive both popularity and team changes.
The 675-policy search operates on at most two completed training months for the differentiated primary predictions. The
prespecified bootstrap does not refit that selection, while the post-protocol refit analysis shows substantial policy
instability and a paired interval spanning zero. Five primary months provide little temporal variation.

**Selection and use validity.** The conditional cohort excludes 178 of 298 complete-window recommendable cases with no
recorded increase. Consequently, 58.0% must not be read as an unconditional success probability. Retrospective alignment
cannot show that presenting a recommendation would cause adoption or better outcomes. The exploratory 23.1% result
restores those cases but conflates absence of an eligible increase with ranking misses, so it is observed alignment, not
a calibrated probability that a recommendation will succeed.

**External and reproducibility validity.** One organization, one 2020 assessment vocabulary, and 42 primary-cohort teams
limit transportability. Code and aggregate evidence are reproducible from the sanitized artifact, but the XP package
alone cannot independently reproduce the empirical results. The separate public prior-project repository contains the
source workbooks but carries no organizational-data license. The submission relies on the reported verbal approval
described below and on a stricter aggregate-only XP release policy.

## 8 Conclusion

The three-signal recommender aligned one of two suggestions with a later recorded increase in 58.0% of conditional cases
and substantially exceeded random expectation. This supports the use of longitudinal organizational history as a source
of hypotheses about what teams may improve next, not as proof that recommendations cause adoption or outperform human
judgment. Time-aware popularity achieved 55.7%, and the richer approach was meaningfully different in only two months,
so incremental value from peer and transition evidence remains unestablished. The defensible contribution is an
auditable temporal evaluation for data-informed agile practice guidance whose evidence and limits remain visible to the
people making the decision.

## Data Availability and Disclosures

The organizational dataset is excluded from the sanitized XP package. No formal ethics approval was required for this
retrospective analysis; XP materials contain aggregate results, use an unnamed organizational description, and omit team
identifiers. The first author created and maintained the workbooks and reports that the responsible manager verbally
approved for academic use and knew would be public in the prior-project GitHub repository; no written record exists.
That repository is not the conference artifact, does not guarantee non-inferability of the organization, and grants no
license to the organizational data. This research received no external funding. The first author was formerly employed
by the source organization and participated in data collection in that professional role; the employment ended more
than five years ago, and the project was developed years later. Software and original documentation are Apache-2.0
licensed; organizational data are excluded. The unpublished public MSc report [18] is prior work. Generative AI
assistance used for planning, language refinement, and methodological checks will be disclosed under the final venue
rule; the authors verified and remain accountable for the work.

## Author Contributions

Erez Morabia contributed the conceptualization, methodology, software, validation, formal analysis, investigation, data
curation, visualization, and original draft. Shmuel Tyszberowicz contributed supervision, methodological guidance, and
critical review and editing. Both authors reviewed the manuscript and will approve the final version before submission.

## References

1. Dybå, T., Dingsøyr, T.: Empirical studies of agile software development: a systematic review. Information and Software Technology 50, 833-859 (2008). doi:10.1016/j.infsof.2008.01.006
2. Dikert, K., Paasivaara, M., Lassenius, C.: Challenges and success factors for large-scale agile transformations: a systematic literature review. Journal of Systems and Software 119, 87-108 (2016). doi:10.1016/j.jss.2016.06.013
3. Henriques, V., Tanner, M.: A systematic literature review of agile maturity model research. IJIKM 12, 53-73 (2017). doi:10.28945/3666
4. Selleri Silva, F. et al.: Using CMMI together with agile software development: a systematic review. Information and Software Technology 58, 20-43 (2015). doi:10.1016/j.infsof.2014.09.012
5. Perkusich, M. et al.: Intelligent software engineering in the context of agile software development: a systematic literature review. Information and Software Technology 119, 106241 (2020). doi:10.1016/j.infsof.2019.106241
6. Fujs, D., Kochovski, P., Stankovski, V., Vavpotic, D.: Key AI features to support Scrum software engineering: practitioners' perspective. Empirical Software Engineering 31, 138 (2026). doi:10.1007/s10664-026-10876-6
7. Kwok, Y.T.C., Adil, M.: AI and teamwork in agile software development: a systematic mapping study. LNBIP 561, 32-40 (2026). doi:10.1007/978-3-032-05799-0_4
8. Cabrero-Daniel, B., Herda, T., Pichler, V., Eder, M.: Exploring human-AI collaboration in agile: customised LLM meeting assistants. LNBIP 512, 163-178 (2024). doi:10.1007/978-3-031-61154-4_11
9. Planötscher, D., Wang, X., Adil, M., Gregory, P., Larimian, S.: Human-AI collaboration in software development activities: perspectives of agile practitioners. LNBIP 578, 274-289 (2026). doi:10.1007/978-3-032-22375-3_17
10. Gasparic, M., Janes, A.: What recommendation systems for software engineering recommend: a systematic literature review. Journal of Systems and Software 113, 101-113 (2016). doi:10.1016/j.jss.2015.11.036
11. Song, Q. et al.: A machine learning based software process model recommendation method. Journal of Systems and Software 118, 85-100 (2016). doi:10.1016/j.jss.2016.05.002
12. Packlick, J.: The Agile Maturity Map: A goal oriented approach to agile improvement. AGILE 2007, 266-271 (2007). doi:10.1109/AGILE.2007.55
13. Choi, S., Kim, D.-K., Park, S.: ReMo: A recommendation model for software process improvement. ICSSP, 135-139 (2012). doi:10.1109/ICSSP.2012.6225957
14. Raza, M., Faria, J.P., Amaro, L., Henriques, P.C.: WebProcessPAIR: recommendation system for software process improvement. ICSSP, 139-140 (2017). doi:10.1145/3084100.3084365
15. Bellogín, A., Said, A.: Improving accountability in recommender systems research through reproducibility. User Modeling and User-Adapted Interaction 31, 941-977 (2021). doi:10.1007/s11257-021-09302-x
16. Klimashevskaia, A., Jannach, D., Elahi, M., Trattner, C.: A survey on popularity bias in recommender systems. User Modeling and User-Adapted Interaction 34, 1777-1834 (2024). doi:10.1007/s11257-024-09406-0
17. Herlocker, J.L., Konstan, J.A., Terveen, L.G., Riedl, J.T.: Evaluating collaborative filtering recommender systems. ACM TOIS 22(1), 5-53 (2004). doi:10.1145/963770.963772
18. Morabia, E.: Agile Practice Recommendation MVP. Unpublished MSc advanced-project report, The Open University of Israel (2026). https://github.com/erezmorabia/agile-prediction-mvp/blob/590433a1a44c1f79c9b618879a28bec1ff16b1e7/docs/PROJECT_DOCUMENTATION.md
19. Efron, B.: Bootstrap methods: another look at the jackknife. Annals of Statistics 7(1), 1-26 (1979). doi:10.1214/aos/1176344552
20. Deen, M., de Rooij, M.: ClusterBootstrap: an R package for the analysis of hierarchical data using generalized linear models with the cluster bootstrap. Behavior Research Methods 52(2), 572-590 (2020). doi:10.3758/s13428-019-01252-y
