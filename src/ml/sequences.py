"""
SequenceMapper: Learn improvement sequences using Markov chains.
"""

from collections import Counter, defaultdict


class SequenceMapper:
    """Learn and map sequences of practice improvements across the organization."""

    def __init__(self, processor, practices):
        """
        Initialize SequenceMapper.

        Args:
            processor: DataProcessor instance with processed team histories
            practices (list): List of practice names
        """
        self.processor = processor
        self.practices = practices
        self.transition_matrix = defaultdict(Counter)
        self.practice_improvement_freq = Counter()
        self.learned = False
        # Cache for time-limited sequences: {max_month: (transition_matrix, practice_improvement_freq)}
        self._sequence_cache = {}

    def learn_sequences(self) -> None:
        """
        Learn transition patterns from historical data across all teams and months.

        Analyzes improvement sequences by examining consecutive time periods for each team.
        When multiple practices improve in the same time period, builds a transition matrix
        showing which practices typically follow others. This creates a Markov-like model
        of improvement patterns across the organization.

        The algorithm:
        1. For each team, iterate through consecutive months
        2. Identify all practices that improved from one month to the next
        3. For each pair of improved practices (A, B) where A improved before B,
           increment the transition count from A to B
        4. Track overall improvement frequency for each practice

        After calling this method, use get_typical_next_practices() to query the
        learned patterns.

        Returns:
            None: Modifies internal state (self.transition_matrix and
                self.practice_improvement_freq). Sets self.learned = True.

        Note:
            - Only considers improvements (increases in practice scores)
            - Requires at least 2 months of data per team
            - Transitions are learned from all available historical data
            - For time-limited sequences (backtesting), use learn_sequences_up_to_month()

        Example:
            >>> mapper = SequenceMapper(processor, practices)
            >>> mapper.learn_sequences()
            Learning improvement sequences...
            Learned 45 transition patterns
        """
        print("Learning improvement sequences...")

        teams = self.processor.get_all_teams()
        months = self.processor.get_all_months()

        for team in teams:
            history = self.processor.get_team_history(team)

            # Sort months for this team
            team_months = sorted([m for m in months if m in history])

            # Look at consecutive time periods
            for i in range(len(team_months) - 1):
                current_month = team_months[i]
                next_month = team_months[i + 1]

                current_vector = history[current_month]
                next_vector = history[next_month]

                # Find which practices improved
                improved_practices = []
                for j, (curr, nxt) in enumerate(zip(current_vector, next_vector)):
                    if nxt > curr:  # Improved
                        practice_name = self.practices[j]
                        improved_practices.append(practice_name)
                        self.practice_improvement_freq[practice_name] += 1

                # Build transition matrix from improvements
                if len(improved_practices) > 1:
                    for j in range(len(improved_practices) - 1):
                        prev = improved_practices[j]
                        curr = improved_practices[j + 1]
                        self.transition_matrix[prev][curr] += 1

        self.learned = True
        print(f"Learned {len(self.transition_matrix)} transition patterns")

    def learn_sequences_up_to_month(self, max_month: int) -> None:
        """
        Learn transition patterns from historical data up to (but not including) max_month.
        Only learns from transitions where both months are < max_month.
        Uses caching to avoid recomputation.

        Args:
            max_month (int): Maximum month (exclusive) - sequences learned from months < max_month
        """
        # Check cache first
        if max_month in self._sequence_cache:
            cached_transition_matrix, cached_practice_improvement_freq = self._sequence_cache[max_month]
            # Create copies to avoid mutation issues
            self.transition_matrix = defaultdict(Counter)
            for k, v in cached_transition_matrix.items():
                self.transition_matrix[k] = Counter(v)
            self.practice_improvement_freq = Counter(cached_practice_improvement_freq)
            self.learned = True
            return

        # Clear previous state
        self.transition_matrix = defaultdict(Counter)
        self.practice_improvement_freq = Counter()

        teams = self.processor.get_all_teams()
        months = self.processor.get_all_months()

        # Filter months to only those < max_month
        available_months = [m for m in months if m < max_month]

        if len(available_months) < 2:
            # Need at least 2 months to learn transitions
            self.learned = True
            # Cache empty result
            self._sequence_cache[max_month] = (defaultdict(Counter), Counter())
            return

        for team in teams:
            history = self.processor.get_team_history(team)

            # Sort months for this team, but only include months < max_month
            team_months = sorted([m for m in available_months if m in history])

            # Look at consecutive time periods
            for i in range(len(team_months) - 1):
                current_month = team_months[i]
                next_month = team_months[i + 1]

                # Double-check: both should be < max_month (already filtered, but be safe)
                if current_month >= max_month or next_month >= max_month:
                    continue

                current_vector = history[current_month]
                next_vector = history[next_month]

                # Find which practices improved
                improved_practices = []
                for j, (curr, nxt) in enumerate(zip(current_vector, next_vector)):
                    if nxt > curr:  # Improved
                        practice_name = self.practices[j]
                        improved_practices.append(practice_name)
                        self.practice_improvement_freq[practice_name] += 1

                # Build transition matrix from improvements
                if len(improved_practices) > 1:
                    for j in range(len(improved_practices) - 1):
                        prev = improved_practices[j]
                        curr = improved_practices[j + 1]
                        self.transition_matrix[prev][curr] += 1

        self.learned = True

        # Cache the result (create deep copies to avoid mutation issues)
        cached_transition_matrix = defaultdict(Counter)
        for k, v in self.transition_matrix.items():
            cached_transition_matrix[k] = Counter(v)
        cached_practice_improvement_freq = Counter(self.practice_improvement_freq)

        self._sequence_cache[max_month] = (cached_transition_matrix, cached_practice_improvement_freq)

    def get_typical_next_practices(self, practice: str, top_n: int = 3) -> list:
        """
        Get practices that typically follow a given practice.

        Args:
            practice (str): Practice name
            top_n (int): Number of practices to return

        Returns:
            list: List of (practice_name, probability) tuples

        Raises:
            ValueError: If sequences not learned
        """
        if not self.learned:
            raise ValueError("Sequences not learned. Call learn_sequences() first.")

        if practice not in self.transition_matrix:
            return []

        transitions = self.transition_matrix[practice].most_common(top_n)
        total = sum(self.transition_matrix[practice].values())

        if total == 0:
            return []

        return [(p, count / total) for p, count in transitions]

    def get_improvement_frequency(self) -> dict:
        """
        Get how often each practice was improved across organization.

        Returns:
            dict: Dictionary of practice -> improvement count
        """
        if not self.learned:
            raise ValueError("Sequences not learned. Call learn_sequences() first.")

        return dict(self.practice_improvement_freq.most_common())

    def get_sequence_stats(self) -> dict:
        """
        Get statistics about learned sequences.

        Returns:
            dict: Statistics including number of transitions, frequencies, etc.
        """
        if not self.learned:
            return {"status": "not_learned"}

        total_transitions = sum(sum(v.values()) for v in self.transition_matrix.values())

        return {
            "num_transition_types": len(self.transition_matrix),
            "total_transitions": total_transitions,
            "practices_that_improved": len(self.practice_improvement_freq),
            "most_improved_practice": self.practice_improvement_freq.most_common(1)[0]
            if self.practice_improvement_freq
            else None,
            "avg_transitions_per_type": (
                total_transitions / len(self.transition_matrix) if self.transition_matrix else 0
            ),
        }

    def get_all_sequences(self, min_count: int = 1) -> list:
        """
        Get all learned improvement sequences sorted by frequency.

        Args:
            min_count (int): Minimum number of times a transition must occur to be included

        Returns:
            list: List of (from_practice, to_practice, count, probability) tuples,
                  sorted by count (descending)
        """
        if not self.learned:
            return []

        sequences = []

        for from_practice, transitions in self.transition_matrix.items():
            total_from = sum(transitions.values())

            for to_practice, count in transitions.items():
                if count >= min_count:
                    probability = count / total_from if total_from > 0 else 0
                    sequences.append((from_practice, to_practice, count, probability))

        # Sort by count (descending), then by probability (descending)
        sequences.sort(key=lambda x: (-x[2], -x[3]))

        return sequences
