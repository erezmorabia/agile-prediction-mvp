# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Agile Practice Prediction System** that uses machine learning to recommend which agile practices teams should focus on next. The system combines collaborative filtering with Markov chain sequence learning to analyze patterns from historical organizational data (87 teams, 35 practices, 10 months).

**Core Business Value**: Provides data-driven recommendations for agile transformation, achieving 49% prediction accuracy (2.0x better than random baseline), eliminating manual analysis time, and scaling to serve 70+ teams simultaneously.

## Common Commands

### Development and Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies (linting, type checking)
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
pytest --cov=src tests/

# Run specific test file
python -m pytest tests/test_suite.py -v
```

### Code Quality
```bash
# Run all quality checks
make check-all

# Individual checks
make type-check    # mypy type checking
make lint          # pylint + ruff
make format        # auto-format with ruff
make check-docs    # docstring validation

# Auto-fix issues
make fix           # runs ruff --fix + format

# Clean cache files
make clean
```

### Running the Application
```bash
# Web interface (recommended)
python src/web_main.py data/raw/combined_dataset.xlsx
# Then open: http://localhost:8000

# CLI interface
python src/main.py data/raw/combined_dataset.xlsx

# Quick start scripts
./run_web.sh       # macOS/Linux
run_web.bat        # Windows
```

## Architecture and Data Flow

### High-Level Architecture
The system follows a **modular, layered architecture**:

```
Web/CLI Interface → API Layer (FastAPI) → ML Engine → Data Layer
```

**Key Design Pattern**: The system uses collaborative filtering + sequence learning to make recommendations. Data only flows from past to present (strict temporal ordering to prevent data leakage).

### Module Organization

**`src/data/`** - Data loading and processing
- [loader.py](src/data/loader.py) - Loads Excel files, identifies practice columns
- [processor.py](src/data/processor.py) - Normalizes scores (0-3 → 0-1), builds team histories indexed by month
- [validator.py](src/data/validator.py) - Validates data quality
- [practice_definitions.py](src/data/practice_definitions.py) - Loads practice level definitions

**`src/ml/`** - Machine learning engine (core algorithms)
- [recommender.py](src/ml/recommender.py) - **Main recommendation engine**. Combines similarity + sequence scores using hybrid weighted approach. This is the most important file to understand.
- [similarity.py](src/ml/similarity.py) - Calculates cosine similarity between teams, finds K most similar teams
- [sequences.py](src/ml/sequences.py) - Learns Markov chain transition matrix from historical data

**`src/validation/`** - Backtesting and optimization
- [backtest.py](src/validation/backtest.py) - Rolling window backtest validation (trains on past, tests on future)
- [optimizer.py](src/validation/optimizer.py) - Parameter optimization using grid search
- [metrics.py](src/validation/metrics.py) - Accuracy calculations, random baseline

**`src/api/`** - Web API layer (FastAPI)
- [routes.py](src/api/routes.py) - API endpoint definitions
- [service.py](src/api/service.py) - Service layer wrapping ML components
- [models.py](src/api/models.py) - Pydantic models for request/response validation

**`src/interface/`** - User interfaces
- [cli.py](src/interface/cli.py) - Interactive command-line interface
- [formatter.py](src/interface/formatter.py) - Output formatting utilities

### Critical Data Flow Pattern

**IMPORTANT**: The system must never use future data to make predictions. All algorithms follow this pattern:

1. **Data Loading**: Excel → DataFrame → Validation → Normalized team histories
2. **Recommendation Generation** (for team T at month M):
   - Find similar teams by comparing T's state at M against **all teams at months < M only**
   - Check what similar teams improved in next 1-3 months (**but only if those months ≤ M**)
   - Learn sequences from **all data with months < M only** (time-limited learning)
   - Combine signals and rank
3. **Validation**: Train on past months, test on future months, rolling window approach

## Key Algorithms

### 1. Collaborative Filtering (Similarity-Based)
- **Location**: [src/ml/similarity.py:61](src/ml/similarity.py#L61)
- **How it works**: Uses cosine similarity to find K=19 most similar teams by comparing practice maturity vectors
- **Key insight**: "Teams like you improved these practices" - learns from peer success patterns
- **Implementation note**: Compares target team at current month against all teams at **all past months** (cross-temporal matching)

### 2. Sequence Learning (Markov Chains)
- **Location**: [src/ml/sequences.py:34](src/ml/sequences.py#L34)
- **How it works**: Builds transition matrix P(B | A improved) from historical improvement patterns
- **Key insight**: "CI/CD typically leads to Test Automation" - learns natural improvement sequences
- **Implementation note**: Uses **time-limited learning** - only learns from months < current_month to prevent data leakage

### 3. Hybrid Recommendation Scoring
- **Location**: [src/ml/recommender.py:25](src/ml/recommender.py#L25) (main `recommend()` method)
- **Formula**:
  ```
  final_score = (similarity_weight × normalized_sim_score) +
                ((1 - similarity_weight) × normalized_seq_score)
  ```
- **Default weights**: 60% similarity, 40% sequence (similarity_weight = 0.6)
- **Normalization**: Scores normalized separately before combining, then final normalization to [0,1]

### 4. Backtest Validation
- **Location**: [src/validation/backtest.py:20](src/validation/backtest.py#L20)
- **How it works**: Rolling window - train on months < test_month, predict for test_month, validate against actual improvements in test_month/+1/+2
- **Key metric**: Accuracy = correct_predictions / total_predictions vs random baseline

## Important Implementation Details

### Data Leakage Prevention
**CRITICAL**: The system has strict temporal ordering to prevent future data from influencing past predictions:

- `SimilarityEngine.find_similar_teams()` only compares against months < current_month
- `SequenceMapper.learn_sequences_up_to_month()` uses sliding window approach
- `RecommendationEngine.recommend()` has `allow_first_three_months` flag to control when predictions start
- All improvement lookups check: `improvement_month <= current_month`

When modifying recommendation logic, always verify no future data leakage.

### Parameter Configuration
**Tunable parameters** (defined in [src/ml/recommender.py:25](src/ml/recommender.py#L25)):
- `top_n`: Number of recommendations to return (default: 2)
- `k_similar`: Number of similar teams to consider (default: 19)
- `similarity_weight`: Weight for similarity vs sequence (default: 0.6)
- `similar_teams_lookahead_months`: Months to check for similar team improvements (default: 3)
- `recent_improvements_months`: Months to check back for recent improvements (default: 3)
- `min_similarity_threshold`: Minimum cosine similarity to consider (default: 0.75)

These were optimized using [src/validation/optimizer.py](src/validation/optimizer.py) - typically 180+ combinations tested.

### Normalization Strategy
The system uses **three layers of normalization**:
1. **Input normalization**: Raw scores (0-3) → normalized (0-1) via division by 3.0
2. **Score normalization**: Similarity and sequence scores normalized separately before combining
3. **Final normalization**: Combined scores normalized to [0,1] for display

This ensures both similarity and sequence signals contribute proportionally.

### Excel Data Format
- **Required columns**: "Team Name" (str), "Month" (int, YYMMDD format)
- **Practice columns**: All other columns, values 0-3 (maturity levels)
- **Example**: Team "AADS" at month 200105 with CI/CD=1, TDD=0, DoD=3, etc.
- **Processing**: Loaded by [DataLoader](src/data/loader.py), normalized by [DataProcessor](src/data/processor.py)

## Code Style Guidelines

### Type Hints (Required)
All functions must have type hints for parameters and return values:
```python
def recommend(
    self,
    target_team: str,
    current_month: int,
    top_n: int = 2
) -> List[Tuple[str, float, float]]:
    """Generate recommendations."""
    pass
```

Use `typing` module for complex types: `List`, `Dict`, `Tuple`, `Optional`, etc.

### Docstrings (Google Style)
All public functions must have comprehensive docstrings:
```python
def process_data(team_name: str, month: int) -> Dict[str, float]:
    """
    Process team data for given month.

    Args:
        team_name (str): Name of the team
        month (int): Month in YYMMDD format

    Returns:
        Dict[str, float]: Processed data with practice scores

    Raises:
        ValueError: If team not found or month invalid
    """
```

See [.cursor/rules/documentation.mdc](.cursor/rules/documentation.mdc) for full guidelines.

### Naming Conventions
- Classes: `PascalCase` (e.g., `RecommendationEngine`)
- Functions/methods: `snake_case` (e.g., `find_similar_teams`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TOP_N`)
- Private methods: Prefix with `_` (e.g., `_calculate_internal_metric`)

### Code Formatting
- Line length: 120 characters max (soft limit: 100)
- Indentation: 4 spaces (never tabs)
- Import order: stdlib → third-party → local (alphabetical within groups)
- Run `make format` before committing

See [.cursor/rules/code-style.mdc](.cursor/rules/code-style.mdc) for full guidelines.

## Testing Strategy

### Test Organization
- Location: `tests/` directory
- Run with: `python -m pytest tests/ -v`
- Main test file: [tests/test_suite.py](tests/test_suite.py)

### Test Coverage Targets
Focus on testing:
- Core recommendation algorithm accuracy
- Data loading and normalization correctness
- Edge cases (unknown teams, missing data, first/last months)
- Similarity calculations
- Sequence learning

### Testing Pattern
Use the Arrange-Act-Assert pattern:
```python
def test_recommendation_generation():
    # Arrange
    team = "AADS"
    month = 200105

    # Act
    recommendations = engine.recommend(team, month, top_n=2)

    # Assert
    assert len(recommendations) == 2
    assert all(r[1] > 0 for r in recommendations)
```

See [.cursor/rules/testing.mdc](.cursor/rules/testing.mdc) for full guidelines.

## Common Development Tasks

### Adding a New Feature
1. Read relevant modules first (especially [src/ml/recommender.py](src/ml/recommender.py) for core logic)
2. Understand the data flow and temporal constraints
3. Write tests first (TDD approach recommended)
4. Add type hints and docstrings
5. Run `make check-all` before committing
6. Update documentation if API changes

### Modifying Recommendation Logic
**CRITICAL CHECKS**:
1. ✅ No data leakage - verify all data access uses `months <= current_month`
2. ✅ Normalization - ensure scores normalized properly before combining
3. ✅ Backtest validation - run backtest to verify accuracy didn't degrade
4. ✅ Parameter sensitivity - test with different parameter values

### Debugging Recommendations
1. Check what similar teams were found: look at `SimilarityEngine.find_similar_teams()` output
2. Check sequence patterns: examine `SequenceMapper.get_typical_next_practices()` results
3. Compare similarity vs sequence scores: add debug logging in `RecommendationEngine.recommend()`
4. Validate against historical data: use [src/validation/backtest.py](src/validation/backtest.py)

### Performance Optimization
Current performance:
- Recommendation generation: <1 second per team
- Backtest validation: 1-2 minutes for full dataset
- Parameter optimization: 30-60 minutes (can be cancelled)

For optimization:
- Use caching (already implemented for sequences)
- Vectorize operations with NumPy
- Profile before optimizing: `python -m cProfile -o profile.stats src/main.py`

## Important Cursor Rules

The [.cursor/rules/](.cursor/rules/) directory contains important coding standards:
- **type-hints.mdc**: Type annotation requirements (use `typing` module)
- **code-style.mdc**: PEP 8 compliance, naming conventions, line length (120 max)
- **testing.mdc**: Test file naming (`test_*.py`), pytest patterns, coverage targets
- **quality.mdc**: Error handling (specific exceptions, clear messages), logging standards
- **documentation.mdc**: Google-style docstrings with Args/Returns/Raises

These rules are enforced via `make check-all` and should be followed for all code changes.

## Documentation References

- [README.md](README.md) - Project overview, features, business value
- [QUICK_START.md](QUICK_START.md) - 3-step quick start guide
- [INSTALLATION.md](INSTALLATION.md) - Detailed installation instructions
- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) - Academic documentation, algorithm details, evaluation results
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development setup, code quality checklist

## Key Files to Understand

To understand the system, read these files in order:

1. [src/data/loader.py](src/data/loader.py) - Data loading basics
2. [src/data/processor.py](src/data/processor.py) - Data normalization and team history structure
3. [src/ml/similarity.py](src/ml/similarity.py) - Collaborative filtering
4. [src/ml/sequences.py](src/ml/sequences.py) - Sequence learning
5. [src/ml/recommender.py](src/ml/recommender.py) - **Core algorithm** (read this carefully!)
6. [src/validation/backtest.py](src/validation/backtest.py) - Validation methodology

## Troubleshooting

### Import Errors
Run from project root: `cd /Users/ErezMo/Documents/agile-prediction-mvp`

### Type Check Failures
Many existing issues - focus on new code. Run: `make type-check`

### Test Failures
Ensure data file exists: `ls data/raw/combined_dataset.xlsx`

### Recommendation Issues
- Check data exists for team/month
- Verify at least 2 months of history
- Run backtest to validate: `python -m pytest tests/test_suite.py::TestRecommendationEngine -v`

## Project Context

- **Development**: Built with Claude Code (AI pair programming)
- **Purpose**: Academic project (Open University, Israel) + Real-world deployment readiness
- **Status**: Production-ready MVP, validated on historical data
- **Future**: Ready for pilot testing with selected teams

---

**Remember**: This is a machine learning system that learns from organizational history to guide agile transformation. The core insight is: "What did successful peers do next?" - not generic best practices, but patterns from this specific organization's data.
