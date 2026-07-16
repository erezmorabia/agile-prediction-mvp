"""
SequenceMapper: Learn first-order Markov chain improvement sequences.
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
        Learn first-order Markov transition patterns from historical data across all teams.

        For each team, builds the chronological sequence of "improvement-bearing" months
        (months where at least one practice improved relative to the prior month), skipping
        over months with zero improvements. Each practice improved in one such step gets a
        transition edge to every practice improved in the *next* improvement-bearing step
        (full cross-product between consecutive steps). Practices improved within the same
        step get no edge between them, since simultaneous improvements carry no ordering
        information.

        The algorithm (per team):
        1. Sort the team's months chronologically
        2. For each consecutive month pair, compute the set of practices that improved
        3. Drop empty sets, keeping only improvement-bearing steps, in chronological order
        4. For each consecutive pair of improvement-bearing steps (prev_set, next_set),
           increment transition_matrix[a][b] for every a in prev_set, b in next_set
        5. Track overall improvement frequency for each practice

        After calling this method, use get_typical_next_practices() to query the
        learned patterns.

        Returns:
            None: Modifies internal state (self.transition_matrix and
                self.practice_improvement_freq). Sets self.learned = True.

        Note:
            - Only considers improvements (increases in practice scores)
            - Requires at least 2 improvement-bearing months per team to produce a transition
            - Transitions are learned from all available historical data
            - For time-limited sequences (backtesting), use learn_sequences_up_to_month()

        Example:
            >>> mapper = SequenceMapper(processor, practices)
            >>> mapper.learn_sequences()
            Learning improvement sequences...
            Learned 45 transition patterns
        """
        self.transition_matrix = defaultdict(Counter)
        self.practice_improvement_freq = Counter()

        teams = self.processor.get_all_teams()
        months = self.processor.get_all_months()

        for team in teams:
            history = self.processor.get_team_history(team)

            # Sort months for this team
            team_months = sorted([m for m in months if m in history])

            self._learn_team_transitions(team_months, history)

        self.learned = True

    def _learn_team_transitions(self, team_months: list, history: dict) -> None:
        """
        Build first-order Markov transitions for one team's chronological history.

        Mutates self.transition_matrix and self.practice_improvement_freq in place.

        Args:
            team_months (list): Sorted months available for this team.
            history (dict): Mapping of month -> practice score vector for this team.
        """
        # Chronological list of practice-name sets, one per improvement-bearing step
        # (steps with zero improvements are skipped, so "next" always means "the next
        # time something actually improved," not just the next calendar month)
        improved_sets = []

        for i in range(len(team_months) - 1):
            current_vector = history[team_months[i]]
            next_vector = history[team_months[i + 1]]

            improved = [
                self.practices[j]
                for j, (curr, nxt) in enumerate(zip(current_vector, next_vector))
                if nxt > curr  # Improved
            ]

            if improved:
                improved_sets.append(improved)

        for practices_improved in improved_sets:
            for practice_name in practices_improved:
                self.practice_improvement_freq[practice_name] += 1

        # Full cross-product between each improvement-bearing step and the next one;
        # no edges within a step, since simultaneous improvements have no known order
        for prev_set, next_set in zip(improved_sets, improved_sets[1:]):
            for prev_practice in prev_set:
                for next_practice in next_set:
                    self.transition_matrix[prev_practice][next_practice] += 1

    def learn_sequences_up_to_month(self, max_month: int) -> None:
        """
        Learn first-order Markov transition patterns from historical data up to (but not
        including) max_month. See learn_sequences() for the transition-construction algorithm;
        this variant restricts each team's month history to months < max_month before applying
        it, so no transition can straddle the max_month boundary. Uses caching to avoid
        recomputation.

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

            self._learn_team_transitions(team_months, history)

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
