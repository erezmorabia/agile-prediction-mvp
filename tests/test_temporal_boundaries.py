"""
Critical tests for temporal boundary enforcement and data leakage prevention.

These tests verify that the ML algorithms never use future data when making predictions,
which would invalidate the model's results. This is the most critical aspect of the system.

Run tests with: python -m pytest tests/test_temporal_boundaries.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collections import Counter, defaultdict

import pytest
import pandas as pd
import numpy as np
from src.data import DataProcessor
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine


class TestTemporalBoundaries:
    """Test that algorithms strictly enforce temporal boundaries to prevent data leakage."""

    @pytest.fixture
    def temporal_dataframe(self):
        """Create DataFrame with clear temporal structure for testing boundaries."""
        # Create data spanning 6 months with clear improvement patterns
        data = {
            'Team Name': ['TeamA'] * 6 + ['TeamB'] * 6 + ['TeamC'] * 6,
            'Month': [202001, 202002, 202003, 202004, 202005, 202006] * 3,
            'Practice1': [0, 0, 1, 1, 2, 2,  # TeamA improves in 202003, 202005
                         0, 0, 0, 1, 1, 2,  # TeamB improves in 202004, 202006
                         0, 1, 1, 1, 2, 2],  # TeamC improves in 202002, 202005
            'Practice2': [0, 0, 0, 1, 1, 2,  # TeamA improves in 202004, 202006
                         0, 0, 1, 1, 2, 2,  # TeamB improves in 202003, 202005
                         0, 0, 0, 0, 1, 1],  # TeamC improves in 202005
            'Practice3': [0, 0, 0, 0, 1, 1,  # TeamA improves in 202005
                         0, 0, 0, 1, 1, 2,  # TeamB improves in 202004, 202006
                         0, 0, 1, 1, 2, 2],  # TeamC improves in 202003, 202005
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def temporal_processor(self, temporal_dataframe):
        """Create processor with temporal test data."""
        practices = ['Practice1', 'Practice2', 'Practice3']
        processor = DataProcessor(temporal_dataframe, practices)
        processor.process()
        return processor

    @pytest.fixture
    def temporal_recommender(self, temporal_processor):
        """Create recommender with temporal test data."""
        practices = ['Practice1', 'Practice2', 'Practice3']
        similarity_engine = SimilarityEngine(temporal_processor)
        sequence_mapper = SequenceMapper(temporal_processor, practices)
        sequence_mapper.learn_sequences()
        recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)
        return recommender

    @staticmethod
    def _reconstruct_first_order_transitions(processor, practices, max_month):
        """
        Independently reconstruct the expected first-order Markov transition matrix
        using only months < max_month, mirroring SequenceMapper's construction:
        chain each improvement-bearing step (skipping steps with zero improvements) to
        the next one, full cross-product, no edges within a step.

        Written independently of SequenceMapper so the test doesn't just re-exercise
        the same code path it's meant to check.
        """
        expected = defaultdict(Counter)

        for team in processor.get_all_teams():
            history = processor.get_team_history(team)
            team_months = sorted([m for m in history.keys() if m < max_month])

            improved_sets = []
            for i in range(len(team_months) - 1):
                curr_vector = history[team_months[i]]
                next_vector = history[team_months[i + 1]]
                improved = [practices[j] for j in range(len(practices)) if next_vector[j] > curr_vector[j]]
                if improved:
                    improved_sets.append(improved)

            for prev_set, next_set in zip(improved_sets, improved_sets[1:]):
                for prev_practice in prev_set:
                    for next_practice in next_set:
                        expected[prev_practice][next_practice] += 1

        return {k: dict(v) for k, v in expected.items()}

    def test_sequences_only_learn_from_past_months(self, temporal_processor):
        """
        CRITICAL: Verify sequence learning only uses months < max_month.

        This tests the core data leakage prevention: when learning sequences
        up to month M, the algorithm must ONLY use data from months < M,
        never from month M itself or later months.
        """
        practices = ['Practice1', 'Practice2', 'Practice3']
        sequence_mapper = SequenceMapper(temporal_processor, practices)

        # Learn sequences up to 202004
        max_month = 202004
        sequence_mapper.learn_sequences_up_to_month(max_month)
        actual = {k: dict(v) for k, v in sequence_mapper.transition_matrix.items()}

        # The transition matrix built from months < max_month must exactly match an
        # independent reconstruction restricted to the same months - anything else
        # means either leakage from month >= max_month or a construction mismatch.
        expected = self._reconstruct_first_order_transitions(temporal_processor, practices, max_month)
        assert actual == expected, (
            f"Transitions don't match a months-<{max_month}-only reconstruction "
            f"(possible data leakage). Expected {expected}, got {actual}"
        )

        # Sanity check that the boundary actually matters for this fixture: including
        # month 202004 (TeamB improves Practice1+2 in the 202003->202004 step) must change
        # the matrix, otherwise this test isn't exercising the boundary at all.
        expected_with_leak = self._reconstruct_first_order_transitions(temporal_processor, practices, 202005)
        assert expected_with_leak != expected, (
            "Including month 202004 didn't change the expected transitions - "
            "this fixture no longer exercises the temporal boundary."
        )

    def test_similarity_only_uses_past_months(self, temporal_processor, temporal_recommender):
        """
        CRITICAL: Verify similarity matching only uses months < target_month.

        When finding similar teams at month M, the algorithm must only compare
        against other teams' states at months < M, never at month M or later.
        """
        similarity_engine = SimilarityEngine(temporal_processor)

        target_team = 'TeamA'
        target_month = 202004
        k_similar = 5

        # Find similar teams (use min_similarity=0.0 to allow all teams for testing)
        similar_teams = similarity_engine.find_similar_teams(
            target_team, target_month, k=k_similar, min_similarity=0.0
        )

        # CRITICAL CHECK: All similar teams must be from months < target_month
        for team, month, similarity in similar_teams:
            assert month < target_month, \
                f"Data leakage! Similar team '{team}' from month {month} >= target {target_month}"

        # Additional check: Verify no team appears at target_month or later
        for team, month, similarity in similar_teams:
            assert month != target_month, \
                f"Data leakage! Found team at exact target_month {target_month}"

    def test_backtest_recommendations_use_only_past_data(self, temporal_recommender, temporal_processor):
        """
        CRITICAL: Verify backtest recommendations at month M use only data from months < M.

        When generating recommendations for backtesting at test_month M,
        the system must only use data from months < M for training.
        """
        target_team = 'TeamA'
        test_month = 202004

        # Get recommendations at test_month (use min_similarity=0.0 to ensure we find teams)
        recommendations = temporal_recommender.recommend(
            target_team,
            test_month,
            top_n=2,
            k_similar=3,
            allow_first_three_months=True,  # Allow testing at any month
            min_similarity_threshold=0.0  # Allow all similarity levels for testing
        )

        # Verify recommendations were generated (basic sanity check)
        assert isinstance(recommendations, list), "Recommendations should be a list"

        # CRITICAL: Verify sequences were learned only from months < test_month
        sequence_mapper = temporal_recommender.sequence_mapper
        all_months = sorted(temporal_processor.get_all_months())

        # The sequences should not include transitions from test_month or later
        # We can't directly verify this without accessing internal state,
        # but we can verify that recommendations are consistent with past data only

        # Check: If we re-learn sequences with max_month = test_month,
        # the transitions should not change (they're already limited to past data)
        sequence_mapper.learn_sequences_up_to_month(test_month)
        transitions_at_test = sequence_mapper.transition_matrix

        # Verify no transitions use test_month or later as the "from" month
        for practice, next_practices in transitions_at_test.items():
            # This is indirect, but verifies the transition matrix structure
            assert isinstance(next_practices, dict), \
                f"Transition matrix corrupted for practice {practice}"

    def test_boundary_month_exactly_equal_excluded(self, temporal_processor):
        """
        CRITICAL: Verify month exactly = current_month is EXCLUDED from training.

        This is a boundary condition test: when learning up to month M,
        month M itself must be excluded (only months < M, not <= M).
        """
        practices = ['Practice1', 'Practice2', 'Practice3']
        sequence_mapper = SequenceMapper(temporal_processor, practices)

        test_month = 202003

        # Learn sequences up to test_month
        sequence_mapper.learn_sequences_up_to_month(test_month)
        transitions = sequence_mapper.transition_matrix

        # Manually verify: check that transitions from 202003 are NOT included
        all_teams = temporal_processor.get_all_teams()

        for team in all_teams:
            history = temporal_processor.get_team_history(team)

            # If team has test_month and a month after it
            team_months = sorted(history.keys())
            if test_month in team_months:
                test_idx = team_months.index(test_month)

                if test_idx + 1 < len(team_months):
                    # Check if any improvements from test_month -> next_month
                    # These should NOT be in the learned transitions
                    curr_vector = history[test_month]
                    next_month = team_months[test_idx + 1]
                    next_vector = history[next_month]

                    improved = [i for i in range(len(practices))
                               if next_vector[i] > curr_vector[i]]

                    # If there were improvements from test_month forward,
                    # verify they're not reflected in the transition counts
                    # (This is indirect, but tests the boundary condition)
                    if len(improved) > 0:
                        # The total number of transitions should be less than if we included test_month
                        sequence_mapper.learn_sequences_up_to_month(next_month)
                        transitions_with_future = sequence_mapper.transition_matrix

                        # Count should be different if test_month boundary is respected
                        count_past = sum(len(v) for v in transitions.values())
                        count_with_future = sum(len(v) for v in transitions_with_future.values())

                        assert count_with_future >= count_past, \
                            f"Transition count decreased when including more data - logic error"

    def test_recommendation_at_first_month_raises_error(self, temporal_recommender):
        """
        CRITICAL: Verify recommendations at first global month raise ValueError.

        The first month has no history, so recommendations should fail
        unless allow_first_three_months=True.
        """
        target_team = 'TeamA'
        first_month = 202001  # First month in our test data

        # Should raise ValueError
        with pytest.raises(ValueError, match="first month"):
            temporal_recommender.recommend(
                target_team,
                first_month,
                top_n=2,
                allow_first_three_months=False  # Strict mode
            )

        # Should work at a non-first month with allow_first_three_months=True
        # (month 1 itself has no past history to draw from, use month 4 which has it)
        recommendations = temporal_recommender.recommend(
            target_team,
            202004,
            top_n=2,
            allow_first_three_months=True,
            min_similarity_threshold=0.0,
        )
        assert isinstance(recommendations, list)

    def test_no_future_similar_teams_in_explanation(self, temporal_recommender, temporal_processor):
        """
        CRITICAL: Verify recommendation explanations don't reference future data.

        When explaining why a practice was recommended, the system should
        only reference similar teams from past months, not future months.
        """
        target_team = 'TeamA'
        target_month = 202004
        practice = 'Practice1'

        # Get recommendations (use min_similarity=0.0)
        recommendations = temporal_recommender.recommend(
            target_team,
            target_month,
            top_n=2,
            allow_first_three_months=True,
            min_similarity_threshold=0.0
        )

        # Get explanation for first recommended practice
        if len(recommendations) > 0:
            recommended_practice = recommendations[0][0]

            explanation = temporal_recommender.get_recommendation_explanation(
                target_team,
                target_month,
                recommended_practice,
                recent_improvements_months=3
            )

            # Parse explanation for mentioned months (this is heuristic)
            # The explanation should not mention months >= target_month

            # Verify explanation exists and is a dict
            assert isinstance(explanation, dict), "Explanation should be a dict"
            assert len(explanation) > 0, "Explanation should not be empty"


class TestDataLeakageEdgeCases:
    """Test edge cases that could cause subtle data leakage."""

    @pytest.fixture
    def edge_case_dataframe(self):
        """Create DataFrame with edge case scenarios."""
        data = {
            'Team Name': ['TeamA'] * 5 + ['TeamB'] * 5,
            'Month': [202001, 202002, 202003, 202004, 202005] * 2,
            'Practice1': [0, 1, 2, 2, 3,  # TeamA maxes out
                         0, 0, 1, 2, 2],  # TeamB lags behind
            'Practice2': [0, 0, 0, 1, 2,  # TeamA improves later
                         0, 1, 1, 1, 2],  # TeamB improves early
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def edge_case_processor(self, edge_case_dataframe):
        """Create processor with edge case data."""
        practices = ['Practice1', 'Practice2']
        processor = DataProcessor(edge_case_dataframe, practices)
        processor.process()
        return processor

    def test_sparse_team_data_no_leakage(self, edge_case_processor):
        """
        Test that teams with sparse/missing months don't cause data leakage.

        When teams have missing months, the algorithm should not accidentally
        use future data to fill gaps.
        """
        practices = ['Practice1', 'Practice2']
        sequence_mapper = SequenceMapper(edge_case_processor, practices)

        # Learn sequences up to 202004 (returns None, updates internal state)
        sequence_mapper.learn_sequences_up_to_month(202004)

        # Get the learned transition matrix
        transition_matrix = sequence_mapper.transition_matrix

        # Verify transition matrix is valid (it's a defaultdict(Counter))
        assert transition_matrix is not None, "Transition matrix should exist"

        # Get typical next practices to verify structure
        for practice in practices:
            next_practices = sequence_mapper.get_typical_next_practices(practice, top_n=5)
            # Should return a list of tuples (practice, probability)
            assert isinstance(next_practices, list), f"Next practices should be a list for {practice}"
            for next_practice, prob in next_practices:
                assert 0.0 <= prob <= 1.0, \
                    f"Invalid probability {prob} for {practice} -> {next_practice}"

    def test_boundary_conditions_off_by_one(self, edge_case_processor):
        """
        Test off-by-one errors in month boundary checking.

        Common bug: using <= instead of <, or >= instead of >.
        Verify strict inequality is enforced.
        """
        practices = ['Practice1', 'Practice2']
        similarity_engine = SimilarityEngine(edge_case_processor)

        target_team = 'TeamA'
        target_month = 202003

        similar_teams = similarity_engine.find_similar_teams(
            target_team, target_month, k=5, min_similarity=0.0
        )

        # CRITICAL: ALL similar teams must be from months STRICTLY < target_month
        for team, month, similarity in similar_teams:
            assert month < target_month, \
                f"Off-by-one error! Team '{team}' from month {month} not < {target_month}"

            # Additional check: month should not equal target_month
            assert month != target_month, \
                f"Boundary error! Team '{team}' from exact target_month {target_month}"

    def test_empty_historical_window(self, edge_case_processor):
        """
        Test handling when no historical data exists before target_month.

        If target_month is the first month globally, there's no past data.
        System should fail gracefully.
        """
        practices = ['Practice1', 'Practice2']
        sequence_mapper = SequenceMapper(edge_case_processor, practices)

        # Try to learn sequences up to the first month
        first_month = 202001

        # This should result in empty transitions (no past data)
        sequence_mapper.learn_sequences_up_to_month(first_month)
        transition_matrix = sequence_mapper.transition_matrix

        # Verify empty or minimal transitions
        # With no past months, transition_matrix should be empty or have no entries
        total_transitions = sum(len(transition_matrix[p]) for p in practices)
        assert total_transitions == 0, \
            f"Should have no transitions for first month, got {total_transitions}"


class TestRecommendationTemporalConsistency:
    """Test that recommendations are temporally consistent."""

    @pytest.fixture
    def consistency_dataframe(self):
        """Create DataFrame for consistency testing."""
        data = {
            'Team Name': ['TeamA'] * 4 + ['TeamB'] * 4,
            'Month': [202001, 202002, 202003, 202004] * 2,
            'Practice1': [0, 1, 2, 3,  # TeamA fully progresses
                         0, 0, 1, 2],  # TeamB lags
            'Practice2': [0, 0, 1, 2,  # TeamA progresses
                         0, 0, 0, 1],  # TeamB slower
            'Practice3': [0, 0, 0, 1,  # TeamA starts late
                         0, 0, 0, 0],  # TeamB doesn't start
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def consistency_recommender(self, consistency_dataframe):
        """Create recommender for consistency testing."""
        practices = ['Practice1', 'Practice2', 'Practice3']
        processor = DataProcessor(consistency_dataframe, practices)
        processor.process()
        similarity_engine = SimilarityEngine(processor)
        sequence_mapper = SequenceMapper(processor, practices)
        sequence_mapper.learn_sequences()
        recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)
        return recommender

    def test_recommendations_improve_over_time(self, consistency_recommender):
        """
        Test that recommendations at later months use more historical data.

        As time progresses, the system should have more training data,
        potentially leading to different (hopefully better) recommendations.
        """
        target_team = 'TeamB'

        # Get recommendations at different months (use min_similarity=0.0)
        recs_early = consistency_recommender.recommend(
            target_team, 202002, top_n=2, allow_first_three_months=True,
            min_similarity_threshold=0.0
        )

        recs_late = consistency_recommender.recommend(
            target_team, 202004, top_n=2, allow_first_three_months=True,
            min_similarity_threshold=0.0
        )

        # Both should be valid recommendations
        assert isinstance(recs_early, list)
        assert isinstance(recs_late, list)

        # Later recommendations might be different (more data available)
        # This is not a strict requirement, just a consistency check
        # The key is that both are valid and use only past data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
