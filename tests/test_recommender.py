"""
Extended tests for RecommendationEngine class.

RecommendationEngine is now a thin wrapper delegating to PolicyEngine (src/ml/policy.py):
recommend(team, prediction_month) takes no tuning parameters - the month's globally
selected policy is the only configuration authority. See tests/test_policy.py and
tests/test_blend_reproduction.py for PolicyEngine's own unit and reproduction tests;
these tests only check that the wrapper delegates correctly.
"""

import pytest
from src.ml.recommender import RecommendationEngine


class TestRecommendationEngineExtended:
    """Extended tests for RecommendationEngine functionality."""

    def _first_predictable(self, recommender, sample_processor):
        """Find a (team, prediction_month) pair valid under the new contract, or skip."""
        engine = recommender.policy_engine
        for month in engine.prediction_months():
            for team in sample_processor.get_all_teams():
                if engine.baseline_month_for(team, month) is not None:
                    return team, month
        pytest.skip("Sample fixture has no valid prediction month (needs >= 4 total months)")

    def test_recommend_basic(self, sample_recommender, sample_processor):
        """Test recommend returns a RecommendationResult with 0 or 2 practices."""
        team, month = self._first_predictable(sample_recommender, sample_processor)
        result = sample_recommender.recommend(team, month)

        assert result.team == team
        assert result.prediction_month == month
        assert isinstance(result.practices, tuple)
        assert len(result.practices) in (0, 2)

        for practice in result.practices:
            assert isinstance(practice, str)
            score = result.scores[practice]
            level = result.current_levels[practice]
            assert 0.0 <= score <= 1.0
            assert 0.0 <= level <= 1.0

    def test_recommend_always_returns_at_most_two(self, sample_recommender, sample_processor):
        """The primary flow always returns exactly two recommendations, or zero when the
        team has fewer than two non-maxed candidate practices - never a tunable count."""
        team, month = self._first_predictable(sample_recommender, sample_processor)
        result = sample_recommender.recommend(team, month)

        assert len(result.practices) == 0 or len(result.practices) == 2
        assert result.insufficient_practices == (len(result.practices) == 0)

    def test_recommend_takes_no_tuning_parameters(self, sample_recommender):
        """recommend() no longer accepts top_n/k_similar/similarity_weight/etc - the
        monthly policy is the sole configuration authority."""
        import inspect

        signature = inspect.signature(RecommendationEngine.recommend)
        assert list(signature.parameters) == ["self", "target_team", "prediction_month"]

    def test_recommend_excludes_maxed_practices(self, sample_recommender, sample_processor):
        """Test recommend excludes practices already at maximum level."""
        team, month = self._first_predictable(sample_recommender, sample_processor)
        result = sample_recommender.recommend(team, month)

        for practice in result.practices:
            assert result.current_levels[practice] < 1.0

    def test_recommend_sorted_by_score(self, sample_recommender, sample_processor):
        """Test recommend returns recommendations sorted by score (descending)."""
        team, month = self._first_predictable(sample_recommender, sample_processor)
        result = sample_recommender.recommend(team, month)

        scores = [result.scores[p] for p in result.practices]
        assert scores == sorted(scores, reverse=True)

    def test_recommend_team_not_found(self, sample_recommender, sample_processor):
        """An unrecognized team name raises ValueError (matches the old recommend()'s
        behavior) - APIService and the CLI both already check team existence before
        ever calling recommend(), so this is a caller-contract violation, not a
        graceful "insufficient practices" outcome."""
        engine = sample_recommender.policy_engine
        month = engine.prediction_months()[0] if engine.prediction_months() else None
        if month is None:
            pytest.skip("Sample fixture has no valid prediction month")

        with pytest.raises(ValueError):
            sample_recommender.recommend("UnknownTeam", month)

    def test_recommend_first_month_has_no_baseline(self, sample_recommender, sample_processor):
        """The dataset's very first month has no prior snapshot for any team, so it can
        never be recommendable. `prediction_month` here must be a real global month -
        PolicyEngine.recommend() assumes valid input, matching every current caller
        (APIService/CLI/BacktestEngine), which already validate against
        PolicyEngine.prediction_months() before calling."""
        first_month = sample_processor.get_all_months()[0]
        team = sample_processor.get_all_teams()[0]

        result = sample_recommender.recommend(team, first_month)
        assert result.insufficient_practices is True
        assert result.practices == ()

    def test_get_recommendation_explanation_basic(self, sample_recommender, sample_processor):
        """Test get_recommendation_explanation returns explanation."""
        team, month = self._first_predictable(sample_recommender, sample_processor)
        result = sample_recommender.recommend(team, month)

        if not result.practices:
            pytest.skip("No recommendations available for this team/month")

        practice = result.practices[0]
        explanation = sample_recommender.get_recommendation_explanation(team, month, practice)

        assert isinstance(explanation, dict)
        assert 'practice' in explanation
        assert 'similar_teams_improved' in explanation
        assert 'total_similar_teams_checked' in explanation
        assert 'similar_teams_list' in explanation
        assert 'has_sequence_boost' in explanation
        assert 'no_similar_teams_found' in explanation

        assert explanation['practice'] == practice
        assert isinstance(explanation['similar_teams_improved'], int)
        assert isinstance(explanation['total_similar_teams_checked'], int)
        assert isinstance(explanation['similar_teams_list'], list)
        assert isinstance(explanation['has_sequence_boost'], bool)
        assert isinstance(explanation['no_similar_teams_found'], bool)

    def test_get_recommendation_explanation_team_not_found(self, sample_recommender):
        """Test get_recommendation_explanation raises error for unknown team."""
        with pytest.raises(ValueError):
            sample_recommender.get_recommendation_explanation("UnknownTeam", 202001, "Practice1")

    def test_get_recommendation_explanation_month_not_found(self, sample_recommender, sample_processor):
        """Test get_recommendation_explanation raises error when team has no baseline for month."""
        team = sample_processor.get_all_teams()[0]
        with pytest.raises(ValueError):
            sample_recommender.get_recommendation_explanation(team, 99999999, "Practice1")
