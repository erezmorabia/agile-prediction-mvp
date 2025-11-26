"""
Extended tests for RecommendationEngine class.
"""

import pytest
from src.ml.recommender import RecommendationEngine


class TestRecommendationEngineExtended:
    """Extended tests for RecommendationEngine functionality."""
    
    def test_recommend_basic(self, sample_recommender, sample_processor):
        """Test recommend returns recommendations."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]  # Use second-to-last month
        
        recommendations = recommender.recommend(team, current_month, top_n=3)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        
        # Check format: (practice_name, score, current_level)
        for rec in recommendations:
            assert len(rec) == 3
            practice_name, score, current_level = rec
            assert isinstance(practice_name, str)
            assert isinstance(score, float)
            assert isinstance(current_level, float)
            assert 0.0 <= score <= 1.0
            assert 0.0 <= current_level <= 1.0
    
    def test_recommend_top_n_parameter(self, sample_recommender, sample_processor):
        """Test recommend respects top_n parameter."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Test with different top_n values
        for top_n in [1, 2, 5]:
            recommendations = recommender.recommend(team, current_month, top_n=top_n)
            assert len(recommendations) <= top_n
    
    def test_recommend_k_similar_parameter(self, sample_recommender, sample_processor):
        """Test recommend respects k_similar parameter."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Test with different k_similar values
        for k_similar in [5, 10, 19]:
            recommendations = recommender.recommend(
                team, current_month, top_n=3, k_similar=k_similar
            )
            assert isinstance(recommendations, list)
    
    def test_recommend_similarity_weight_parameter(self, sample_recommender, sample_processor):
        """Test recommend respects similarity_weight parameter."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Test with different similarity weights
        for weight in [0.0, 0.5, 1.0]:
            recommendations = recommender.recommend(
                team, current_month, top_n=3, similarity_weight=weight
            )
            assert isinstance(recommendations, list)
    
    def test_recommend_excludes_maxed_practices(self, sample_recommender, sample_processor):
        """Test recommend excludes practices already at maximum level."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        recommendations = recommender.recommend(team, current_month, top_n=10)
        
        # Check that no recommendations have current_level >= 1.0
        for practice_name, score, current_level in recommendations:
            assert current_level < 1.0
    
    def test_recommend_sorted_by_score(self, sample_recommender, sample_processor):
        """Test recommend returns recommendations sorted by score (descending)."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        recommendations = recommender.recommend(team, current_month, top_n=5)
        
        if len(recommendations) > 1:
            # Check that scores are in descending order
            scores = [rec[1] for rec in recommendations]
            assert scores == sorted(scores, reverse=True)
    
    def test_recommend_team_not_found(self, sample_recommender):
        """Test recommend raises error for unknown team."""
        recommender = sample_recommender
        
        with pytest.raises(ValueError):
            recommender.recommend("UnknownTeam", 202001, top_n=3)
    
    def test_recommend_month_not_found(self, sample_recommender, sample_processor):
        """Test recommend raises error when team has no data for month."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        
        if len(teams) == 0:
            pytest.skip("No teams available")
        
        team = teams[0]
        invalid_month = 99999999
        
        with pytest.raises(ValueError):
            recommender.recommend(team, invalid_month, top_n=3)
    
    def test_recommend_first_month_restriction(self, sample_recommender, sample_processor):
        """Test recommend restricts first month (without allow_first_three_months)."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        # Get first month globally
        all_months = sorted(sample_processor.get_all_months())
        first_month = all_months[0]
        
        # If team's first month is the global first month, should raise error
        if team_months[0] == first_month:
            with pytest.raises(ValueError, match="at least 2 months"):
                recommender.recommend(team, first_month, top_n=3, allow_first_three_months=False)
    
    def test_recommend_allow_first_three_months(self, sample_recommender, sample_processor):
        """Test recommend allows first month when allow_first_three_months=True."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[0]
        
        # Should work with allow_first_three_months=True
        recommendations = recommender.recommend(
            team, current_month, top_n=3, allow_first_three_months=True
        )
        assert isinstance(recommendations, list)
    
    def test_get_recommendation_explanation_basic(self, sample_recommender, sample_processor):
        """Test get_recommendation_explanation returns explanation."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Get a recommendation first
        recommendations = recommender.recommend(team, current_month, top_n=1)
        
        if len(recommendations) == 0:
            pytest.skip("No recommendations available")
        
        practice = recommendations[0][0]
        
        explanation = recommender.get_recommendation_explanation(team, current_month, practice)
        
        assert isinstance(explanation, dict)
        assert 'practice' in explanation
        assert 'similar_teams_improved' in explanation
        assert 'total_similar_teams_checked' in explanation
        assert 'similar_teams_list' in explanation
        assert 'has_sequence_boost' in explanation
        
        assert explanation['practice'] == practice
        assert isinstance(explanation['similar_teams_improved'], int)
        assert isinstance(explanation['total_similar_teams_checked'], int)
        assert isinstance(explanation['similar_teams_list'], list)
        assert isinstance(explanation['has_sequence_boost'], bool)
    
    def test_get_recommendation_explanation_team_not_found(self, sample_recommender):
        """Test get_recommendation_explanation raises error for unknown team."""
        recommender = sample_recommender
        
        with pytest.raises(ValueError):
            recommender.get_recommendation_explanation("UnknownTeam", 202001, "Practice1")
    
    def test_get_recommendation_explanation_month_not_found(self, sample_recommender, sample_processor):
        """Test get_recommendation_explanation raises error when team has no data for month."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        
        if len(teams) == 0:
            pytest.skip("No teams available")
        
        team = teams[0]
        invalid_month = 99999999
        
        with pytest.raises(ValueError):
            recommender.get_recommendation_explanation(team, invalid_month, "Practice1")
    
    def test_recommend_no_similar_teams(self, sample_recommender, sample_processor):
        """Test recommend handles case when no similar teams found."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Use very high similarity threshold to potentially find no teams
        try:
            recommendations = recommender.recommend(
                team, current_month, top_n=3, min_similarity_threshold=0.99
            )
            # Should either return empty list or raise ValueError
            assert isinstance(recommendations, list)
        except ValueError as e:
            # ValueError is acceptable if no similar teams found
            assert "No similar teams" in str(e) or "similar teams" in str(e).lower()
    
    def test_recommend_min_similarity_threshold(self, sample_recommender, sample_processor):
        """Test recommend respects min_similarity_threshold parameter."""
        recommender = sample_recommender
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Need at least 1 team and 2 months")
        
        team = teams[0]
        history = sample_processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} needs at least 2 months")
        
        current_month = team_months[-2]
        
        # Test with different thresholds
        for threshold in [0.0, 0.5, 0.75]:
            try:
                recommendations = recommender.recommend(
                    team, current_month, top_n=3, min_similarity_threshold=threshold
                )
                assert isinstance(recommendations, list)
            except ValueError:
                # ValueError is acceptable if threshold too high
                pass

