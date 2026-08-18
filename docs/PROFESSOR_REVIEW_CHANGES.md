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

**Professor comment:** Remove the term “Big Data”; a dataset of approximately 30,000 observations (87 teams × 35 practices × 10 months) is not considered big by modern data-science standards.

**Decision applied:** The documentation now describes the dataset as a **moderate-sized organizational dataset** of approximately 30,000 practice-level maturity values. It discusses processing efficiency and future scalability without claiming Big Data capability.

### Project documentation changes

The following edits were made in `docs/PROJECT_DOCUMENTATION.md`:

| Section | Exact change |
| --- | --- |
| **Executive Summary → System Capabilities** | Replaced “Handles large-scale data efficiently” with an accurate statement that the system processes the project dataset efficiently, including the dimensions and approximate number of practice-level maturity values. |
| **§5.4 Performance Considerations** | Renamed **Big Data Handling** to **Performance and Scalability**. |
| **§7.1 How Implementation Addresses Proposal Objectives** | Replaced the large-scale-data claim with “Processes the project dataset efficiently.” |
| **§7.2 Strengths** | Replaced the claim that the algorithms handle large datasets with a forward-looking scalability statement tied to growth beyond the current project dataset. |
| **§7.6 Dataset Scale and Efficiency** | Renamed **Big Data Handling Capabilities** to **Dataset Scale and Efficiency** and added an explicit description of the dataset as moderate-sized (87 teams × 35 practices × 10 months; approximately 30,000 practice-level maturity values). |

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
| **§3.3 Collaborative Filtering Algorithm and §3.7 Worked Examples** | Replaced “improved in the next 1–3 months” with “subsequent observed improvement within a 1–3-month window.” |
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

**Decision applied:** Documentation now explains that the 655 team-month observations reflect variable team coverage rather than complete ten-month coverage for every team.

### Project documentation changes

| Section | Exact change |
| --- | --- |
| **§6.1 Dataset Description** | Added the full distribution of recorded months per team: 48 teams have all 10 months and 39 have 1–9 months. The section explicitly attributes the variation to teams joining or leaving the recorded population and explains that analyses use each team's available chronological history. |
| `README.md` | Added a concise dataset-coverage note next to the 655 team-month observation summary. |

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
