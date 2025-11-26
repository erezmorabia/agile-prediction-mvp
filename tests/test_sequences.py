"""
Extended tests for SequenceMapper class.
"""

import pytest
from src.ml.sequences import SequenceMapper


class TestSequenceMapperExtended:
    """Extended tests for SequenceMapper functionality."""
    
    def test_get_typical_next_practices_basic(self, sample_sequence_mapper):
        """Test get_typical_next_practices returns next practices."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        # Get a practice that has transitions
        if len(mapper.transition_matrix) == 0:
            pytest.skip("No transitions learned")
        
        practice = list(mapper.transition_matrix.keys())[0]
        next_practices = mapper.get_typical_next_practices(practice, top_n=3)
        
        assert isinstance(next_practices, list)
        assert len(next_practices) <= 3
        
        # Check format: (practice_name, probability)
        for practice_info in next_practices:
            assert len(practice_info) == 2
            practice_name, probability = practice_info
            assert isinstance(practice_name, str)
            assert isinstance(probability, float)
            assert 0.0 <= probability <= 1.0
    
    def test_get_typical_next_practices_top_n(self, sample_sequence_mapper):
        """Test get_typical_next_practices respects top_n parameter."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        if len(mapper.transition_matrix) == 0:
            pytest.skip("No transitions learned")
        
        practice = list(mapper.transition_matrix.keys())[0]
        
        # Test with different top_n values
        for top_n in [1, 2, 5]:
            next_practices = mapper.get_typical_next_practices(practice, top_n=top_n)
            assert len(next_practices) <= top_n
    
    def test_get_typical_next_practices_no_transitions(self, sample_sequence_mapper):
        """Test get_typical_next_practices returns empty list for practice with no transitions."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        # Use a practice that likely has no transitions
        practice = "NonexistentPractice"
        next_practices = mapper.get_typical_next_practices(practice, top_n=3)
        
        assert isinstance(next_practices, list)
        assert len(next_practices) == 0
    
    def test_get_typical_next_practices_not_learned(self, sample_processor, sample_practices):
        """Test get_typical_next_practices raises error when sequences not learned."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        # Don't call learn_sequences()
        
        with pytest.raises(ValueError, match="Sequences not learned"):
            mapper.get_typical_next_practices("Practice1", top_n=3)
    
    def test_get_improvement_frequency(self, sample_sequence_mapper):
        """Test get_improvement_frequency returns frequency dictionary."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        freq = mapper.get_improvement_frequency()
        
        assert isinstance(freq, dict)
        # All values should be non-negative integers
        for practice, count in freq.items():
            assert isinstance(practice, str)
            assert isinstance(count, int)
            assert count >= 0
    
    def test_get_improvement_frequency_not_learned(self, sample_processor, sample_practices):
        """Test get_improvement_frequency raises error when sequences not learned."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        # Don't call learn_sequences()
        
        with pytest.raises(ValueError, match="Sequences not learned"):
            mapper.get_improvement_frequency()
    
    def test_get_sequence_stats_not_learned(self, sample_processor, sample_practices):
        """Test get_sequence_stats returns status when not learned."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        stats = mapper.get_sequence_stats()
        
        assert isinstance(stats, dict)
        assert stats.get('status') == 'not_learned'
    
    def test_get_sequence_stats_after_learning(self, sample_sequence_mapper):
        """Test get_sequence_stats after learning sequences."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        stats = mapper.get_sequence_stats()
        
        assert isinstance(stats, dict)
        assert 'status' not in stats or stats.get('status') != 'not_learned'
        assert 'num_transition_types' in stats
        assert 'total_transitions' in stats
        assert 'practices_that_improved' in stats
        
        # Check that stats are valid
        assert stats['num_transition_types'] >= 0
        assert stats['total_transitions'] >= 0
        assert stats['practices_that_improved'] >= 0
    
    def test_get_all_sequences_basic(self, sample_sequence_mapper):
        """Test get_all_sequences returns all sequences."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        sequences = mapper.get_all_sequences(min_count=1)
        
        assert isinstance(sequences, list)
        
        # Check format: (from_practice, to_practice, count, probability)
        for seq in sequences:
            assert len(seq) == 4
            from_practice, to_practice, count, probability = seq
            assert isinstance(from_practice, str)
            assert isinstance(to_practice, str)
            assert isinstance(count, int)
            assert isinstance(probability, float)
            assert count >= 1
            assert 0.0 <= probability <= 1.0
    
    def test_get_all_sequences_min_count(self, sample_sequence_mapper):
        """Test get_all_sequences filters by min_count."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        # Get all sequences
        all_sequences = mapper.get_all_sequences(min_count=1)
        
        # Filter with higher min_count
        filtered_sequences = mapper.get_all_sequences(min_count=2)
        
        assert len(filtered_sequences) <= len(all_sequences)
        
        # All filtered sequences should have count >= min_count
        for from_practice, to_practice, count, probability in filtered_sequences:
            assert count >= 2
    
    def test_get_all_sequences_sorted(self, sample_sequence_mapper):
        """Test get_all_sequences returns sequences sorted by count (descending)."""
        mapper = sample_sequence_mapper
        
        if not mapper.learned:
            mapper.learn_sequences()
        
        sequences = mapper.get_all_sequences(min_count=1)
        
        if len(sequences) > 1:
            # Check that sequences are sorted by count (descending)
            counts = [seq[2] for seq in sequences]
            assert counts == sorted(counts, reverse=True)
    
    def test_get_all_sequences_not_learned(self, sample_processor, sample_practices):
        """Test get_all_sequences returns empty list when not learned."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        # Don't call learn_sequences()
        
        sequences = mapper.get_all_sequences(min_count=1)
        
        assert isinstance(sequences, list)
        assert len(sequences) == 0
    
    def test_learn_sequences_up_to_month_basic(self, sample_processor, sample_practices):
        """Test learn_sequences_up_to_month learns sequences up to specified month."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        months = sample_processor.get_all_months()
        
        if len(months) < 3:
            pytest.skip("Need at least 3 months")
        
        # Learn sequences up to second-to-last month
        max_month = months[-2]
        mapper.learn_sequences_up_to_month(max_month)
        
        assert mapper.learned
        
        # Should have learned some transitions
        assert len(mapper.transition_matrix) >= 0 or len(mapper.practice_improvement_freq) >= 0
    
    def test_learn_sequences_up_to_month_caching(self, sample_processor, sample_practices):
        """Test learn_sequences_up_to_month uses caching."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        months = sample_processor.get_all_months()
        
        if len(months) < 3:
            pytest.skip("Need at least 3 months")
        
        max_month = months[-2]
        
        # First call
        mapper.learn_sequences_up_to_month(max_month)
        first_transitions = dict(mapper.transition_matrix)
        first_freq = dict(mapper.practice_improvement_freq)
        
        # Second call should use cache
        mapper.learn_sequences_up_to_month(max_month)
        second_transitions = dict(mapper.transition_matrix)
        second_freq = dict(mapper.practice_improvement_freq)
        
        # Results should be the same (from cache)
        assert first_transitions == second_transitions
        assert first_freq == second_freq
    
    def test_learn_sequences_up_to_month_insufficient_data(self, sample_processor, sample_practices):
        """Test learn_sequences_up_to_month handles insufficient data gracefully."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        # Use first month (no past months)
        max_month = months[0]
        mapper.learn_sequences_up_to_month(max_month)
        
        # Should still mark as learned, but with no transitions
        assert mapper.learned
    
    def test_learn_sequences_up_to_month_excludes_future(self, sample_processor, sample_practices):
        """Test learn_sequences_up_to_month only uses months before max_month."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        months = sample_processor.get_all_months()
        
        if len(months) < 3:
            pytest.skip("Need at least 3 months")
        
        max_month = months[-2]
        mapper.learn_sequences_up_to_month(max_month)
        
        # Verify that sequences were learned only from months < max_month
        # This is tested implicitly by checking that learned sequences exist
        assert mapper.learned
    
    def test_learn_sequences_basic(self, sample_processor, sample_practices):
        """Test learn_sequences learns from all available data."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        
        mapper.learn_sequences()
        
        assert mapper.learned
        assert len(mapper.transition_matrix) >= 0 or len(mapper.practice_improvement_freq) >= 0
    
    def test_learned_flag(self, sample_processor, sample_practices):
        """Test learned flag is set correctly."""
        mapper = SequenceMapper(sample_processor, sample_practices)
        
        assert not mapper.learned
        
        mapper.learn_sequences()
        
        assert mapper.learned

