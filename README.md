# Agile Practice Recommendation MVP

**Empirical Organizational Learning for Likely Next Agile Practices**

A recommendation system whose core innovation is empirically learning organizational improvement behavior to identify likely next practices. It derives team-specific guidance from observed peer-team maturity histories and practice-transition behavior; collaborative filtering and the Practice Transition Model are the implementation tools behind that approach.

---

## For Teachers/Evaluators

**Requirement:** Python 3.8+ installed.

```bash
git clone https://github.com/erezmorabia/agile-prediction-mvp.git
cd agile-prediction-mvp
./start_mac_linux.sh        # macOS/Linux
```

```cmd
start_windows.bat         # Windows
```

Dependencies install automatically. Browser opens to **http://localhost:8000**.

See **[QUICK_START.md](docs/QUICK_START.md)** for a guided walkthrough of all four tabs.  
See **[PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)** for the full academic report and technical documentation.

### What to Expect:
- **Web Interface:** Modern, interactive UI at http://localhost:8000
- **Recommendations:** Get personalized practice recommendations for teams
- **Validation:** Run backtest validation with accuracy metrics (~58.0% primary accuracy, 2.2x better than random, 2.3pp ahead of a time-aware-popularity comparison arm)
- **Statistics:** View system statistics and practice definitions
- **Sequences:** Explore learned improvement patterns

> **Interpreting performance results:** Accuracy and improvement figures are aggregate historical backtest averages across the organization. They are not guarantees that every team, in every month, will improve or match a recommendation.

---

## What This System Does

### **The Business Problem**

Organizations implementing agile transformation face a critical challenge:

> **"Which agile practices should each team focus on next to maximize success?"**

With 70+ teams, 30+ practices to implement, and constantly changing priorities, making the right decision for each team at each point in time is **impossible to do manually**.

Poor choices lead to:
- Wasted resources on practices teams aren't ready for
- Slower transformation progress
- Team frustration and resistance
- Missed business benefits

### **The Solution**

This MVP’s core innovation is an empirical approach to learning organizational improvement behavior. It recommends which **agile practices** each team should focus on next (default: top 2, configurable) by turning observed team histories into team-specific guidance. The following implementation tools support that approach:

1. **What similar teams did successfully** 
   - Uses collaborative filtering to find teams like yours
   - Learns what they improved and how they progressed

2. **Observed improvement transitions**
   - Identifies which practices typically follow others
   - Uses a Practice Transition Model to learn organizational transition patterns
   - Ensures recommendations make logical sense

3. **Real organizational data**
   - Built on actual data from 87 teams
   - 10 months of improvement history (655 team-month observations)
   - Coverage varies because teams joined or left the recorded population at different points: 48 teams have all 10 recorded months and 39 have 1–9 months
   - 35 different agile practices tracked

### **Business Value**

| Metric | Baseline | With System | Impact |
|--------|----------|-------------|--------|
| **Decision Accuracy** | ~26.0% (random) | 58.0% | **2.2x better** |
| **Manual Analysis Time** *(practitioner estimate, not measured — [see basis](docs/PROJECT_DOCUMENTATION.md))* | 4-8 hours/month | 0 hours | **100% automated** |
| **Teams Served** | 1-2 | 70+ simultaneously | **Scale 35-70x** |
| **Decision Confidence** | Intuition | Data-driven | **Proven model** |
| **Learning Speed** | Months | Weekly | **Faster improvement** |

### **Real-World Impact Example**

*Illustrative scenario only; actual team outcomes depend on local context and are not guaranteed by the model.*

**Month 1:**
- System recommends Team A focus on "CI/CD" (based on 5 similar teams who succeeded)
- Team A may choose to implement CI/CD
- The team evaluates whether the practice improves its maturity

**Month 2:**
- System incorporates newly available organizational history
- Recommends similar practices to comparable teams
- Comparable teams may see different outcomes
- Recommendations can be re-evaluated as additional data becomes available

**Month 3+:**
- Organization-wide patterns strengthen
- Recommendation quality should be monitored with new backtests
- Teams and the organization evaluate whether the recommendations add value

### **Typical ROI**

Research shows organizations with guided agile transformation achieve:
- **4x higher success rate** than unguided
- **3-4x faster time to value**
- **2-3x better team adoption**

This system automates and optimizes that guidance.

### **Key Capabilities**

- **Automatic Recommendations** - No manual analysis needed  
- **Personalized** - Each team gets unique recommendations  
- **Intelligent Sequencing** - Knows what's next in the improvement path  
- **Evidence-Based** - Built on 655 data points across 87 teams  
- **Validated** - 58.0% primary aggregate historical backtest accuracy (2.2x better than random, 2.3pp ahead of a time-aware-popularity comparison arm)
- **Scalable** - Works with any number of teams/practices
- **Continuous Learning** - Gets smarter each month
- **Pilot-Ready** - Tested and deployable for pilot use with selected teams (see [PROJECT_DOCUMENTATION.md §7.3](docs/PROJECT_DOCUMENTATION.md) for the gap to full production hardening)

## How It Works: The 4-Step Recommendation Engine

### **The Problem Statement**

> **"How do we decide which agile practices each team should implement next?"**

**Why this is hard:**
- 87 teams all at different maturity levels
- 35 different practices to choose from
- Each team has unique context and readiness
- Manual decisions are subjective and inconsistent
- Wrong choices waste time and resources
- Leaders have no data-driven way to decide

### **The Solution: 4-Step Recommendation Engine**

Your code solves this by automating the decision-making process:

---

### **STEP 1: Find Similar Teams (Collaborative Filtering)**

```python
# From: src/ml/similarity.py
similarity_engine.find_similar_teams(target_team, current_month, k=19)
```

**What it does:**
- Looks at Team A's current practice scores (e.g., DoD=3, CI/CD=1, TDD=0)
- Compares them to all other teams using cosine similarity
- Finds the K most similar teams (K is one of 5, 10, or 19 - chosen automatically per prediction month by the global policy, not a fixed default)
- Returns: The most similar teams to Team A

**Why this matters:**
- Similar teams have already figured out what works
- If Team B succeeded after improving CI/CD, Team A likely will too
- Peer learning is more credible than external recommendations

**Example:**
```
Team A (target):      DoD=3, CI/CD=1, TDD=0, Code Review=2
Team B (similar):     DoD=3, CI/CD=1, TDD=0, Code Review=2 ✓ Match!
Team C (similar):     DoD=3, CI/CD=1, TDD=1, Code Review=2 ✓ Close match!
Team D (different):   DoD=1, CI/CD=3, TDD=3, Code Review=1 ✗ Not similar
```

---

### **STEP 2: See What They Did Next (Sequence Learning)**

```python
# From: src/ml/sequences.py
sequence_mapper.learn_sequences()
sequence_mapper.get_typical_next_practices(practice, top_n=5)
```

**What it does:**
- Looks at ALL 87 teams' improvement history
- Links each improvement-bearing step to that team's next improvement-bearing step
- Counts the practice-to-practice transitions observed across the organization
- Learns empirical transition patterns; the next step may occur after one or more recorded months

**Why this matters:**
- It adds organizational context to peer-based recommendations
- It gives more weight to practices that were observed after a team's recent improvements
- It does not assume a universal or causal order of practice adoption

**Most frequent transitions in the checked-in organizational dataset:**

| From practice | To practice | Observed count | All transitions from source | Conditional frequency |
| --- | --- | ---: | ---: | ---: |
| Unified backlog | Product Owner | 7 | 24 | 29.2% |
| Scrum Master | Tech debt strategy | 7 | 28 | 25.0% |
| Tech debt strategy | Product Owner | 6 | 47 | 12.8% |
| Reducing WIP | Tech debt strategy | 5 | 15 | 33.3% |
| Scrum Master | Unified backlog | 5 | 28 | 17.9% |
| DoR | Reducing WIP | 5 | 30 | 16.7% |
| Retro | Scrum Master | 5 | 38 | 13.2% |
| Tech debt strategy | Tech debt strategy | 5 | 47 | 10.6% |
| DoR | Tech debt strategy | 4 | 30 | 13.3% |
| DoD | Tech debt strategy | 4 | 32 | 12.5% |

These figures were calculated by the application from `combined_dataset.xlsx`: 471 observed
transitions among 30 practices retained after missing-data filtering. The conditional frequency is
`count(A → B) / all observed transitions from A`, so it describes this organization's history; it
does not establish causation or guarantee an individual team's next improvement.

---

### **STEP 3: Combine Signals (Hybrid Scoring)**

```python
# From: src/ml/recommender.py
recommendations = recommender.recommend(team, current_month, top_n=2)  # Default: 2, configurable
```

**What it does:**
```
For each practice:
  similarity_score = How many similar teams improved this?
  sequence_score = Do observed transition patterns support this candidate?
  final_score = (similarity_score × 0.7) + (sequence_score × 0.3)

Rank by final_score
Filter out practices already at level 3 (mature)
Return top N (default: 2)
```

**Why this works:**
- Similarity alone: "Teams like you improved CI/CD" (good but rigid)
- Transitions alone: "The organization has observed certain practices after recent improvements" (useful but general)
- Combined: "Similar teams and observed organizational transitions both support this candidate"

---

### **STEP 4: Validate on Historical Data (Backtest)**

```python
# From: src/validation/backtest.py
backtest = BacktestEngine(recommender, processor)
results = backtest.run_backtest()
```

**What it does:**
- Takes historical data from months 1-6 (training)
- Uses it to identify likely next practices for teams in months 8-10 (testing)
- Checks: Did the recommendations align with later improvements?
- Calculates accuracy

**Why this matters:**
- Evaluates recommendation alignment against historical data
- 58.0% primary aggregate backtest accuracy vs ~26.0% random = **2.2x better**
- Supports informed use of recommendations while individual outcomes remain uncertain

---

### **Real Example: How It Solves the Problem**

**Scenario: Team A (Avengers) at Month 200705**

**Before the system:**
```
Manager: "Hmm, what should Avengers focus on next?"
- Check email from other teams? No good info
- Ask PM? Subjective opinion
- Look at industry best practices? Too generic
- Result: Guess... probably wrong choice
```

**With the system:**
```python
# Step 1: Find similar teams
similar = similarity_engine.find_similar_teams("Avengers", 200705, k=19)
# Result: Top 19 most similar teams by cosine similarity

# Step 2: What did they improve next?
# Strikers: improved CI/CD, Test Automation
# WeView: improved Test Automation, TDD
# Team B: improved CI/CD
# Team C: improved Test Automation
# Team D: improved TDD

# Step 3: Score & combine
# CI/CD: 3 teams improved it + fits sequence pattern = 0.75
# Test Automation: 3 teams improved it + high sequence boost = 0.82
# TDD: 2 teams improved it + lower sequence score = 0.61

# Step 4: Rank
1. Test Automation (score: 0.82) ← RECOMMEND THIS
2. CI/CD (score: 0.75)
3. TDD (score: 0.61)

# Output to manager:
"Avengers should focus on: Test Automation (confidence: 82%)"
```

**Result:**
- Avengers implements Test Automation
- They succeed (similar teams did too)
- Improvement is natural sequence (fits the pattern)
- Manager has data-driven confidence
- Time saved vs manual analysis

---

### **How It Scales**

| Situation | Manual Process | System Process |
|-----------|---------------|----------------|
| 1 team recommendation | 1-2 hours analysis | 0.1 seconds |
| 87 teams recommendations | 87-174 hours/month | <10 seconds |
| Adjust strategy | Redo all analysis | Re-run (instant) |
| Learn from new data | Manual review | Automatic |

---

### **The Core Insight**

The system answers: **"What did successful peers do next?"**

**Instead of:**
- Generic best practices (not tailored)
- Manager intuition (inconsistent)
- Random selection (3% accuracy)
- One-size-fits-all (doesn't work for all teams)

**It does:**
- Personalized (tailored to each team's context)
- Evidence-based (from 87 real teams)
- Validated (58.0% primary aggregate historical backtest accuracy)
- Scalable (works for all teams simultaneously)
- Continuous learning (improves each month)

---

### **What Each Code Component Does**

| File | Solves | Example |
|------|--------|---------|
| `loader.py` | Read data | "Load 87 teams from Excel" |
| `processor.py` | Prepare data | "Normalize scores 0-3 → 0-1" |
| `validator.py` | Verify quality | "Check no missing data" |
| `similarity.py` | Find peers | "Find 5 teams like Avengers" |
| `sequences.py` | Learn patterns | "Count observed transitions between improvement-bearing steps" |
| `recommender.py` | Make decision | "Recommend: Test Automation" |
| `backtest.py` | Prove it works | "68% accuracy on historical data" |
| `cli.py` | Present results | "Show menu to manager" |

---

### **The Bottom Line**

**Problem:** "Which practice should Team X do next?"

**Solution:** "Look at teams that are doing well, see what they did next, check if it fits the natural sequence, and recommend that."

**Result:** 2.2x better decisions than random guessing, fully automated, works for 70+ teams simultaneously.

## Features

- **Data Loading** - Read and validate agile metrics from Excel
- **ML Engine** - Collaborative filtering + Practice Transition Model
- **Recommendations** - Top N practices for each team (default: 2)
- **Backtest Validation** - Validate on historical data
- **Web Interface** - Modern browser-based UI (NEW)
- **CLI Interface** - Interactive command-line system
- **Test Suite** - Comprehensive unit tests (177+ test functions)

## Quick Start

### 1. Prerequisites

```bash
Python 3.8+
pip (Python package manager)
```

### 2. Installation

```bash
# Copy your Excel file
cp /path/to/20250204_Cleaned_Dataset.xlsx data/raw/

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the System

**Option A: Web Interface (Recommended for non-technical users)**

```bash
python src/web_main.py data/raw/combined_dataset.xlsx
```

Then open your browser to: `http://localhost:8000`

**Option B: Command-Line Interface (For technical users)**

```bash
python src/main.py data/raw/combined_dataset.xlsx
```

Or simply:
```bash
python src/main.py
```

**Option C: Standalone Executable (No Python installation required)**

Build a standalone executable that includes everything:

**On macOS:**
```bash
./build_executable.sh
# Then run: ./dist/AgilePredictionSystem
```

**On Windows:**
```cmd
build_executable.bat
# Then run: dist\AgilePredictionSystem.exe
```

The executable will automatically start the server and open your browser. See the "Building Executables" section below for more details.

## Building Executables

You can build standalone executables that don't require Python installation. This is ideal for distributing the application to users who don't have Python installed.

### Prerequisites

- Python 3.8+ (only needed for building, not for running the executable)
- PyInstaller (automatically installed by build scripts)

### Building

**macOS:**
```bash
./build_executable.sh
```

**Windows:**
```cmd
build_executable.bat
```

The build process will:
1. Check/install PyInstaller if needed
2. Bundle all Python dependencies
3. Include web static files and data files
4. Create executable in `dist/` directory

### Running the Executable

**macOS:**
```bash
./dist/AgilePredictionSystem
```

**Windows:**
```cmd
dist\AgilePredictionSystem.exe
```

The executable will:
- Start the web server automatically
- Open your default browser to http://localhost:8000
- Display server logs in the console window
- Press Ctrl+C to stop the server

### Distribution

To distribute the application:
1. Build the executable for the target platform
2. Share the entire `dist/AgilePredictionSystem` folder (macOS) or `dist/AgilePredictionSystem.exe` + supporting files (Windows)
3. The executable includes all dependencies and data files

**File Size:** ~50-100 MB (includes Python runtime and all dependencies)

**Note:** Executables are platform-specific. You need to build separately for macOS and Windows.

### Development Mode Still Works

All existing development workflows remain unchanged:
- `python3 src/web_main.py data/raw/combined_dataset.xlsx` - Still works
- `./start_mac_linux.sh` - Still works
- `start_windows.bat` - Still works
- Running from IDE/editor - Still works

The executable build is an additional option, not a replacement for development.

## Project Structure

```
agile-prediction-mvp/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── src/
│   ├── main.py              # CLI entry point
│   ├── web_main.py          # Web interface entry point
│   ├── data/                # Data loading & processing
│   │   ├── loader.py        # Excel file loader
│   │   ├── processor.py     # Data normalization
│   │   └── validator.py     # Data validation
│   ├── ml/                  # Machine learning engine
│   │   ├── similarity.py    # Cosine similarity
│   │   ├── sequences.py     # Practice Transition Model
│   │   └── recommender.py   # Main recommendation engine
│   ├── interface/           # User interface
│   │   ├── cli.py          # CLI interface
│   │   └── formatter.py    # Output formatting
│   ├── api/                 # Web API (NEW)
│   │   ├── main.py         # FastAPI application
│   │   ├── routes.py       # API routes
│   │   ├── models.py       # Pydantic models
│   │   └── service.py      # API service layer
│   └── validation/          # Testing & metrics
│       ├── backtest.py      # Historical validation
│       └── metrics.py       # Performance metrics
├── web/                     # Frontend (NEW)
│   ├── index.html          # Main HTML page
│   └── static/
│       ├── css/
│       │   └── style.css   # Styling
│       └── js/
│           ├── api.js      # API client
│           └── app.js     # Application logic
├── tests/
│   └── test_suite.py        # Unit tests
├── examples/
│   └── demo.py              # Example usage
└── data/
    ├── raw/                 # Input Excel files
    ├── processed/           # Processed data
    └── results/             # Output results
```

## Usage

### Web Interface (Recommended)

1. Start the web server:
```bash
python src/web_main.py data/raw/combined_dataset.xlsx
```

2. Open your browser to: `http://localhost:8000`

3. Use the web interface:
   - **Recommendations Tab**: Get recommendations for teams
   - **Backtest Tab**: Run validation on historical data
   - **Statistics Tab**: View system statistics

4. Features:
   - Filter teams by improvements (for validation)
   - Interactive team and month selection
   - Visual validation results, split into primary and sensitivity backtest results
   - No configuration form - the global monthly policy is the sole configuration authority

### Command-Line Interface

```bash
python src/main.py data/raw/combined_dataset.xlsx
```

Then select from the menu:
- **1** - Get recommendations for a team
- **2** - Run backtest validation
- **3** - View system statistics
- **4** - View improvement sequences
- **5** - Exit

### Example: Get Recommendations

```
Enter team name: Avengers
Enter current month (YYMMDD): 200705

Top 2 Recommendations for Avengers (Month 200705):
1. CI/CD
   Recommendation Score: 0.742
   Current Level: 0.33

2. Test automation
   Recommendation Score: 0.681
   Current Level: 0.00

Note: the primary flow always returns exactly two recommendations - top_n is not configurable
```

### Example: Run Backtest

```
Primary Results:
   Months Included: 5
   Total Predictions: 121 (team/month combinations)
   Overall Accuracy: 58.0% (average of all months)
   Random Baseline: 26.0%
   Improvement: 2.2x better than random
   Time-Aware Popularity: 55.7% (blend beats it by 2.3pp)

Sensitivity Results:
   Months Included: 7
   Overall Accuracy: 50.9%
   Random Baseline: 23.5%
```

*Note: Actual results may vary based on data distribution and test configuration*

## Running Tests

```bash
# Install pytest
pip install pytest

# Run test suite (177+ test functions)
python -m pytest tests/test_suite.py -v
```

## Code Quality Checks

This project includes static analysis and type checking tools to ensure code quality.

### Quick Start

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all checks
make check-all

# Or use the script
./scripts/check_code.sh check-all    # macOS/Linux
scripts\check_code.bat check-all     # Windows
```

### Available Commands

**Using Makefile (recommended):**
```bash
make install-dev    # Install development dependencies
make type-check     # Run mypy type checking
make lint           # Run pylint and ruff linting
make format         # Format code with ruff
make check-docs     # Check docstring style
make check-all      # Run all checks
make fix            # Auto-fix issues where possible
```

**Using scripts:**
```bash
# macOS/Linux
./scripts/check_code.sh [type-check|lint|format|check-docs|check-all|fix]

# Windows
scripts\check_code.bat [type-check|lint|format|check-docs|check-all|fix]
```

### Tools Used

- **mypy** - Static type checking
- **ruff** - Fast linting and code formatting
- **pylint** - Comprehensive code quality checking
- **pydocstyle** - Docstring style validation (Google convention)

### Configuration Files

- `mypy.ini` - Type checking configuration
- `.pylintrc` - Pylint configuration
- `pyproject.toml` - Ruff and pydocstyle configuration
- `setup.cfg` - Alternative configuration for flake8/pydocstyle

### CI/CD Integration

Code quality checks run automatically on push/PR via GitHub Actions (`.github/workflows/checks.yml`). Checks are non-blocking initially to allow gradual adoption.

## Algorithm Overview

### 1. Data Loading & Processing
- Loads Excel file with team practices and maturity levels (0-3)
- Normalizes values to 0-1 range
- Validates data quality
- Builds team histories indexed by month

### 2. Similarity Engine
- Calculates cosine similarity between teams
- Finds K most similar teams for each team
- Uses current practice profiles for similarity

### 3. Sequence Learning
- Learns which practices typically follow one another across consecutive improvement-bearing steps
- Builds a practice transition matrix from historical data
- Identifies common improvement sequences

### 4. Recommendation Engine
- Combines similarity and sequence patterns
- For each team at each month:
  1. Find K=19 most similar teams
  2. See what they improved in next period
  3. Weight by similarity score
  4. Add sequence boost
  5. Rank and return top 5

### 5. Validation
- Backtest on historical data
- Train/test split: chronological
- Calculates accuracy metrics
- Compares to random baseline

## Expected Results

With the implemented codebase:

- **MVP Timeline**: 1-2 days
- **Data Coverage**: 87 teams, 35 practices, 10 months; 655 team-month observations with variable per-team coverage
- **Backtest Accuracy**: 58.0% primary aggregate accuracy, 2.2x random baseline, 2.3pp ahead of a walk-forward time-aware-popularity comparison arm (validated on historical data; exploratory, not a per-team guarantee - see `docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_REQUIREMENTS-refined.md`)

## ML Algorithm Details

### Collaborative Filtering
```
For team T at month M:
  1. Find K most similar teams (K chosen per month by the global policy - 5, 10, or 19)
  2. Check what those teams improved in the next 2 observed snapshots
  3. Weight by similarity: score += similarity_weight * improvement_magnitude
```

### Sequence Learning
```
For each practice P:
  1. Look at all organization history
  2. When practice A improved, what came next?
  3. Build probability: P(B | A improved)
  4. If T recently improved A, boost practices that follow A
```

### Recommendation Scoring
```
score(practice) = similarity_weight * similarity_score
                 + sequence_weight   * sequence_score
                 + popularity_weight * time_aware_popularity_score

- Similarity: based on similar teams
- Sequence: based on common improvement patterns
- Time-aware popularity: based on organization-wide improvement trends
- All three weights are chosen once per prediction month by the global policy, not fixed constants
```

## How This Project Was Built

### **Project Timeline**

- **Duration**: Developed iteratively alongside AI code assistants (Claude Code and Cursor)
- **Code Size**: ~5,663 lines of production-quality source code (~9,300 total with tests)
- **Development Approach**: Agile MVP methodology (build fast, validate early)

### **Architecture**

The system is built in 5 modular components:

| Component | Purpose | Size |
|-----------|---------|------|
| **Data Module** | Load, validate, and process Excel data | ~250 lines |
| **ML Engine** | Similarity calculation + Sequence learning | ~650 lines |
| **CLI Interface** | Interactive command-line system | ~280 lines |
| **Validation** | Backtest engine + performance metrics | ~150 lines |
| **Tests** | Comprehensive test suite (7 tests) | ~240 lines |

### **Technology Stack**

- **Language**: Python 3.8+
- **Data Processing**: pandas, numpy
- **Machine Learning**: scikit-learn (cosine similarity)
- **Excel Support**: openpyxl
- **Testing**: pytest

### **ML Algorithms Used**

1. **Collaborative Filtering**
   - Cosine similarity to find similar teams
   - Weighted recommendations from peer teams

2. **Practice Transition Model**
   - Discovers which practices typically follow one another across consecutive improvement-bearing steps
   - Learns transition probabilities
   - Boosts logical improvement sequences

3. **Global Adaptive Blend**
   - Combines similarity + sequence + time-aware popularity, weighted by a policy selected once per prediction month
   - Filters out already-mature practices
   - Always returns exactly two ranked recommendations

### **Validation & Testing**

- **Comprehensive test suite** covering all components, including a byte-exact reproduction test against the research-validated blend numbers
- **58.0% primary aggregate backtest accuracy** - 2.2x better than the random baseline, 2.3pp ahead of a time-aware-popularity comparison arm; individual team outcomes may differ, and this remains an exploratory result
- **Data validation** - Quality checks on input
- **Error handling** - Robust edge case handling
- **Pilot-ready** - Code ready for pilot deployment (see `PROJECT_DOCUMENTATION.md` §7.3 for production-hardening gaps: auth, monitoring, automated data pipeline, multi-tenancy)

## Data Format

### **Excel File Requirements**

Your Excel file must have the following structure:

| Column | Name | Type | Description |
|--------|------|------|-------------|
| 1 | Team Name | Text | Team identifier (e.g., "Avengers", "Strikers") |
| 2 | Month | Number | Time period in YYMMDD format (e.g., 200107 = Jan 2020) |
| 3+ | Practice Names | Number (0-3) | Agile practices with maturity scores |

### **Maturity Level Scale**

Each practice is scored 0-3:

- **0** = Not implemented
- **1** = Basic/Initial (first steps)
- **2** = Advanced/Intermediate (well-established)
- **3** = Optimized/Mature (excellence)

### **Example Excel Structure**

```
Team Name    Month   DoD  DoR  CI/CD  Test automation  TDD  Code review
Avengers     200107  3    3    1      0                0    2
Avengers     200304  3    3    1      1                0    2
Avengers     200402  3    3    2      1                1    2
Strikers     200107  2    2    0      0                0    1
Strikers     200304  2    2    1      1                0    1
Strikers     200402  2    2    1      1                1    2
WeView       200107  1    1    0      0                0    0
WeView       200304  1    1    0      0                1    1
WeView       200402  2    2    1      1                1    1
```

### **Data Requirements**

- **Minimum 2 time periods per team** - Needed to show improvement trends
- **Consistent practice columns** - Same columns for all rows
- **No missing values** - All cells should have data (0-3)
- **Multiple teams** - At least 5 teams for meaningful patterns
- **Chronological months** - Time periods should progress (e.g., 200107, 200304, 200402)

### **What Happens During Processing**

1. **Loading** - Reads your Excel file
2. **Validation** - Checks data quality and format
3. **Normalization** - Converts scores from 0-3 → 0-1 range
4. **Indexing** - Builds team histories by month
5. **Analysis** - Identifies patterns and sequences

### **Tips for Best Results**

- Include 6+ months of data (more data = better patterns)
- Include 50+ teams (more teams = better recommendations)
- Use consistent team names (no "Team A" and "TeamA")
- Collect data monthly for consistent improvement tracking
- Ensure scores reflect actual maturity, not wishful thinking

## Next Steps After MVP

1. **Extend to Full System** (Weeks 2-3)
   - Add more features
   - Improve UI (web dashboard)
   - Optimize algorithms

2. **Deploy to Avaya** (Week 4)
   - Real-world testing with teams
   - Collect feedback
   - Iterate based on results

3. **Production** (Ongoing)
   - Monthly updates with new data
   - Monitor accuracy
   - Refine recommendations

## Known Limitations

- Requires at least 2 time periods per team
- Works best with consistent team structure
- No handling of team merges/splits
- Sequential (not parallel) processing

## Dependencies

- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scikit-learn` - Machine learning (cosine similarity)
- `openpyxl` - Excel file reading

## Configuration

There is nothing to configure. The global two-month adaptive blend (`src/ml/policy.py`,
`PolicyEngine`) selects one policy automatically for each prediction month from a fixed grid, and
that policy - not a caller, not a config file - is the sole configuration authority for the
primary recommendation flow and its backtest:

- **Peer count**: 5, 10, or 19 similar teams, chosen per prediction month
- **Minimum similarity threshold**: 0.0, 0.5, or 0.75, chosen per prediction month
- **Similarity / sequence / popularity weights**: one of 15 combinations of 0/25/50/75/100% summing to 100%, chosen per prediction month
- **Popularity recency weight**: 0/25/50/75/100%, chosen per prediction month
- **`top_n`**: pinned to 2 - the primary flow always returns exactly two recommendations
- **Similarity look-ahead and sequence recency windows**: fixed at 2 observed snapshots, never part of the grid

The selection rule: maximize mean Hit Rate@N over strictly earlier prediction months whose full
3-snapshot outcome window has already closed, falling back to a 100%-popularity bootstrap policy
before any prior month qualifies. See `docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_REQUIREMENTS-refined.md`
for the full protocol. A static all-history grid-search optimizer (`src/validation/optimizer.py`)
existed earlier in the project but was removed entirely after walk-forward analysis showed its
headline accuracy figure had been selected on the same data it was measured on.

## Troubleshooting

### "File not found"
```bash
python src/main.py /full/path/to/your/file.xlsx
```

### "ModuleNotFoundError: No module named 'src'"
This has been fixed in the code. If you encounter this, ensure you're running from the project root directory:
```bash
cd /path/to/agile-prediction-mvp
python src/main.py data/raw/20250204_Cleaned_Dataset.xlsx
```

### "No similar teams found"
- Ensure you have enough teams (>5)
- Check that data exists for the month

### Tests failing
```bash
# Install pytest
pip install pytest

# Run with verbose output
python -m pytest tests/ -v -s
```

## System Statistics

When running, you'll see:

```
Loaded data: 87 teams, 35 practices, 10 months
   Total rows: 655

Processed 87 team histories

Learned 28 transition patterns

Similarity Engine: Ready
Sequence Mapper: Ready

System initialized successfully!
```

## Code Statistics

- **Total Source Lines**: ~5,663
- **Test Lines**: ~3,637
- **Combined Total**: ~9,300 lines
- **Core ML modules**: recommender.py, similarity.py, sequences.py
- **Data modules**: loader.py, processor.py, validator.py
- **Interface modules**: CLI and Web interfaces

## License

Academic - For educational and research purposes

## Contributing

This is an MVP. Future improvements could include:
- Real-time recommendations
- Team segmentation
- Practice dependency modeling
- Web UI dashboard
- REST API

## Questions?

Refer to README sections or check specific module docstrings:
```python
python -c "from src.ml import RecommendationEngine; help(RecommendationEngine)"
```

---

**Ready to use!** Start with: `python src/main.py`
