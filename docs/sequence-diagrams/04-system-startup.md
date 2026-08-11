# Flow 4 — System Startup

Loads the Excel dataset, validates and filters it, and builds the ML engines the app depends on,
all before the web server starts accepting requests. It isn't a user-triggered use case, but it
explains why Flows 1-3 can run quickly — the expensive setup work already happened here.

**Trigger**: none — runs once when `web_main.py` starts.

**Participants**: `web_main.py` (the orchestrator — plays the same role `Browser` plays in the other
three flows), plus two grouped backend stages:
- `Data Pipeline` — groups `DataLoader`, `DataValidator`, and `DataProcessor`, which run one after
  another to turn the raw Excel file into a clean, per-team practice-history dataset.
- `ML Engines` — groups `SimilarityEngine`, `SequenceMapper`, and `RecommendationEngine`, the three
  models built from that dataset.

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
    WebMain->>ML: build the sequence mapper, learn sequences
    Note right of ML: learns Markov transition probabilities from<br/>the full history, done eagerly here so the Sequences tab<br/>(UC-04) has data immediately - Flows 1-2 later overwrite<br/>this same matrix in place, scoped to a prediction month
    WebMain->>ML: build the recommendation engine
    Note right of ML: wires the two prebuilt engines together —<br/>construction itself does no computation,<br/>hybrid scoring runs later, per request, in Flows 1-3

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
- **Sequence learning is eager here, lazy everywhere else — and gets overwritten in place**:
  `SequenceMapper.learn_sequences()` runs once at startup across the full history, populating
  `self.transition_matrix`/`self.practice_popularity`. The Sequences tab (UC-04,
  `GET /api/sequences`) reads those two attributes directly with no re-learning call
  (`sequences.py:258`), so at startup it shows the org-wide view. Flows 1-2 instead call
  `learn_sequences_up_to_month(max_month)`, which clears and rebuilds those **same** attributes on
  the **same** `SequenceMapper` instance, scoped to months `< max_month` — there's no separate copy.
  So the first recommendation or backtest call after startup overwrites the full-history matrix in
  place, and the Sequences tab then reflects whatever `max_month` was last requested rather than the
  org-wide view it's meant to show, until the process restarts. Backtest (Flow 2) calls this **once
  per test month** as it walks the rolling window (`backtest.py:253`); results per `max_month` are
  cached (`_sequence_cache`) so repeat calls for the same month are free, but nothing restores the
  full-history state afterward.
- **"Building" the recommendation engine is just wiring**: `RecommendationEngine.__init__`
  (`src/ml/recommender.py:11-23`) only stores references to the already-built `similarity_engine`,
  `sequence_mapper`, and `practices` (plus `processor`, pulled off `similarity_engine`) — no
  computation happens here. It still gets its own step in this diagram because `RecommendationEngine`
  is a named lifeline in Flows 1-2 (see `01-get-recommendations.md`, `02-run-backtest.md`); this is
  where that object comes into existence before those flows call it. The actual hybrid-scoring
  combination happens later, per request, inside `recommend()` / `get_recommendation_explanation()`.
- `DataValidator.validate()`'s pass/fail result is discarded by `web_main.py` — a failed check only
  produces warning log lines, it never blocks startup.

Citations current as of this session (`web_main.py:173-252`, `src/data/validator.py:27-57,182-218`,
`src/ml/sequences.py:27,121`, `src/validation/backtest.py:253`, `src/ml/recommender.py:11-23`);
re-verify against the code if the implementation changes.
