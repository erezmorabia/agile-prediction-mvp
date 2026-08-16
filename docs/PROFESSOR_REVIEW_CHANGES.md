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
| `docs/sequence-diagrams/01-get-recommendations.md`, `02-run-backtest.md`, and `04-system-startup.md` | Reworded flow explanations from prediction terminology to recommendation terminology. |

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
