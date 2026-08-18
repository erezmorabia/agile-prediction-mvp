# Flow 3 — System Startup

Loads the Excel dataset, validates and filters it, and builds the ML engines the app depends on,
all before the web server starts accepting requests. It isn't a user-triggered use case, but it
explains how the recommendation, backtest, and sequence-exploration flows are initialized.

**Trigger**: none — runs once when `web_main.py` starts.

**Participants**: `web_main.py` (the orchestrator — plays the same role `Browser` plays in the other
three flows), plus two grouped backend stages:
- `Data Pipeline` — groups `DataLoader`, `DataValidator`, and `DataProcessor`, which run one after
  another to turn the raw Excel file into a clean, per-team practice-history dataset.
- `ML Engines` — groups `SimilarityEngine`, `SequenceMapper`, and `RecommendationEngine` (which
  owns a `PolicyEngine`), built from that dataset.

```mermaid
sequenceDiagram
    participant WebMain as web_main.py
    participant Data as Data Pipeline
    participant ML as ML Engines

    WebMain->>Data: load the Excel file
    Note right of Data: reads the raw spreadsheet into a table
    WebMain->>Data: validate, then filter out unreliable practices
    Note right of Data: logs data-quality warnings (never blocks startup),<br/>drops practices missing over 90% of their values
    WebMain->>Data: normalize scores and build team histories
    Note right of Data: rescales 0-3 maturity scores to 0-1,<br/>produces the per-team history everything else reads
    Data-->>WebMain: ready

    WebMain->>ML: build the similarity engine
    Note right of ML: enables cosine-similarity lookups between teams
    WebMain->>ML: build the transition model, learn practice transitions
    Note right of ML: learns practice-transition probabilities from<br/>the full history, done eagerly here so the Practice Transitions tab<br/>(UC-04) has data immediately - Flows 1-2 later overwrite<br/>this same matrix in place, scoped to a recommendation month
    WebMain->>ML: build the recommendation engine and PolicyEngine
    Note right of ML: wires the engines together<br/>construction does no policy selection<br/>the global blend is selected lazily per prediction month

    WebMain->>WebMain: wire up the API layer and start the web server
    Note right of WebMain: builds APIService around the recommender,<br/>then starts listening for requests on port 8000
```

## Notes

- **Why these two groups**: nothing inside the "Data Pipeline" stage or the "ML Engines" stage talks
  back to `web_main.py` mid-step or to each other directly — `web_main.py` constructs each piece and
  hands it to the next, in a straight line. Grouping them keeps this diagram to 3 lifelines instead
  of 7, since the point here is "what gets built, in what order," not call-and-response between
  components (see `docs/PROJECT_DOCUMENTATION.md` §4.1 for the full component breakdown if you need
  the individual class names).
- **Correction vs. a prior claim in `architecture.md`**: the missing-value filter
  (`DataValidator.filter_high_missing_practices()`) does **not** mutate the practices list in
  place — it returns a new, filtered list, and `web_main.py` reassigns its local variable to that.
- **Practice-transition learning is eager here, lazy everywhere else — and gets overwritten in place**:
  `SequenceMapper.learn_sequences()` runs once at startup across the full history, populating
  `self.transition_matrix`/`self.practice_popularity`. `PolicyEngine` later calls
  `learn_sequences_up_to_month(max_month)`, which rebuilds those same attributes using only
  observations before the recommendation baseline. The Practice Transitions tab deliberately
  restores the all-history view before reading it: `APIService.get_improvement_sequences()` calls
  `learn_sequences()` on every request. Cutoff-specific sequence results are cached in
  `_sequence_cache` for repeated policy evaluation.
- **"Building" the recommendation engine is just wiring**: `RecommendationEngine.__init__`
  (`src/ml/recommender.py:11-23`) only stores references to the already-built `similarity_engine`,
  `sequence_mapper`, and `practices` (plus `processor`, pulled off `similarity_engine`) — no
  computation happens here. It still gets its own step in this diagram because `RecommendationEngine`
  is a named lifeline in Flows 1-2 (see `01-get-recommendations.md`, `02-run-backtest.md`); this is
  where that object comes into existence before those flows call it. The actual three-factor
  scoring and monthly policy selection happen later, per request, inside `PolicyEngine`.
- `DataValidator.validate()`'s pass/fail result is discarded by `web_main.py` — a failed check only
  produces warning log lines, it never blocks startup.

References: `web_main.py`, `src/data/validator.py`, `src/ml/sequences.py`,
`src/api/service.py`, `src/ml/recommender.py`, and `src/ml/policy.py`.
