# Professor Review Change Log

This file records the changes made in response to professor feedback. New review comments should be added as separate entries so this document can be shared as a complete summary when the review is finished.

## 1. Calibrate "prediction" terminology

**Professor comment:** Replace strong "prediction" language with more cautious language, such as describing the system as identifying a likely next agile practice maturity.

**Decision applied:** Documentation now describes the system as identifying a team's **likely next practice** or providing a **recommendation**. Backtest outcomes are described as **validated recommendations** or **recommendation alignment**, rather than claims that a prediction was correct.

### Project documentation changes

The following edits were made specifically in `docs/PROJECT_DOCUMENTATION.md`:

| Section | Exact change |
| --- | --- |
| Title and **Abstract** | Retitled the document to **Identifying Likely Large-Scale Agile Implementation Pathways**. Reframed the 50.3% result as recommendations aligning with later improvements in 50.3% of evaluated cases. |
| **Executive Summary → Validation Methodology / Successful Results** | Replaced prediction accuracy wording with recommendation validation, **Recommendation Accuracy**, and alignment with later improvements. |
| **§1.3 Scope and Limitations** | Changed the minimum-history statement to say the system needs two months of history to generate recommendations. |
| **§1.4 Connection to Original Proposal** | Replaced “predicting the next required adoption steps” with “identifying likely next adoption steps.” |
| **§2.2 Similarity-Based Recommendation** | Rephrased the general collaborative-filtering explanation to identify likely preferences instead of predict preferences. |
| **§3.6 Validation Methodology** | Changed the rolling-window step and validation criteria to describe generating and validating recommendations. The formulas `correct_predictions / total_predictions` and `correct_predictions_popularity / total_predictions` were retained exactly because they are existing technical field names. |
| **§4.3 Data Flow** | Renamed displayed flow stages from per-month predictions to per-month recommendations. |
| **§5.2 Key Implementation Decisions** | Clarified that future months are not used to generate recommendations. |
| **§6.2 Evaluation Metrics and §6.3 Backtest Results** | Renamed reader-facing metrics to **Total Recommendations Evaluated** and **Validated Recommendations**. |
| **§6.4, §6.7, §7.1, §7.3, §8.1, §8.2** | Reframed validation results, historical comparisons, system limitations, conclusions, and deployment readiness around recommendations and likely next practices rather than definitive predictions. |
| **§10.1, §10.4, §10.6, §11.2** | Updated the user manual and module description: renamed the displayed system description, the recommendation-month instruction, outcome metric wording, and backtest validation wording. |

### Other documentation changes

| Location | Exact change |
| --- | --- |
| `README.md` | Renamed the displayed project heading to **Agile Practice Recommendation MVP**; updated the backtest explanation and example result labels to recommendations and validated recommendations. Repository and executable names were intentionally retained. |
| `docs/QUICK_START.md` | Changed “top predicted practices” to “likely next practices.” |
| `docs/INSTALLATION.md` | Changed the displayed system name to **Agile Practice Recommendation System**. |
| `docs/flowcharts/run-backtest.md` | Reworded backtest descriptions and labels from live predictions to likely next-practice recommendations and recommendation evaluation. |
| `docs/flowcharts/learn-sequences-up-to-month.md` and `docs/flowcharts/ranked-similar-teams.md` | Reworded data-leakage explanations to refer to recommendation evaluation. |
| `docs/sequence-diagrams/01-get-recommendations.md`, `02-run-backtest.md`, and `03-system-startup.md` | Reworded flow explanations from prediction terminology to recommendation terminology. |

Repository and executable names were intentionally retained where they appear in the documentation.

## 2. Remove "Big Data" terminology

**Professor comment:** Remove the term “Big Data”; even the theoretical complete grid of 30,450
team-practice cells (87 teams × 35 practices × 10 months) is not considered big by modern
data-science standards.

**Decision applied:** The documentation now describes the dataset as a **moderate-sized
organizational dataset** with 22,925 team-practice cells across 655 raw source rows,
while distinguishing that actual coverage from the 30,450-cell theoretical complete grid. It
discusses processing efficiency and future scalability without claiming Big Data capability.

### Project documentation changes

The following edits were made in `docs/PROJECT_DOCUMENTATION.md`:

| Section | Exact change |
| --- | --- |
| **Executive Summary → System Capabilities** | Replaced “Handles large-scale data efficiently” with an accurate statement that the system processes the project dataset efficiently, including the dimensions and approximate number of practice-level maturity values. |
| **§5.4 Performance Considerations** | Renamed **Big Data Handling** to **Performance and Scalability**. |
| **§7.1 How Implementation Addresses Proposal Objectives** | Replaced the large-scale-data claim with “Processes the project dataset efficiently.” |
| **§7.2 Strengths** | Replaced the claim that the algorithms handle large datasets with a forward-looking scalability statement tied to growth beyond the current project dataset. |
| **§7.6 Dataset Scale and Efficiency** | Renamed **Big Data Handling Capabilities** to **Dataset Scale and Efficiency** and added an explicit description of the dataset as moderate-sized (22,925 cells across 655 raw source rows; 30,450 cells only for a theoretical complete grid). Item 14 later distinguishes these rows from the 654 unique team-month keys used analytically. |

## 3. Clarify the popularity-baseline improvement claim

**Professor comment:** Clarify that the 6.7% improvement over the popularity approach is an organizational average and cannot be guaranteed for every individual team.

**Decision applied:** The 6.7 percentage-point improvement is now explicitly presented as an aggregate organizational backtest result, not a per-team guarantee.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **§6.3 Backtest Results → Popularity Baseline Comparison** | Added a caveat directly below the +6.7 percentage-point result: it is a macro-average across tested months, and individual team results can be higher or lower depending on their history, maturity profile, and validation-period improvements. |
| **Executive Summary → Successful Results; §6.3; §7.1; §7.4; §7.5; §8.1** | Added or reinforced the rule that accuracy and improvement figures are aggregate backtest results, not guaranteed per-team or per-month outcomes. Softened language that implied a recommendation would necessarily improve a team or reduce risk. |
| `README.md` and `docs/QUICK_START.md` | Added a prominent aggregate-results disclaimer and revised examples and metric labels so they do not imply assured improvement for individual teams. |

## 4. Rename the sequence component to “Practice Transition Model”

**Professor comment:** Replace “Markov Chain” terminology with “Practice Transition Model” and avoid presenting the implementation as a formal Markov chain.

**Decision applied:** Documentation now describes this component as an empirical model of observed practice-to-practice transitions between consecutive improvement-bearing steps. It explains transition counts and conditional probabilities without claiming the Markov property.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **Abstract; Executive Summary; §1.3; §4.2; §7.1; §8.1; §9.1; §11.2** | Replaced Markov-chain terminology with **Practice Transition Model** or practice-transition terminology. |
| **§2.3 Practice Transition Model** | Replaced the Markov-chain definition and memoryless-property claims with an explanation of observed consecutive-step transitions, transition counts, and conditional probabilities. |
| **§3.4 Practice Transition Model Algorithm** | Renamed the algorithm section and clarified that it models ordered transitions only between consecutive improvement-bearing steps; same-step improvements are not given an arbitrary order. |
| **§9.2 Practice Transition Matrix** | Renamed the matrix description and removed the claim that it is a first-order Markov chain. |

## 5. Use observed-improvement terminology for time

**Professor comment:** Refer to improvements as “observed improvement” rather than “next month’s improvement,” because teams may take several months to progress.

**Decision applied:** Documentation now describes results as subsequent observed improvements and states the applicable 1–3-month or three-recorded-month validation window where needed. This avoids implying that every improvement must occur in the immediately following calendar month.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **§3.3 Collaborative Filtering Algorithm and §3.7 Worked Examples** | Clarified that peer evidence checks the next two recorded snapshots, subject to the recommendation baseline boundary. |
| **§10.6 Understanding Results** | Replaced “next month, month after, month after that” with a subsequent observed-improvement window covering the target month and the following two recorded months. |
| `README.md` | Rephrased transition examples to describe subsequent observed improvements rather than presumed next-month outcomes. |

## 6. Document maximum maturity

**Professor comment:** Include a note or data analysis showing how many teams reached the highest maturity level and in which practices, acknowledging that improvement is impossible once the maximum is reached.

**Decision applied:** Added a report-only maximum-maturity analysis using each team’s latest available profile. It explains that level 3 is the scale maximum and that the recommender excludes level-3 practices from further recommendations.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **§6.9 Maximum-Maturity Analysis** | Added the analysis basis, the distribution of team-level level-3 saturation, summary statistics, and a complete 35-practice table of level-3 team counts and percentages. The section notes that latest record dates vary for 12 teams and cross-references the existing maximum-maturity recommendation filter. |

## 7. Document variable team observation coverage

**Professor comment:** Explicitly mention that the number of observations varies because teams joined or left at different points during the ten-month period.

**Decision applied:** Documentation now explains that the unique team-month observations reflect variable team coverage rather than complete ten-month coverage for every team. Item 14 later corrects the analytical count to 654 while preserving the 655-row source workbook.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **§6.1 Dataset Description** | Added the full distribution of recorded months per team: 48 teams have all 10 months and 39 have 1–9 months. The section explicitly attributes the variation to teams joining or leaving the recorded population and explains that analyses use each team's available chronological history. Item 14 later corrects the one-month/two-month categories after duplicate-key resolution. |
| `README.md` | Added a concise dataset-coverage note; Item 14 later distinguishes 655 raw rows from 654 unique analytical observations. |

## 8. Identify the core innovation

**Professor comment:** Frame the novelty as the empirical approach to learning organizational behavior for prediction, rather than the specific machine learning algorithms used.

**Decision applied:** The project’s core innovation is now stated as empirically learning organizational improvement behavior to identify likely next practices. Collaborative filtering, the Practice Transition Model, and hybrid scoring are presented as established implementation tools that operationalize this contribution.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **Abstract** | Added the canonical core-innovation statement and clarified that the implementation tools operationalize the empirical approach. |
| **Executive Summary → The Approach** | Reframed the approach around empirical organizational learning before introducing the algorithmic components. |
| **§1.2 Project Objectives** | Replaced the algorithm-first objective with **Empirical Organizational Learning**. |
| **§8.1 Summary of Achievements** | Added a contribution statement distinguishing the novel empirical framing from the established algorithmic techniques. |
| `README.md` | Reframed the project summary and solution overview around empirical organizational learning. |

## 9. Include empirical practice-transition tables

**Professor comment:** Replace synthetic or typical examples of practice relationships with tables showing actual probabilities derived from the organizational data.

**Decision applied:** Documentation now reports observed transition counts and conditional frequencies calculated from the checked-in organizational dataset, rather than illustrative CI/CD, testing, or code-review pathways. The values are presented as descriptive evidence, not causal or universal adoption rules.

### Project documentation changes

| Location | Exact change |
| --- | --- |
| **§3.4, §3.7, §6.8, and §9.2** in `docs/PROJECT_DOCUMENTATION.md` | Corrected the conditional-probability denominator to all observed transitions originating from the source practice; replaced the synthetic sequence example and the 60%/55%/45% table with the top 10 observed transitions, including count, source-transition denominator, and conditional frequency. Added the associated 471-transition, 310-pair dataset summary and removed causal dependency claims. |
| `README.md` | Replaced hard-coded CI/CD/DoD/TDD relationship examples with the same top-10 empirical table and explained its calculation, sample-size context, and non-causal interpretation. |
| `docs/flowcharts/learn-sequences-up-to-month.md` | Replaced named hypothetical practice relationships in the probability illustration with generic practices A–D. |

## 10. Address optimization bias with walk-forward policy selection

**Professor comment:** Avoid tuning hyperparameters and evaluating them on the same dataset; use an earlier training portion to select parameters before applying them to later observations.

**Decision applied:** Replaced static all-history optimization with a stricter walk-forward protocol. For each prediction month, one global policy is selected only from earlier prediction months whose complete three-snapshot outcome windows had already closed. The target month and all later outcomes are excluded from selection. This produces an out-of-time evaluation for every reported month rather than reusing the evaluation outcome to select its policy.

### Project documentation changes

| Location | Exact change |
| --- | --- |
| **Abstract; Executive Summary; §§3.5–3.6; §6.3; §6.5; §9.2; §9.3; §10.4–10.6; §11.2–11.3** in `docs/PROJECT_DOCUMENTATION.md` | Documented the global monthly policy, fixed two-snapshot component windows, 675-policy selection grid, bootstrap policy, no-future-outcome boundary, and removal of the static all-history optimizer. Replaced the prior single aggregate result with separate primary results (five complete-outcome months) and sensitivity results (all seven months), including per-month policies and the independently selected time-aware-popularity comparison on the same evaluable cases. The 58.0% primary result is explicitly framed as exploratory, not proof of superiority over popularity or a per-team guarantee. |
| `README.md` | Updated the user-facing description, configuration guidance, and backtest example to explain automatic month-specific policy selection, fixed windows, the primary/sensitivity split, and the exploratory 58.0% primary result. |
| `src/ml/policy.py` and `tests/test_blend_reproduction.py` | Now provide the executable protocol and its reproduction assertions: fixed component windows, recommendable and evaluable cohorts, the walk-forward selection boundary, bootstrap behavior, and comparison arm. |

## 11. Clarify the outcome-conditioned evaluation cohort and acceleration hypothesis

**Submission-readiness review finding:** The backtest excludes team-month cases in which no
practice improved during the outcome window, but the documentation previously described the
result as general recommendation accuracy. This could be read as evidence that the system causes
teams to improve, including teams that otherwise would not improve.

**Issue classification:** Documentation and interpretation issue, not an implementation defect.
The current backtest answers a narrower but valid retrospective ranking question: when a team had
at least one subsequently observed improvement, did the recommendation list identify one of those
improved practices? Cases without an observed improvement have no successful practice against
which that historical ranking can be evaluated. The implementation was therefore retained, and
no source code was changed for this item.

**Research premise and approved interpretation:** Teams in the organization were expected to
work continuously on improving agile practices. It is plausible that many windows with no
recorded maturity increase represent attempted practices that did not succeed. However, the
dataset contains maturity snapshots only; it does not record which practices were attempted or
whether an attempt failed. The retrospective result therefore supports the system's ability to
identify practices associated with an observed next success. The claim that providing these
recommendations would help teams improve more often or faster remains the project's hypothesis
and requires a prospective pilot.

### Cohort audit

For the five primary prediction months, 298 otherwise eligible team-month cases had a complete
three-snapshot team-level outcome window:

| Cohort | Cases | Share |
| --- | ---: | ---: |
| At least one observed practice improvement | 120 | 40.3% |
| No observed practice improvement | 178 | 59.7% |
| **Total complete-window cases** | **298** | **100.0%** |

The reported primary backtest contains 121 outcome-bearing cases because the implementation uses
the snapshots available inside each globally closed outcome window; one included case has fewer
than three subsequent team-level snapshots. The stricter 298-case audit above requires all three
team-level snapshots and therefore contains 120 outcome-bearing cases.

The 178 no-improvement cases are documented as evidence of the organizational improvement
opportunity. They are not counted as failures of the model, because the historical teams did not
receive its recommendations, and they are not treated as observed failed attempts, because the
dataset does not contain attempt data.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **Abstract and Executive Summary** | Replaced general accuracy wording with **mean monthly Conditional Hit Rate@2** and stated that the reported cohort is conditioned on at least one observed improvement. Added the 298/120/178 complete-window cohort audit and distinguished retrospective alignment from causal acceleration. |
| **§3.6 Validation Methodology** | Added **Evaluation Cohort and Research Hypothesis**, defining the inclusion criteria, the global-window versus team-level-window distinction, the organizational premise, the unobserved-attempt limitation, and the data required for a causal pilot. |
| **§3.6 and §6.2 Evaluation Metrics** | Renamed the reader-facing headline metric to **Conditional Hit Rate@2** (or **Conditional Hit Rate@N** in the general definition). Clarified that the unit is an outcome-bearing recommendation case, while preserving existing implementation field names such as `overall_accuracy`. |
| **§6.3 Backtest Results** | Relabeled primary, sensitivity, and per-month results as outcome-conditioned. Explained why the primary report has 121 cases while the stricter complete-team-window audit has 120 improvement cases. |
| **§6.4, §7.1–§7.5, and §8.1–§8.2** | Reframed conclusions as retrospective recommendation alignment and pilot readiness, not proof that recommendations cause improvement or shorten adoption time. |
| **§10.4 and §10.6; §11.4 code example** | Updated the user-facing explanation and example output to use conditional hit-rate terminology. Documented that **Overall Accuracy** remains the current interface/API label for this outcome-conditioned metric. |

### Prospective validation required

To test the acceleration hypothesis, a pilot should record, for every recommendation cycle:

- the recommendations shown to the team;
- which practices the team attempted, including attempts not recommended by the system;
- successful and failed attempts;
- subsequent maturity changes; and
- time from recommendation and attempt to improvement.

This would allow comparison with an appropriate control or standard-guidance group and would test
whether access to the likely-pathways recommendations changes improvement probability or time to
improvement. The current retrospective backtest does not make that causal claim.

## 12. Correct the random baseline to use eligible candidates

**Submission-readiness review finding:** The random baseline drew from all 30 retained practices,
while the recommender draws only from practices that are below maximum maturity for the evaluated
team. It also inserted the average number of improved practices into a nonlinear probability
formula instead of calculating the exact probability for each case. This made the random baseline
too low and overstated the improvement factor.

**Issue classification:** Code implementation and evaluation-methodology issue, with consequential
documentation changes.

**Decision applied:** Random performance is now calculated separately for every outcome-bearing
case using the same eligible, non-maxed candidate set available to the recommender:

`P_i(hit) = 1 - C(n_i - k_i, top_n) / C(n_i, top_n)`

Here, `n_i` is the number of eligible candidates for the case, `k_i` is the number of those
candidates that subsequently improved, and `top_n` is 2. Case expectations are averaged within
each prediction month and the monthly values are then averaged across the reporting scope. This
matches the candidate pool and monthly macro-aggregation of Conditional Hit Rate@2.

The same candidate-aware, per-case, monthly-macro method is used for the random Precision@N,
Recall@N, and MRR comparators.

### Result changes

| Scope | Conditional Hit Rate@2 | Previous random baseline | Corrected random baseline | Corrected factor |
| --- | ---: | ---: | ---: | ---: |
| Primary | 58.0% | 26.0% | **30.6%** | **1.89x** |
| Sensitivity | 50.9% | 23.5% | **28.0%** | **1.82x** |

The model's Conditional Hit Rate@2, the time-aware-popularity comparison, and the selected monthly
policies do not change. Only the random comparison and metrics derived from it change.

The corrected primary supplementary comparisons are:

| Metric | Model | Corrected random baseline | Corrected factor |
| --- | ---: | ---: | ---: |
| Precision@N | 35.6% | 17.4% | 2.04x |
| Recall@N | 17.6% | 8.4% | 2.09x |
| MRR | 0.46 | 0.24 | 1.91x |

### Implementation and documentation changes

| Location | Exact change |
| --- | --- |
| `src/validation/backtest.py` | Replaced the all-practices/average-improvement baseline with exact per-case hypergeometric probabilities using each case's eligible candidate count and improved-candidate count. Aligned the headline and supplementary random baselines with monthly macro-aggregation. |
| `tests/test_backtest.py` | Added hand-calculated probability tests, verified that the case-specific candidate count affects the baseline, and added a two-month aggregation test that distinguishes monthly macro-averaging from pooled-case averaging. |
| `tests/test_blend_reproduction.py` | Added checked-in-dataset reproduction assertions for the corrected primary and sensitivity baselines, improvement factors, and primary supplementary baselines. |
| `docs/PROJECT_DOCUMENTATION.md` | Corrected all headline and sensitivity random-baseline figures and factors; documented the per-case formula, eligible candidate pool, aggregation rule, and corrected supplementary comparisons. |
| `README.md` | Updated the primary result table and added a concise explanation of the candidate-aware random baseline. |

## 13. Distinguish monthly macro-average from pooled hit rate

**Submission-readiness review finding:** The primary result is reported as 58.0%, while the
aggregate counts returned by the backtest are 71 hits across 121 cases, which produce 58.7% when
pooled. Without an explicit aggregation explanation, a reviewer could interpret this as an
arithmetic inconsistency.

**Issue classification:** Documentation-transparency issue, not a code implementation defect.
The implementation intentionally calculates formal scope-level metrics as monthly macro-averages,
giving each prediction month equal weight. It also returns the total hit and case counts needed to
calculate the pooled descriptive result.

**Decision applied:** Retained the mean monthly Conditional Hit Rate@2 as the headline because the
policy is selected and evaluated by prediction month, larger-team months should not dominate, and
all model-versus-baseline comparisons use the same aggregation. Added the pooled case-level rate
as a descriptive transparency measure.

| Scope | Monthly macro-average (headline) | Pooled descriptive result |
| --- | ---: | ---: |
| Primary | **58.0%** | **71/121 = 58.7%** |
| Sensitivity | **50.9%** | **81/151 = 53.6%** |

### Documentation changes

| Location | Exact change |
| --- | --- |
| **§6.2 Evaluation Metrics** in `docs/PROJECT_DOCUMENTATION.md` | Defined the monthly macro-aggregation convention and distinguished it from the pooled descriptive hit rate. |
| **§6.3 Backtest Results** in `docs/PROJECT_DOCUMENTATION.md` | Added primary and sensitivity pooled hit counts/rates beside the headline monthly figures and explained why formal comparisons remain macro-averaged. |
| `README.md` | Relabeled the headline result as mean monthly Hit Rate@2, added 71/121 = 58.7%, and documented the corresponding sensitivity figures. |

No source code was changed for this item.

## 14. Preserve and explicitly resolve the repeated team-month source key

**Submission-readiness review finding:** The source workbook contains 655 rows but only 654 unique
`(Team Name, Month)` keys. Rows 41 and 42 of `Sheet1` both describe team `ASBCE` at `20200107` and
disagree on seven practices: DoD, Story Points, Demo, Retro, Personas, Tech story template, and
Release tracker. The prior processor stored histories in a month-keyed dictionary, so the later
row silently overwrote the earlier row.

**Issue classification:** Source-data quality issue and code implementation issue, with
documentation consequences.

**Decision applied:** The raw Excel workbook remains unchanged so the original evidence and its
provenance are preserved. Validation now reports repeated team-month keys. Processing operates on
an internal copy, deterministically ignores earlier occurrences, retains the final source
occurrence, logs the resolution, and exposes observation-audit attributes containing the raw row
count, unique observation count, number of ignored rows, and affected keys.

Retaining the final occurrence formalizes the implementation's previous effective behavior. A
separate check retaining the earlier row instead confirmed that either choice produces the same
backtest rates, random baselines, time-aware-popularity comparison, and selected monthly policies.
The rule therefore does not change any reported evaluation result.

### Corrected dataset accounting

| Measure | Value |
| --- | ---: |
| Raw source rows retained in the workbook | 655 |
| Unique team-month observations used analytically | 654 |
| Earlier duplicate rows ignored during processing | 1 |

The unique-month coverage distribution now assigns three teams to one recorded month and six
teams to two recorded months. The remaining coverage categories are unchanged.

### Implementation and documentation changes

| Location | Exact change |
| --- | --- |
| `data/raw/combined_dataset.xlsx` | **No change.** Both source rows remain intact. |
| `src/data/validator.py` | Added repeated `(Team Name, Month)` detection and duplicate counts to the data-quality report. Temporal-coverage counting now uses unique team-month keys. |
| `src/data/processor.py` | Added deterministic retain-final resolution on an internal copy, warning output, and source-to-analysis observation-audit attributes. The caller's DataFrame and source workbook are not modified. |
| `tests/test_validator.py` and `tests/test_processor.py` | Added regression tests for detection, unique-key accounting, source preservation, retain-final behavior, warning output, and audit attributes. |
| `tests/test_blend_reproduction.py` | Added a checked-in-workbook assertion for 655 raw rows, 654 unique observations, one ignored row, and the `ASBCE/20200107` key. Existing reproduction checks confirm unchanged model results. |
| `docs/PROJECT_DOCUMENTATION.md` | Distinguished raw rows from unique analytical observations, corrected the team-coverage table, documented the affected source key and processing rule, and updated validation, pipeline, and scale descriptions. |
| `README.md` | Distinguished the unchanged 655-row source workbook from the 654 unique observations used in analysis. |

## 15. Replace obsolete worked examples and date encoding

**Submission-readiness review finding:** The main worked example still described the former fixed
70% similarity / 30% sequence recommender, added a final normalization step that the current scorer
does not perform, and used invented teams, scores, practices, and outcomes while calling the example
"actual data." API, CLI, data-format, and Python examples also used six-digit dates such as `200105`,
although the source and implementation use numeric `YYYYMMDD` snapshot dates. The Python example
failed with `ValueError: list.index(x): x not in list` and omitted the production missing-practice
filter.

**Issue classification:** Documentation issue, not a recommendation-algorithm implementation
defect. The current `PolicyEngine` already implements the adaptive three-factor blend.

**Decision applied:** Replaced the invented example with a reproducible `Black Pearl` / `20200803`
case from the checked-in dataset. The example reports its `20200705` baseline, selected policy,
normalized component values, direct three-factor score calculation, top-two recommendations, and
retrospective Conditional Hit@2 outcome. It explicitly states that the final blended scores are not
normalized a second time and that the retrospective match is not a causal result.

### Documentation changes

| Location | Exact change |
| --- | --- |
| **§3.7 Worked Examples** in `docs/PROJECT_DOCUMENTATION.md` | Replaced the obsolete synthetic two-factor example with an actual-data three-factor case reproduced from the current implementation. |
| **§9.2 Algorithm Details** | Corrected the scoring formula, component normalization scopes, direct ranking behavior, and deterministic tie-break. Removed the nonexistent final-normalization step. |
| **§9.3-§9.4 and §10.5** | Replaced six-digit dates with actual `YYYYMMDD` values and clarified that required columns are located by name; `Month` is the final column in the checked-in workbook. |
| **§11.4 Code Examples** | Added validation and the production 90%-missing-practice filter, changed to a valid team/date case, and displayed the serializable selected-policy audit record. |

No recommendation implementation or source-workbook data was changed for this item.

## 16. Align the high-level architecture descriptions with the three-factor model

**Submission-readiness review finding:** Several overview sections still described the system as a
two-signal hybrid of collaborative filtering and sequence learning. They omitted time-aware
popularity and the global monthly `PolicyEngine`, called the transition signal "content-based," and
described recommendation scores as probabilities of success even though they are uncalibrated
relative ranking scores.

**Issue classification:** Documentation issue only. The implementation already combines
similarity, sequence, and time-aware popularity under one policy selected per prediction month.

**Decision applied:** Updated the conceptual overview, methodology summary, data flow, and user
manual overview to name all three evidence sources and the monthly policy-selection stage. The
transition component is now characterized as empirical sequential evidence rather than conventional
content-based recommendation, and output scores are described as combined historical-evidence
scores rather than calibrated success probabilities.

### Documentation changes

| Location | Exact change |
| --- | --- |
| **§2.4 Hybrid Recommendation Approaches** in `docs/PROJECT_DOCUMENTATION.md` | Defined the current three-signal hybrid and distinguished transition evidence from conventional content-based recommendation. |
| **§3.1 System Architecture Overview** | Added popularity and monthly policy selection to processing; replaced the success-probability claim with relative historical-evidence ranking language. |
| **§4.3 Data Flow** | Routed recommendation generation through `RecommendationEngine` and `PolicyEngine`, showing similarity, transition, popularity, completed-prior-month policy selection, and candidate filtering. |
| **§10.1 System Overview** | Updated the user-facing summary to explain all three signals and their month-specific global weighting policy. |

No source code or source-workbook data was changed for this item.

## 17. Correct and contextualize the CHAOS Report comparison

**Submission-readiness review finding:** The background stated that companies implementing agile
had approximately four times the probability of success, without identifying the source. The
statement was based on The Standish Group's *CHAOS Report 2015*, but the report's unit is software
projects rather than companies and its all-project figures are 39% for agile and 11% for waterfall
(approximately 3.5 times). The same section described multi-year transformations as a general
research fact even though that statement reflects the author's practical experience.

**Issue classification:** Documentation accuracy and attribution issue only.

**Decision applied:** Corrected the unit and figures, named *CHAOS Report 2015* and page 7 directly
in the text, and clarified that the comparison is an association rather than proof that the project
approach caused the outcome. The transformation-duration statement is now explicitly identified as
practitioner experience. Because this is practical-project documentation and only one external
report is invoked, no standalone bibliography was added.

No source code, tests, README content, or source-workbook data was changed for this item.

## 18. Align the documented REST API contract with the implemented routes

**Submission-readiness review finding:** The API section repeated endpoint number 4, described the
`/api/sequences` response as a list instead of its actual structured object, named the wrong Excel
attachment filename, and said every response was JSON even though the data and documentation
endpoints return Excel and plain text. It also omitted Pydantic's HTTP 422 response and did not
distinguish the implemented 400 and 404 cases. The request model's generated OpenAPI description
still referred to a six-digit `YYMMDD-style` value.

**Issue classification:** API documentation issue plus one code-level API-metadata issue. There was
no recommendation-algorithm or route-behavior defect.

**Decision applied:** Documented the existing REST contract rather than changing runtime behavior.
The endpoint list is numbered 1 through 9, response structures and content types match the routes,
and the 400/404/422/500 cases are distinguished. The `RecommendationRequest.month` field description
now says `YYYYMMDD`, keeping generated OpenAPI documentation consistent with the source data.

### Changes

| Location | Exact change |
| --- | --- |
| **§4.4 API Design** in `docs/PROJECT_DOCUMENTATION.md` | Clarified that application-data endpoints use JSON while `/api/example-data` returns Excel and `/api/docs` returns plain-text Markdown. |
| **§9.3 API Documentation** | Corrected endpoint numbering, sequence-response shape, download filename, documentation content type, and HTTP error-status descriptions. |
| `src/api/models.py` | Corrected the generated OpenAPI description of `RecommendationRequest.month` from `YYMMDD-style` to `YYYYMMDD`; runtime validation and behavior are unchanged. |

No route logic, recommendation implementation, tests, README content, or source-workbook data was
changed for this item.

## 19. Correct the code-organization and performance descriptions

**Submission-readiness review finding:** The accurate count of 23 Python modules was accompanied by
volatile and outdated line-count estimates. The documentation incorrectly assigned random-baseline,
improvement-factor, and aggregate calculations to `MetricsCalculator`; claimed chunked processing
that is not implemented; and described the async behavior more broadly than the code supports. The
repository tree was also presented as complete even though it intentionally showed only key files.

**Issue classification:** Documentation issue only. No runtime behavior was defective.

**Decision applied:** Retained the verified 23-module count while removing line-count estimates.
Clarified that `BacktestEngine` calculates Conditional Hit Rate@2, random baselines, improvement
factors, and aggregate scopes, while `MetricsCalculator` supplies the per-list proportion used as
Precision@N and MRR. Replaced the chunk-processing claim with the actual in-memory pandas approach,
described the single-worker backtest offload precisely, and labeled the directory tree as abridged.

No source code, tests, README content, or source-workbook data was changed for this item.

## 20. Limit scalability claims to the evidence demonstrated

**Submission-readiness review finding:** Several remaining statements claimed 100–200 MB memory
usage without a benchmark, linear algorithmic scaling, support for real-time updates, and
demonstrated large-organization scalability. The code loads a workbook into memory at startup,
similarity evidence scans historical team states, and policy selection evaluates as many as 675
policies across the eligible cases. A larger peer count expands peer evidence rather than the
target team's candidate set.

**Issue classification:** Documentation overstatement, not a defect for the submitted dataset or
supervised pilot scope.

**Decision applied:** Removed the unmeasured memory figure and linear/real-time claims. The report
now limits demonstrated performance to the submitted 87-team, 35-raw-practice, 10-snapshot dataset,
describes the current monthly restart-and-reload workflow, and identifies profiling, load testing,
indexed/vectorized search, persistent storage, and database-backed processing as possible needs for
larger deployment. "Candidate coverage" was corrected to "peer-evidence coverage."

No source code, tests, README content, or source-workbook data was changed for this item.

## 21. Correct two residual model-description statements

**Submission-readiness review finding:** A follow-up scan found that the strengths section still
described a two-signal hybrid and that two limitations sections called recommendations
"probabilistic," although the implementation produces uncalibrated evidence-based ranking scores.

**Issue classification:** Documentation issue only.

**Decision applied:** The strength now names peer similarity, practice-transition evidence, and
time-aware popularity under the global monthly policy. The scope and algorithm limitations now
state that outputs are evidence-based rankings rather than calibrated success probabilities or
guarantees.

No source code, tests, README content, or source-workbook data was changed for this item.

## 22. Make deployment-readiness language consistently pilot-scoped

**Submission-readiness review finding:** The report's detailed limitations correctly described a
functional prototype without authentication, monitoring, automated ingestion, multi-user design,
or deployment infrastructure, but later sections still called it "ready for deployment," claimed
deployment requirements were met, and described error handling as robust and documentation as
complete.

**Issue classification:** Documentation issue only. The implementation is suitable for the stated
supervised-pilot scope, not a hardened production deployment.

**Decision applied:** Renamed the conclusion section to "Pilot Deployment Readiness," explicitly
limited readiness to a small supervised pilot, and relabeled demonstrated capabilities accordingly.
The report now describes prototype-level validation/error handling, on-demand recommendations from
startup-loaded data, and documentation for methodology, installation, operation, and pilot use.
"Real-World Ready" was replaced with the narrower "Organizational Data Fit," and deployment next
steps were reframed as controlled-pilot steps.

No source code, tests, README content, or source-workbook data was changed for this item.

## 23. Correct the missing-recommendations troubleshooting guidance

**Submission-readiness review finding:** The troubleshooting section advised users to check whether
the team improved during the later validation window when no recommendations appeared. Subsequent
improvement is not a recommendation-eligibility condition; it determines only whether retrospective
validation is available.

**Issue classification:** Documentation issue only.

**Decision applied:** The troubleshooting guidance now directs users to the returned message and the
actual eligibility requirements: a valid team and prediction snapshot, an earlier baseline, and at
least two practices below maximum maturity. It explicitly separates recommendation availability
from subsequent-outcome validation.

No source code, tests, README content, or source-workbook data was changed for this item.

## 24. Update application metadata to name the current three-factor model

**Submission-readiness review finding:** The CLI header, FastAPI description, and ML package
docstring still advertised only collaborative filtering and sequence learning. These strings were
visible to CLI users, generated API-documentation users, or code reviewers and omitted time-aware
popularity and monthly policy selection.

**Issue classification:** Code-level presentation and metadata issue, not an algorithm defect.

**Decision applied:** Updated the CLI header to identify the adaptive similarity/sequence/popularity
blend, expanded the FastAPI description to name all three evidence sources and the monthly selected
policy, and aligned the ML package docstring with the current model.

No algorithm, API behavior, tests, project-documentation content, README content, or
source-workbook data was changed for this item.

## 25. Rename the Precision@N helper to match its formula

**Submission-readiness review finding:** `MetricsCalculator.calculate_hit_rate()` returned the
proportion of recommendations that matched observed improvements. That formula is Precision@N, not
the binary per-case Hit Rate@N used as the project's headline metric. `BacktestEngine` already used
the value correctly as precision, so no reported calculation was wrong, but the method name made
the two metrics easy to confuse.

**Issue classification:** Code naming and maintainability issue, not a metric-formula defect.

**Decision applied:** Renamed the helper to `calculate_precision_at_n()`, updated its docstring,
backtest call, focused tests, and code-documentation references. The formula and all reported
results remain unchanged.

No recommendation scoring, backtest formula, API contract, README content, or source-workbook data
was changed for this item.

## 26. Distinguish recorded snapshots from calendar months

**Submission-readiness review finding:** The validation-methodology summary said that improvements
may occur one to three months after a recommendation. The implementation actually evaluates the
next three recorded team snapshots. For teams with incomplete monthly coverage, those snapshots
can span more than three calendar months.

**Issue classification:** Documentation issue only; the implementation already uses the intended
three-snapshot outcome window.

**Decision applied:** Replaced the calendar-month wording with an explicit three-recorded-snapshot
horizon and noted that it does not necessarily equal three calendar months.

No source code, calculations, reported results, API behavior, or source-workbook data was changed
for this item.

## 27. Replace arithmetic month notation with the implemented snapshot boundary

**Submission-readiness review finding:** Two validation summaries described the outcome window as
`test_month`, `test_month+1`, and `test_month+2`. This notation implied arithmetic calendar-month
increments, while the implementation selects up to the first three recorded team snapshots after
that team's baseline. The first such snapshot can be at or after the global prediction month,
depending on the team's data coverage.

**Issue classification:** Documentation issue only; the implementation already uses the intended
snapshot-based boundary.

**Decision applied:** Updated both validation summaries to describe the outcome window as up to the
first three recorded team snapshots after the baseline.

No source code, calculations, reported results, API behavior, or source-workbook data was changed
for this item.

## 28. Correct stale BacktestEngine model labels

**Submission-readiness review finding:** The module and class docstrings in
`src/validation/backtest.py` described the model as a "global two-month adaptive blend." That label
did not accurately distinguish monthly policy selection, the three-factor blend, the two-snapshot
component windows, and the three-snapshot evaluation window.

**Issue classification:** Code-documentation issue, not an implementation defect.

**Decision applied:** Changed both docstrings to describe the model as a global monthly adaptive
three-factor blend.

No runtime behavior, calculations, tests, project-documentation content, API contract, or
source-workbook data was changed for this item.

## 29. Remove the remaining stale model labels and broken specification links

**Submission-readiness review finding:** Eleven additional source, test, and internal-guidance
references still called the system a "global two-month adaptive blend," even though the model uses
monthly policy selection, three evidence factors, fixed two-snapshot component windows, and a
three-snapshot outcome window. Three code docstrings also linked to
`docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_REQUIREMENTS-refined.md`, which is not present in the
repository.

**Issue classification:** Documentation and terminology issue across source docstrings, test
documentation, and internal project guidance; not an implementation defect.

**Decision applied:** Replaced the eleven remaining stale labels with "global monthly adaptive
three-factor blend" wording and redirected the three broken specification references to the
authoritative `docs/PROJECT_DOCUMENTATION.md`. The updates cover 14 textual references across nine
files, including `CLAUDE.md`.

No runtime behavior, recommendation scoring, backtest calculations, test logic, API contract,
reported results, or source-workbook data was changed for this item.

## 30. Correct the DataProcessor missing-value docstring

**Submission-readiness review finding:** The `DataProcessor.process()` docstring said that replacing
missing values with zero was "not implemented," while the method already performs that replacement
for every practice column on its internal working copy. The project documentation correctly
describes the implemented behavior.

**Issue classification:** Code-documentation issue, not an implementation defect.

**Decision applied:** Removed the incorrect "not implemented" label and clarified that NaN practice
values are replaced with zero in an internal working copy.

No processing behavior, calculations, tests, project-documentation content, raw input data, or
source-workbook data was changed for this item.

## 31. Clarify organizational reach without claiming batch recommendation delivery

**Submission-readiness review finding:** The practical-implications section claimed that the system
could serve more than 70 teams "simultaneously." No concurrency or load test supports that wording,
and the operational web/API flow currently accepts one team per recommendation request. The
intended benefit was that one automated method can replace manual observation across dozens of
teams; additionally, one backtest run does evaluate eligible cases across many teams.

**Issue classification:** Documentation issue. A claim that one operational request generates
recommendations for dozens of teams would instead require a batch-interface implementation.

**Decision applied:** Replaced the simultaneous-service claim with an organizational-reach
statement: the pipeline applies one method across the submitted dataset's 87 teams, a backtest run
evaluates eligible cases across dozens of teams, and operational recommendations remain per-team.

No batch feature, runtime behavior, calculations, tests, API contract, or source-workbook data was
changed for this item.

## 32. Remove the two remaining simultaneous-service claims

**Submission-readiness review finding:** After clarifying the practical-implications section, the
Executive Summary and manual-analysis comparison still repeated the unsupported claim that the
system could serve more than 70 teams simultaneously. The implementation can apply one model
across the 87-team dataset and can evaluate dozens of eligible cases in one backtest, but its
operational recommendation interface remains per-team.

**Issue classification:** Documentation issue only; no batch or concurrency implementation was
claimed or required by the approved wording.

**Decision applied:** Replaced both residual simultaneous-service statements with explicit,
evidence-aligned descriptions of dataset-wide methodological reach, multi-team backtesting, and
per-team operational recommendations.

No runtime behavior, calculations, tests, API contract, batch feature, or source-workbook data was
changed for this item.

## 33. Correct the remaining prose uses of the old model name

**Submission-readiness review finding:** The §3.5 heading and the backtest sequence-diagram
description still called the model a "two-month" blend. That wording did not distinguish monthly
policy selection, three evidence factors, two-snapshot component windows, and the three-snapshot
outcome window.

**Issue classification:** Documentation issue only.

**Decision applied:** Renamed §3.5 to "Global Monthly Adaptive Three-Factor Blend Scoring" and
updated the sequence-diagram description to say that the blend is replayed prediction month by
prediction month. The existing research-result filename containing `fixed-two-month` was preserved
because it is a real artifact path; literal code comments about comparing two snapshots were also
left unchanged.

No runtime behavior, calculations, tests, API contract, research artifact, or source-workbook data
was changed for this item.

## 34. Correct the DataLoader example statistics

**Submission-readiness review finding:** The `DataLoader.load()` docstring example named the
checked-in cleaned workbook but claimed 87 teams, 30 practices, 10 months, and 870 rows. Loading
that workbook produces 87 teams, 35 raw practice columns, 10 months, and 655 source rows. The
30-practice count applies only after a later missing-data filter, not at the loading stage.

**Issue classification:** Code-documentation issue, not a loader implementation defect.

**Decision applied:** Replaced the simulated, inaccurate console output with an executable example
that reports `(87, 35, 10, 655)` from the loader attributes and loaded DataFrame.

No loader behavior, filtering logic, tests, project-documentation content, or source-workbook data
was changed for this item.

## 35. Replace placeholder practice names in the DataLoader example

**Submission-readiness review finding:** After correcting the DataLoader example's counts, its
final line still showed placeholder practices (`Practice A`, `Practice B`, and `Practice C`) even
though the example names the checked-in cleaned workbook. Its actual first three practice columns
are `Product Owner`, `Scrum Master`, and `Multi function team`.

**Issue classification:** Code-documentation issue only.

**Decision applied:** Replaced the placeholder output with the three practice names actually
returned by the example workbook.

No loader behavior, practice ordering, tests, project-documentation content, or source-workbook
data was changed for this item.

## 36. Distinguish on-demand recommendations from real-time data ingestion

**Submission-readiness review finding:** Two report sections described recommendations as
"real-time" and based on "current data." The system calculates recommendations on demand, but it
loads the organizational dataset from an Excel workbook at application startup and has no live
data feed or automatic refresh.

**Issue classification:** Documentation issue, not an implementation defect.

**Decision applied:** Replaced both real-time-data statements with wording that accurately
describes on-demand recommendations based on the organizational dataset loaded at startup.

No runtime behavior, data-loading process, tests, API contract, automatic-refresh feature, or
source-workbook data was changed for this item.

## 37. Replace nonexistent console output in processing examples

**Submission-readiness review finding:** The `DataProcessor.process()` and
`SequenceMapper.learn_sequences()` docstring examples displayed progress and count messages even
though neither method writes those messages to standard output. Both methods return `None` and
signal completion through internal state.

**Issue classification:** Code-documentation issue, not an implementation defect.

**Decision applied:** Replaced the four nonexistent output lines with checks showing that
`processor.processed` and `mapper.learned` become `True` after their respective methods run.

No runtime behavior, logging, calculations, tests, project-documentation content, or
source-workbook data was changed for this item.

## 38. Remove the misunderstood Uvicorn keep-alive override

**Submission-readiness review finding:** `src/web_main.py` described
`timeout_keep_alive=300` as a five-minute allowance for long-running optimization requests. The
optimization endpoints no longer exist, and Uvicorn's keep-alive timeout controls how long an idle
persistent connection waits for new data; it does not extend the duration permitted for a running
backtest request. Backtest work is already offloaded from the event loop by the API.

**Issue classification:** Code configuration issue plus code-documentation issue; not a backtest
algorithm defect.

**Decision applied:** Removed the five-minute idle keep-alive override so Uvicorn uses its default,
kept the 30-second graceful-shutdown setting, removed the obsolete optimization-timeout note, and
replaced the nearby comment with a neutral server-start description.

No recommendation behavior, backtest execution path, calculations, tests, API schema, reported
results, or source-workbook data was changed for this item. Runtime behavior changes only for idle
persistent HTTP connections.

## 39. Return a failure status when the CLI workbook is missing

**Submission-readiness review finding:** `src/main.py` documented an exit code of `1` for missing
input files, but its two missing-workbook branches used bare `return` statements. Because the
entry point passes the result to `sys.exit()`, those branches produced operating-system status `0`
despite printing an error.

**Issue classification:** Code implementation issue; the documented exit-code contract was
already correct.

**Decision applied:** Changed both missing-workbook branches to return `1` and added regression
tests for a missing default workbook and a missing explicitly supplied workbook.

**Verification:** `tests/test_runtime_versions.py` passes all 12 tests, and Ruff passes for
`src/main.py` and `tests/test_runtime_versions.py`.

No successful-startup behavior, recommendation logic, backtest calculation, API contract,
project-documentation content, or source-workbook data was changed for this item.

## 40. Correct the entrypoint command examples

**Submission-readiness review finding:** The `main()` docstrings in `src/main.py` and
`src/web_main.py` presented shell commands with Python interactive prompts (`>>>`), making them
invalid as Python examples. They also showed simulated output, including web-server output that no
longer matched the current logger messages. The CLI module-level usage omitted the `src/` path
required when running from the repository root.

**Issue classification:** Code-documentation issue only.

**Decision applied:** Reformatted both function examples as shell commands run from the repository
root, removed simulated output, and corrected the CLI usage and example paths to
`python src/main.py`.

No entrypoint behavior, logging, calculations, tests, API contract, project-documentation content,
or source-workbook data was changed for this item.

## 41. Align entrypoint return-code documentation with handled errors

**Submission-readiness review finding:** The CLI and web `main()` docstrings claimed that missing
files, invalid data, general startup exceptions, and (for the web server) `KeyboardInterrupt` were
raised to callers. Both entrypoints instead handle startup errors and return status `1`; the web
entrypoint handles Ctrl+C as a normal shutdown with status `0`. Validator findings can also be
reported as warnings without terminating startup.

**Issue classification:** Code-documentation issue only.

**Decision applied:** Removed both inaccurate `Raises` sections and expanded their `Returns`
descriptions to document the implemented success, handled-error, and web Ctrl+C exit statuses.

No entrypoint behavior, exception handling, validation policy, calculations, tests, API contract,
project-documentation content, or source-workbook data was changed for this item.

## 42. Regenerate and verify the submission PDF

**Submission-readiness review finding:** The generated
`output/pdf/PROJECT_DOCUMENTATION.pdf` predated the approved corrections to the canonical Markdown
report and therefore did not contain the final reviewed content.

**Issue classification:** Generated-documentation artifact issue, not a code implementation
defect.

**Decision applied:** Rebuilt the PDF from the updated `docs/PROJECT_DOCUMENTATION.md` using the
repository's existing report-build workflow, then checked its structure, extracted text, table of
contents, page numbering, and rendered page layout.

No recommendation behavior, calculations, tests, API contract, report-generation code, or
source-workbook data was changed for this item.

## 43. Make zip length handling explicit

**Submission-readiness review finding:** Ruff reported 15 `zip()` calls without an explicit
`strict=` setting. Fourteen pair practice names or maturity-score vectors that are required to have
equal lengths, where silent truncation could conceal malformed internal data. One pairs a sequence
of improvement-bearing steps with its one-position offset and is intentionally unequal in length.

**Issue classification:** Code-quality and defensive-implementation issue, not a documentation or
algorithm-formula defect.

**Decision applied:** Added `strict=True` to the fourteen equal-length comparisons and
`strict=False` to the intentionally offset transition-step pairing.

**Verification:** Ruff no longer reports B905 for the affected files. The complete non-UI suite
passes with 181 tests passed and 12 skipped, and `git diff --check` is clean.

No valid-data recommendation behavior, backtest calculations, API contract, reported results, or
source-workbook data was changed for this item. Malformed unequal-length inputs now fail visibly
instead of being silently truncated.

## 44. Preserve causes when converting caught exceptions

**Submission-readiness review finding:** Ruff reported eight caught exceptions that were replaced
with new exceptions without explicit chaining. Seven API route handlers convert unexpected errors
into generic HTTP 500 responses, and `DataLoader` converts an Excel-reading failure into a
`ValueError`. Without `from e`, their causal relationship is less explicit in diagnostic
tracebacks.

**Issue classification:** Code-quality and diagnostic issue, not a documentation or functional
behavior defect.

**Decision applied:** Added `from e` to all eight replacement raises, preserving their original
causes for internal diagnosis while retaining the existing public exception types and messages.

**Verification:** Ruff no longer reports B904. The complete non-UI suite passes with 181 tests
passed and 12 skipped, and `git diff --check` is clean.

No recommendation behavior, calculations, API response body, HTTP status, reported results, or
source-workbook data was changed for this item.

## 45. Move API imports before module-level initialization

**Submission-readiness review finding:** Ruff reported seven E402 violations because
`src/api/routes.py` initialized its logger and thread-pool executor before local imports, while
`src/api/service.py` initialized its logger before five project imports. The modules worked, but
the ordering was surprising and failed the repository's source lint check.

**Issue classification:** Code-quality and maintainability issue, not a documentation or runtime
behavior defect.

**Decision applied:** Grouped standard-library, third-party, and local imports before module-level
logger and executor initialization in both API modules.

**Verification:** Ruff reports no E402 or import-block-order finding in the affected files. The
complete non-UI suite passes with 181 tests passed and 12 skipped, and `git diff --check` is clean.

No imported dependency, executor configuration, API behavior, calculations, reported results, or
source-workbook data was changed for this item.

## 46. Clear the remaining mechanical source-lint findings

**Submission-readiness review finding:** After the substantive lint categories were resolved,
seven mechanical findings remained: two whitespace-only blank lines, one redundant read-mode
argument, one unnecessary list conversion inside `sorted()`, two unused assignments, and one
unused loop variable.

**Issue classification:** Code-quality cleanup, not a documentation or functional behavior issue.

**Decision applied:** Removed the blank-line whitespace, redundant `"r"` mode, unnecessary
`list()` conversion, and unused assignments; renamed the unused loop value with an underscore
prefix.

**Verification:** Ruff passes across all files under `src/`. The complete non-UI suite passes with
181 tests passed and 12 skipped.

No recommendation behavior, calculations, API contract, reported results, or source-workbook data
was changed for this item.

## 47. Make test targets use the project Python interpreter

**Submission-readiness review finding:** Several Makefile targets invoked bare `python`, `pip`,
or `pytest`. On the review machine, `python` resolves to Python 2.7, so `make test-ui` failed before
test collection even though the suite passed when invoked with the project's virtual-environment
interpreter.

**Issue classification:** Build and test-tooling implementation issue, not a documentation or
application behavior defect.

**Decision applied:** Added a `PYTHON` Make variable that prefers `.venv/bin/python` when the
project virtual environment exists and otherwise falls back to `python3`. Routed dependency
installation and all pytest-based Makefile targets through `$(PYTHON) -m ...`.

**Verification:** `make test` selected `.venv/bin/python` and completed with 181 tests passed and
12 skipped. `make test-ui` selected the same interpreter and completed with all 6 browser tests
passed. Ruff passes across all files under `src/`, and `git diff --check` is clean.

No recommendation behavior, calculations, API contract, reported results, or source-workbook data
was changed for this item.

## 48. Describe the static-analysis aggregate as an advisory audit

**Submission-readiness review finding:** `make check-all` suppressed nonzero exit statuses from
mypy, Pylint, Ruff, and pydocstyle, then printed `All checks complete!`. README recommended the
target and CLAUDE.md described its rules as enforced, although the current audit reports 65 mypy
errors in 11 files and additional Pylint and pydocstyle findings. Ruff passes.

**Issue classification:** Build and quality-tooling implementation issue with a documentation-
alignment consequence, not an algorithm or application behavior defect.

**Decision applied:** Retained the existing checks as a non-blocking legacy-code audit, but made
that status explicit in the Makefile help and completion message, README, and CLAUDE.md. The
documentation now identifies the automated tests and Ruff as the currently enforced passing
checks. This avoids misrepresenting known static-analysis debt as a successful quality gate.

**Verification:** Makefile help identifies `make check-all` as advisory; its completion message
instructs the reader to review reported findings. README and CLAUDE.md now use the same semantics,
Ruff passes across `src/`, and `git diff --check` is clean.

No static-analysis finding was suppressed in tool configuration, and no recommendation behavior,
calculations, tests, API contract, reported results, or source-workbook data was changed for this
item.

## 49. Add the project repository to the submitted report

**Submission-readiness review finding:** The canonical project documentation did not identify the
GitHub repository containing the submitted implementation.

**Issue classification:** Documentation and submission-packaging issue, not a code implementation
or algorithm defect.

**Decision applied:** Added the configured GitHub repository URL to the report metadata and made it
a visible, clickable `Project repository` entry on the PDF title page.

**Verification:** Rebuilt the PDF from the canonical Markdown source, confirmed that the repository
URL is present in the extracted PDF text and link annotations, and visually inspected the rendered
title page for alignment and legibility.

No recommendation behavior, calculations, tests, API contract, reported results, or source-workbook
data was changed for this item.
