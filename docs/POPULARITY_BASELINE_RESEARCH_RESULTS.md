# Popularity Strategy Research Results

## Scope

This is an offline diagnostic research run. It does not modify the production
recommender, API, UI, or existing validation behavior.

> **Methodology correction:** the personalized similarity/sequence configuration
> used here was originally selected using the full dataset. Although the blend
> weights and switch thresholds use prior outer-month outcomes only, the base
> configuration leaks future evaluation information. Therefore none of the
> reported policy results are a leak-free confirmation; they are useful only as
> diagnostics for the fully nested study.

The harness in `scripts/research_popularity_strategies.py` evaluates three
pre-specified strategies using the existing recommendation engine and data
preparation flow:

- **Switch:** choose two popularity or two personalized recommendations from a
  prior-data convergence signal.
- **Split:** choose one popularity and one distinct personalized recommendation.
- **Blend:** rank practices from a weighted combination of popularity and
  personalized scores.

At each outer test month, switch thresholds and blend weights are selected
only from prior outer-month outcomes. Bootstrap months use the predeclared
defaults of 0.10 and 0.50 respectively.

## Primary result

The primary population includes only the five months with a complete
three-month outcome window (May through September 2020). Accuracy is the
macro-average of monthly HR@2.

| Policy | Accuracy | Gap vs. popularity | Meets strict aggregate criterion? |
|---|---:|---:|---|
| Popularity baseline | 43.57% | — | — |
| Switch | 51.17% | +7.60 pp | Yes |
| Split | 44.45% | +0.88 pp | Yes |
| Blend | 50.06% | +6.49 pp | Yes |

The switch and blend results are promising but exploratory. The switch
thresholds tested in this run were above the observed concentration values, so
the selected switch policy used the personalized path in every primary month;
it therefore does not yet establish that the convergence gate itself adds
value.

## Sensitivity result

Including all seven currently eligible months, where October and November have
shorter observed outcome windows, produces:

| Policy | Accuracy | Gap vs. popularity |
|---|---:|---:|
| Popularity baseline | 43.67% | — |
| Switch | 53.57% | +9.90 pp |
| Split | 43.06% | -0.61 pp |
| Blend | 52.78% | +9.11 pp |

## Reproduce

```bash
.research-venv/bin/python scripts/research_popularity_strategies.py \
  --output results/popularity-strategy-research-20260817.json
```

The machine-readable per-month results, selected parameters, eligible-case
counts, and prior-data convergence scores are in
`results/popularity-strategy-research-20260817.json`.

## Interpretation and next research step

The current run indicates that the pre-specified switch and blend policy arms
can beat popularity under the agreed primary metric. It does not confirm a
production improvement: the dataset is small, the historical period was used
to explore these policy families, and the underlying personalized
configuration was selected using full-dataset information.

Before any production decision, use additional unseen months or an independent
dataset. For the switch arm specifically, calibrate candidate convergence
thresholds around the observed HHI range (approximately 0.043–0.049), then run
the same pre-specified nested protocol again.

## Follow-up: calibrated switch and complete score blend

The follow-up pre-specified switch thresholds of `0.043`, `0.045`, `0.047`,
and `0.049`; it also requested all production-model scored practices before
performing the research-only blend. Neither change modifies application code.
It retains the base-configuration leakage described above and remains
diagnostic only.

| Policy | Full-window accuracy | Gap vs. popularity |
|---|---:|---:|
| Popularity baseline | 43.57% | — |
| Switch | 45.62% | +2.05 pp |
| Split | 44.45% | +0.88 pp |
| Complete-score blend | 54.92% | +11.35 pp |

The switch now uses popularity in the first outer month and personalization in
later months, so the gate is exercised. The complete-score blend is the
strongest exploratory result. Across the all-seven-month sensitivity analysis,
it scores 50.53% versus popularity's 43.67% (+6.86 pp).

Reproduce the follow-up with:

```bash
.research-venv/bin/python scripts/research_popularity_strategies.py \
  --output results/popularity-strategy-followup-20260817.json
```

## Superseded fully nested result

The first fully nested result below conditioned the evaluated cohort on whether
the selected personalized configuration returned two recommendations. That made
the popularity baseline configuration-dependent and invalidated the comparison.
It is superseded by the fixed-cohort result that follows.

## Fully nested 162-configuration result — fixed cohort

This is the first valid result in this document that removes the
base-configuration leakage. For every outer month, the personalized similarity/sequence
configuration was selected from a predeclared 162-configuration grid using
only earlier months whose full three-month outcome window had already closed.
Switch thresholds and blend weights were selected under the same rule.

Every policy is evaluated on the same fixed cohort: team/month cases with an
observed outcome and two eligible popularity recommendations. A personalized
recommendation failure remains in that cohort and is a miss for the pure
personalized policy.

The first three months necessarily use a predeclared bootstrap configuration;
August and September are the only primary-window months with one and two
completed inner evaluations respectively. This is an unavoidable limitation of
the ten-month dataset, not an exception to the protocol.

| Policy | Full-window accuracy | Gap vs. popularity |
|---|---:|---:|
| Popularity baseline | 42.85% | — |
| Nested personalized | 42.58% | -0.26 pp |
| Nested switch | 38.77% | -4.07 pp |
| Nested split | 40.58% | -2.27 pp |
| Nested complete-score blend | **51.44%** | **+8.59 pp** |

The all-seven-month sensitivity result for blending is 46.26% versus 44.29%
popularity (+1.97 pp). The blend's primary result meets the agreed strict
aggregate criterion, but the small number of genuinely retuned primary months
makes it exploratory rather than a production decision.

The run is reproducible with:

```bash
.research-venv/bin/python scripts/research_fully_nested_popularity.py \
  --output results/fully-nested-popularity-fixed-cohort-20260817.json
```
