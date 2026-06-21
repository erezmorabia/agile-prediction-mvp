# CLAUDE.md

ML-powered recommendation system that predicts which agile practices a team should improve next, using collaborative filtering and Markov chain sequence learning on historical data from 87 teams across 10 months.

---

## CRITICAL — Skill Loading Gate (BLOCKING PREREQUISITE)

**STOP. Before reading any code files, load relevant skills.**

This overrides all other workflows including plan mode.

**Step 1 — Identify which skills to load:**
- **Domain skills** — load any domain whose code you will touch (see Domain Skills table below). Load all domains you expect to touch.
- **UC skills** — only load if you are modifying the specific user-facing flow. Default: skip when in doubt.

**Step 2 — Invoke via the Skill tool:**
```
Skill({ skill: "domain-ml" })
Skill({ skill: "uc-01-get-recommendations" })
```

**Enforcement:** If you find yourself reading source files without having called Skill first, stop immediately and load the relevant skill(s) before continuing.

---

## Quick Reference

### Run the app
```bash
python src/web_main.py data/raw/combined_dataset.xlsx  # web UI → localhost:8000
./start_mac_linux.sh                                           # macOS/Linux shortcut
start_windows.bat                                            # Windows shortcut
```

### Test
```bash
make test                           # all tests
make test-file FILE=test_foo.py     # single file
make test-cov                       # coverage report
python -m pytest tests/ -v          # direct pytest
```

### Code quality
```bash
make check-all    # type-check + lint + check-docs
make lint         # pylint + ruff
make format       # auto-format with ruff
make fix          # ruff --fix + format
make clean        # remove cache files
```

### Install
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Guidelines and Best Practices

### Code style
- Line length: 120 chars max (soft 100)
- Classes: `PascalCase`, functions/methods: `snake_case`, constants: `UPPER_SNAKE_CASE`, private: `_prefix`
- Import order: stdlib → third-party → local (alphabetical within groups)
- All public functions require type hints and Google-style docstrings
- Full rules in `.cursor/rules/` — enforced by `make check-all`

### Data leakage prevention — CRITICAL
Never use future data in predictions. All algorithms must gate on `months < current_month` or `months <= current_month`.
After any change to `src/ml/` or `src/validation/`, run:
```bash
make test-file FILE=test_temporal_boundaries.py
```

### Testing approach
- `test_suite.py` — full pipeline integration
- `test_temporal_boundaries.py` — data leakage guard; run on every ML change
- Many pre-existing mypy issues — focus type-check on new code only

### Common pitfalls
- **Import errors:** always run from project root
- **Test failures:** verify `data/raw/combined_dataset.xlsx` exists
- **Recommendation issues:** team must exist and have ≥ 2 months of history
- **Backtest requires ≥ 4 months** of data for rolling window to start
- **PyInstaller paths:** use `get_resource_path()` in `web_main.py`; never hardcode paths

---

## Rules Files

- `.claude/rules/architecture.md` — tech stack, directory structure, API endpoints, functional domains, startup sequence, architectural constraints
- `.claude/rules/product.md` — domain story, core concepts, use cases, user journeys, validation rules

---

## Skills Reference

### Domain Skills

| Skill | Topic | Key code areas |
|---|---|---|
| `/domain-data` | Excel loading, normalization, validation, practice definitions | `src/data/` |
| `/domain-ml` | Collaborative filtering, Markov sequences, hybrid scoring | `src/ml/` |
| `/domain-validation` | Rolling window backtest, parameter optimization, accuracy metrics | `src/validation/` |
| `/domain-api` | FastAPI routes, service layer, Pydantic models, startup | `src/api/`, `src/web_main.py` |
| `/domain-frontend` | Single-page web UI, 4 tabs, API client, rendering | `web/` |

### Use Case Skills

| Skill | Topic | Load when... |
|---|---|---|
| `/uc-01-get-recommendations` | Team + month → top N practice recommendations with explanation | Changing recommendation request/response flow or UI rendering |
| `/uc-02-run-backtest-validation` | Rolling window accuracy validation against historical data | Changing backtest trigger, display, or parameter configuration |
| `/uc-03-run-parameter-optimization` | Grid search for optimal params, cancellation flow | Changing optimization workflow, param ranges, or cancel flow |
| `/uc-04-explore-improvement-sequences` | View learned Markov transition patterns | Changing the Sequences tab or sequence data display |
| `/uc-05-view-system-statistics` | System stats overview tab | Changing Statistics tab or the stats data model |

---

## After Any Feature Change — CRITICAL

Before every commit, run through this checklist:

### 1. Skill docs (update or create)
- *Changed code in an existing domain* → update `.claude/skills/domain-{name}/SKILL.md`
- *New domain* (own module + distinct data flow, no natural existing home) → **create** `.claude/skills/domain-{name}/SKILL.md` AND register it in:
  - Skills Reference table above
  - Functional Domains table in `.claude/rules/architecture.md`
  - Quick-lookup table below
- *Changed a UC flow* → update `.claude/skills/uc-{id}-{name}/SKILL.md`
- *New UC flow* → **create** `.claude/skills/uc-{id}-{name}/SKILL.md` AND register it in:
  - Skills Reference table above
  - Use Case table in `.claude/rules/product.md`

### 2. architecture.md
Update `.claude/rules/architecture.md` if module structure, API endpoints, or functional domains changed.

### 3. product.md
Update `.claude/rules/product.md` if domain concepts, use cases, or validation rules changed.

### 4. Commit together
Commit skill/doc updates in the same commit as the code change.

### Quick-lookup: changed file → skill to update

| Changed file(s) | Update this skill file |
|---|---|
| `src/data/` | `.claude/skills/domain-data/SKILL.md` |
| `src/ml/` | `.claude/skills/domain-ml/SKILL.md` |
| `src/validation/` | `.claude/skills/domain-validation/SKILL.md` |
| `src/api/`, `src/web_main.py` | `.claude/skills/domain-api/SKILL.md` |
| `web/` | `.claude/skills/domain-frontend/SKILL.md` |

### Planning-time creation trigger
If a plan introduces any of:
- A new Python module/function with its own data flow
- A new UI tab or page component with its own data fetch
- A new user-facing trigger → backend → UI flow

Then the plan must include an explicit task to create the skill file and register it in the Skills Reference table above, the Functional Domains table in `architecture.md`, and the quick-lookup table above. UC-type new flows also register in `product.md`.

### Commit-time creation check
Before committing, if any of the following are new and no skill file exists for them yet:
- A new module under `src/`
- A new UI component with its own fetch/data flow
- A new user-facing trigger → backend → UI flow

Create and commit the skill file alongside the code.
