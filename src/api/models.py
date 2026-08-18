"""
Pydantic models for API request/response validation.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    """Request model for getting recommendations.

    top_n is pinned to 2 (the primary flow always returns exactly two recommendations -
    see docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_REQUIREMENTS-refined.md). A request for
    any other value fails Pydantic validation rather than silently receiving a different
    policy. There is no k_similar - peer count is chosen by the month's selected policy,
    not by the caller.
    """

    model_config = ConfigDict(extra="forbid")

    team: str = Field(..., description="Team name")
    month: int = Field(
        ...,
        description="Prediction month in the project's YYMMDD-style integer encoding; must be the fourth recorded global month or later",
    )
    top_n: Literal[2] = Field(2, description="Number of recommendations - must be exactly 2")


class SelectedPolicyInfo(BaseModel):
    """Audit record for the global policy selected for one prediction month."""

    is_bootstrap: bool
    peer_count: int | None = Field(None, description="None (not a default) when the bootstrap policy is in effect")
    min_similarity: float | None = Field(None, description="None (not a default) when the bootstrap policy is in effect")
    similarity_weight: float
    sequence_weight: float
    popularity_weight: float
    popularity_recency_weight: float
    completed_prior_months: list[int]
    mean_prior_hit_rate: float | None = None


class PerMonthResult(BaseModel):
    """Results for a single prediction month in the backtest."""

    month: int
    full_outcome_window: bool
    evaluable_cases: int
    predictions: int
    correct: int
    accuracy: float
    time_aware_popularity_accuracy: float
    blend_minus_popularity: float
    precision: float
    recall: float
    mrr: float
    teams_tested: int
    selected_policy: SelectedPolicyInfo
    popularity_arm_recency_weight: float


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
    team_improved_anything: bool = False


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
    improved_in_months: list[int] | None = None


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
    selected_policy: SelectedPolicyInfo
    no_similar_teams_found: bool = False
    message: str | None = Field(
        None, description="Set when fewer than two recommendations can be returned, e.g. the team has fewer than two practices left to improve"
    )


class BacktestScopeResult(BaseModel):
    """Aggregate backtest metrics over one scope (primary or sensitivity). Rate fields
    are None (not 0.0) when zero months qualify for this scope."""

    months_included: int
    total_predictions: int
    correct_predictions: int
    overall_accuracy: float | None
    random_baseline: float | None
    improvement_gap: float | None
    improvement_factor: float | None
    time_aware_popularity_accuracy: float | None
    blend_minus_popularity: float | None
    overall_precision: float | None
    overall_recall: float | None
    overall_mrr: float | None
    random_precision: float | None
    random_recall: float | None
    random_mrr: float | None
    precision_gap: float | None
    recall_gap: float | None
    mrr_gap: float | None
    precision_improvement_factor: float | None
    recall_improvement_factor: float | None
    mrr_improvement_factor: float | None
    teams_tested: int
    avg_improvements_per_case: float | None


class BacktestResponse(BaseModel):
    """Response model for backtest results.

    Primary aggregate reporting covers only prediction months with a complete
    three-snapshot outcome window; sensitivity covers every prediction month and must
    be labelled/kept separate, never mixed into the primary figures.
    """

    per_month_results: list[PerMonthResult]
    primary: BacktestScopeResult
    sensitivity: BacktestScopeResult


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
