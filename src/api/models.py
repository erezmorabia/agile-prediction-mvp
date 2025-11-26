"""
Pydantic models for API request/response validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Request model for getting recommendations."""

    team: str = Field(..., description="Team name")
    month: int = Field(..., description="Month to predict (yyyymmdd format) - must be month 3 or later")
    top_n: int = Field(2, ge=1, le=10, description="Number of recommendations")
    k_similar: int = Field(19, ge=1, le=20, description="Number of similar teams to consider")


class BacktestConfig(BaseModel):
    """Configuration for fine-tuning backtest parameters."""

    top_n: int = Field(2, ge=1, le=10, description="Number of recommendations")
    k_similar: int = Field(19, ge=1, le=20, description="Number of similar teams to consider")
    similarity_weight: float = Field(0.6, ge=0.0, le=1.0, description="Weight for similarity scores (0.0-1.0)")
    similar_teams_lookahead_months: int = Field(
        3, ge=1, le=6, description="Months to look ahead for similar teams' improvements"
    )
    recent_improvements_months: int = Field(3, ge=1, le=6, description="Months to check back for recent improvements")
    min_similarity_threshold: float = Field(
        0.75, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0 = no filter)"
    )


class BacktestRequest(BaseModel):
    """Request model for running backtest."""

    train_ratio: float | None = Field(
        None, ge=0.1, le=0.9, description="Training data ratio (ignored, kept for compatibility)"
    )
    config: BacktestConfig | None = Field(None, description="Optional configuration for fine-tuning parameters")


class PerMonthResult(BaseModel):
    """Results for a single month in rolling window backtest."""

    month: int
    train_months: list[int]
    predictions: int
    correct: int
    accuracy: float
    teams_tested: int


class TeamInfo(BaseModel):
    """Team information model."""

    name: str
    num_months: int
    months: list[int]
    first_month: int | None
    last_month: int | None


class ImprovementInfo(BaseModel):
    """Information about a team/month with improvements."""

    team: str
    month: int
    next_month: int
    num_improvements: int
    improvements: list[str]


class PracticeImprovement(BaseModel):
    """Information about a practice improvement."""

    practice: str
    improvement: float
    improvement_pct: float
    improved_in: list[int] | None = None  # List of months where improvement occurred


class ValidationSummary(BaseModel):
    """Validation summary for recommendations."""

    next_month: int
    month_after: int | None = None
    month_after_2: int | None = None
    actual_improvements: list[PracticeImprovement]
    validated_count: int
    total_recommendations: int
    accuracy: float | None = None  # None when no improvements occurred (not a model failure)


class SimilarTeamInfo(BaseModel):
    """Information about a similar team that improved a practice."""

    team: str
    month: int
    similarity: float
    similar_at_month: int


class RecommendationItem(BaseModel):
    """Single recommendation item."""

    practice: str
    score: float
    current_level: float
    original_level: float
    level_num: int
    level_description: str
    level_display: str
    why: str
    similar_teams: list[SimilarTeamInfo] = []
    validated: bool


class PracticeProfile(BaseModel):
    """Practice maturity profile grouped by level."""

    level_0: list[str] = Field(default_factory=list, description="Not implemented practices")
    level_1: list[str] = Field(default_factory=list, description="Basic level practices")
    level_2: list[str] = Field(default_factory=list, description="Intermediate level practices")
    level_3: list[str] = Field(default_factory=list, description="Advanced level practices")


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""

    team: str
    month: int  # Month to predict (not the baseline month)
    recommendations: list[RecommendationItem]
    validation: ValidationSummary | None = None
    practice_profile: PracticeProfile | None = None


class BacktestResponse(BaseModel):
    """Response model for backtest results (rolling window)."""

    total_predictions: int
    correct_predictions: int
    overall_accuracy: float
    random_baseline: float
    improvement_gap: float
    improvement_factor: float
    per_month_results: list[PerMonthResult]
    teams_tested: int
    avg_improvements_per_case: float


class MissingValuesDetails(BaseModel):
    """Missing values details model."""

    total_missing: int
    by_practice: dict[str, dict[str, Any]]
    by_month: dict[int, dict[str, Any]]
    practices_with_missing: list[str]
    months_with_missing: list[int]


class SystemStats(BaseModel):
    """System statistics model."""

    num_teams: int
    num_practices: int
    num_months: int
    total_observations: int
    months: list[int]
    practices: list[str]
    similarity_stats: dict[str, Any] | None = None
    missing_values: MissingValuesDetails | None = None
    practice_definitions: dict[str, dict[int, str]] | None = Field(
        None, description="Practice level definitions (practice_name -> level -> definition)"
    )
    practice_remarks: dict[str, str] | None = Field(
        None, description="Practice remarks/notes (practice_name -> remarks)"
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str | None = None


class OptimizationRequest(BaseModel):
    """Request model for finding optimal configuration."""

    min_accuracy: float = Field(0.40, ge=0.0, le=1.0, description="Minimum accuracy threshold")
    top_n_range: list[int] | None = Field(None, description="List of top_n values to test")
    similarity_weight_range: list[float] | None = Field(None, description="List of similarity_weight values to test")
    k_similar_range: list[int] | None = Field(None, description="List of k_similar values to test")
    similar_teams_lookahead_months_range: list[int] | None = Field(None, description="List of lookahead months to test")
    recent_improvements_months_range: list[int] | None = Field(None, description="List of recent months to test")
    min_similarity_threshold_range: list[float] | None = Field(
        None, description="List of min_similarity values to test"
    )
    fixed_params: dict[str, Any] | None = Field(None, description="Fixed parameter values (overrides ranges)")


class OptimizationResult(BaseModel):
    """Single optimization result."""

    config: dict[str, Any]
    model_accuracy: float
    random_baseline: float
    improvement_gap: float
    improvement_factor: float
    total_predictions: int
    correct_predictions: int


class OptimizationResponse(BaseModel):
    """Response model for optimization results."""

    optimal_config: dict[str, Any] | None = None
    model_accuracy: float
    random_baseline: float
    improvement_gap: float
    improvement_factor: float
    total_predictions: int
    correct_predictions: int
    total_combinations_tested: int
    total_combinations_available: int
    valid_combinations: int
    all_results: list[OptimizationResult] = Field(default_factory=list, description="Top 10 results")
    early_stopped: bool = False
    cancelled: bool = False
