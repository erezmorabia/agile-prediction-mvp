"""
RecommendationEngine: Generate practice recommendations using collaborative filtering and sequences.
"""

from collections import defaultdict


class RecommendationEngine:
    """Generate practice recommendations combining similarity and sequence patterns."""

    def __init__(self, similarity_engine, sequence_mapper, practices):
        """
        Initialize RecommendationEngine.

        Args:
            similarity_engine: SimilarityEngine instance
            sequence_mapper: SequenceMapper instance
            practices (list): List of practice names
        """
        self.similarity_engine = similarity_engine
        self.sequence_mapper = sequence_mapper
        self.practices = practices
        self.processor = similarity_engine.processor

    def recommend(
        self,
        target_team: str,
        current_month: int,
        top_n: int = 2,
        k_similar: int = 19,
        allow_first_three_months: bool = False,
        similarity_weight: float = 0.6,
        similar_teams_lookahead_months: int = 3,
        recent_improvements_months: int = 3,
        min_similarity_threshold: float = 0.75,
    ) -> list:
        """
        Generate practice recommendations for a team using collaborative filtering and sequence learning.

        This is the core recommendation algorithm that combines two complementary approaches:
        1. Collaborative Filtering: Find teams similar to the target team and see what they improved
        2. Sequence Learning: Use learned patterns of which practices typically follow others

        Algorithm Details:
        Step 0: Learn sequences up to current_month (sliding window, prevents data leakage)
        Step 1: Find K most similar teams by comparing target team's state at current_month
                against all other teams' states at all past months (months < current_month).
                Uses cosine similarity on practice maturity vectors.
        Step 2: For each similar team, check what practices they improved in the next 1-3 months
                (but only if those months are <= current_month to prevent data leakage).
                Weight improvements by similarity score and improvement magnitude.
        Step 3: Apply sequence boost - if target team recently improved practices (in last N months),
                boost practices that typically follow those improved practices based on learned sequences.
        Step 4: Combine similarity scores and sequence scores with weighted average:
                final_score = similarity_weight * normalized_similarity_score +
                             (1 - similarity_weight) * normalized_sequence_score
        Step 5: Filter out practices already at maximum maturity (normalized score >= 1.0)
        Step 6: Rank by combined score and return top N recommendations

        IMPORTANT: This method only uses data from months <= current_month to prevent
        data leakage. Future months are only used for validation, not prediction.

        Args:
            target_team (str): Name of the team to generate recommendations for.
                Must exist in the processor's team list.
            current_month (int): Current month in yyyymmdd format (e.g., 20200107).
                Used as baseline - recommendations predict what to improve next.
                Must exist in the team's history.
            top_n (int, optional): Number of recommendations to return. Defaults to 2.
            k_similar (int, optional): Number of similar teams to consider for collaborative
                filtering. Higher values use more teams but may include less similar ones.
                Defaults to 19.
            allow_first_three_months (bool, optional): Allow predictions when current_month
                is in the first 3 months globally. Used for backtesting scenarios.
                Defaults to False.
            similarity_weight (float, optional): Weight for similarity-based scores vs sequence
                scores. Range 0.0-1.0. 0.6 means 60% weight on similarity, 40% on sequences.
                Defaults to 0.6.
            similar_teams_lookahead_months (int, optional): How many months ahead to check
                for improvements by similar teams. Higher values capture delayed improvements
                but may be less relevant. Defaults to 3.
            recent_improvements_months (int, optional): How many months back to check for
                recent improvements by the target team to trigger sequence boosts.
                Defaults to 3.
            min_similarity_threshold (float, optional): Minimum cosine similarity (0.0-1.0)
                required for a team to be considered "similar". Filters out dissimilar teams.
                0.0 = no filter, 0.75 = only very similar teams. Defaults to 0.75.

        Returns:
            list: List of tuples, each containing:
                - practice_name (str): Name of the recommended practice
                - score (float): Recommendation score (0.0-1.0, higher = stronger recommendation)
                - current_level (float): Team's current normalized maturity level (0.0-1.0)
                Sorted by score in descending order (best recommendations first).

        Raises:
            ValueError: If target_team not found, current_month not in team's history,
                or if current_month is in first month globally (unless allow_first_three_months=True).

        Example:
            >>> recommendations = recommender.recommend("Team Alpha", 20200107, top_n=3)
            >>> for practice, score, level in recommendations:
            ...     print(f"{practice}: {score:.3f} (current: {level:.2f})")
            Practice A: 0.850 (current: 0.33)
            Practice B: 0.720 (current: 0.50)
            Practice C: 0.650 (current: 0.17)

        Note:
            - Scores are normalized separately for similarity and sequence components before combining
            - Practices at maximum maturity (normalized >= 1.0) are automatically excluded
            - The algorithm prevents data leakage by only using historical data
            - Similar teams are deduplicated (one entry per team, highest similarity kept)
        """
        # Get target team's current state
        history = self.processor.get_team_history(target_team)
        months_list = sorted(history.keys())

        if current_month not in history:
            raise ValueError(f"Team '{target_team}' has no data for month {current_month}")

        # Validate minimum data requirement: need at least 2 months of history
        # Month 2 can be used as baseline to predict month 3, but month 1 cannot
        # Exception: allow_first_three_months=True for backtesting scenarios
        if not allow_first_three_months:
            all_months = sorted(self.processor.get_all_months())
            if len(all_months) >= 2:
                first_month = set(all_months[:1])  # Only filter month 1
                if current_month in first_month:
                    raise ValueError(
                        f"Need at least 2 months of historical data. "
                        f"Month to predict starts from month 3 onwards. "
                        f"Baseline month {current_month} is the first month."
                    )

        current_scores = history[current_month]
        current_idx = months_list.index(current_month)

        # Step 0: Learn sequences up to current_month (using sliding window)
        # This ensures sequences are only learned from months < current_month
        self.sequence_mapper.learn_sequences_up_to_month(current_month)

        # Step 1: Find similar teams
        similar_teams = self.similarity_engine.find_similar_teams(
            target_team, current_month, k=k_similar, min_similarity=min_similarity_threshold
        )

        if not similar_teams:
            raise ValueError(f"No similar teams found for '{target_team}'")

        # Step 2: See what similar teams improved
        # Note: similar_teams now returns (team_name, similarity_score, historical_month)
        # IMPORTANT: Only use past data - check what similar teams improved from their
        # historical_month to THEIR next 1-N months, but only if those months are <= current_month
        # (not in the future). This prevents data leakage and captures improvements that don't
        # happen every month.
        similarity_scores = defaultdict(float)  # Track similarity-based scores separately

        for similar_team, similarity_weight, historical_month in similar_teams:
            try:
                similar_history = self.processor.get_team_history(similar_team)

                # Get the similar team's state when they were similar (at historical_month)
                if historical_month not in similar_history:
                    continue

                similar_state_at_historical = similar_history[historical_month]

                # Get the similar team's months in chronological order
                similar_months = sorted(similar_history.keys())
                hist_idx = similar_months.index(historical_month)

                # Check up to 3 months ahead (but only use months <= current_month)
                # This captures improvements that don't happen every month
                max_months_ahead = 3
                best_improvements = {}  # Track max improvement per practice across 1-3 months

                for months_ahead in range(1, max_months_ahead + 1):
                    if hist_idx + months_ahead >= len(similar_months):
                        break  # No more months available

                    similar_future_month = similar_months[hist_idx + months_ahead]

                    # CRITICAL: Only use improvements that occurred before or at current_month
                    # This ensures we only use past data for predictions (no data leakage)
                    if similar_future_month > current_month:
                        break  # Stop checking future months

                    similar_state_at_future = similar_history[similar_future_month]

                    # Find what this team improved from historical_month to this future month
                    for j, (hist_state, future_state) in enumerate(
                        zip(similar_state_at_historical, similar_state_at_future)
                    ):
                        if future_state > hist_state:  # Improved
                            practice_name = self.practices[j]
                            improvement_magnitude = future_state - hist_state

                            # Keep the maximum improvement across all checked months (1-3)
                            if (
                                practice_name not in best_improvements
                                or improvement_magnitude > best_improvements[practice_name]
                            ):
                                best_improvements[practice_name] = improvement_magnitude

                # Add the best improvements found (weighted by similarity)
                for practice_name, improvement_magnitude in best_improvements.items():
                    similarity_scores[practice_name] += similarity_weight * improvement_magnitude
            except (KeyError, ValueError, IndexError):
                continue

        # Step 3: Add sequence boost
        # If target recently improved something (in the last N months), boost related practices
        # Note: sequences are now learned up to current_month, so this uses time-limited sequences
        # Check the last N months (or as many as available) to find recent improvements
        recently_improved_practices = set()  # Track practices improved in last N months to avoid double-counting

        # Check up to N months back (or as many as available)
        months_to_check = min(recent_improvements_months, current_idx)
        for months_back in range(1, months_to_check + 1):
            if current_idx - months_back < 0:
                break

            past_month = months_list[current_idx - months_back]
            past_scores = history[past_month]

            # Compare past month to current month to find improvements
            for j, (past, curr) in enumerate(zip(past_scores, current_scores)):
                if curr > past:  # Improved from past_month to current_month
                    practice_name = self.practices[j]
                    # Only add if we haven't already seen this improvement
                    # (practices improved in multiple months will only be counted once)
                    if practice_name not in recently_improved_practices:
                        recently_improved_practices.add(practice_name)

        # Apply sequence patterns for all recently improved practices
        sequence_scores = defaultdict(float)  # Track sequence-based scores separately
        for recently_improved in recently_improved_practices:
            # Get typical next practices (from sequences learned up to current_month)
            try:
                for next_practice, transition_prob in self.sequence_mapper.get_typical_next_practices(
                    recently_improved, top_n=3
                ):
                    sequence_scores[next_practice] += transition_prob
            except ValueError:
                # Sequences not learned yet (shouldn't happen, but handle gracefully)
                pass

        # Step 4: Combine similarity and sequence scores with explicit weights
        # Normalize each component separately, then combine with weights
        practices_scores = defaultdict(float)

        # Normalize similarity scores
        max_similarity = max(similarity_scores.values()) if similarity_scores else 1.0
        normalized_similarity = {
            p: (s / max_similarity if max_similarity > 0 else 0.0) for p, s in similarity_scores.items()
        }

        # Normalize sequence scores
        max_sequence = max(sequence_scores.values()) if sequence_scores else 1.0
        normalized_sequence = {p: (s / max_sequence if max_sequence > 0 else 0.0) for p, s in sequence_scores.items()}

        # Combine with weights
        all_practices = set(normalized_similarity.keys()) | set(normalized_sequence.keys())
        for practice in all_practices:
            sim_score = normalized_similarity.get(practice, 0.0)
            seq_score = normalized_sequence.get(practice, 0.0)
            practices_scores[practice] = similarity_weight * sim_score + (1.0 - similarity_weight) * seq_score

        # Step 5: Filter and rank
        recommendations = []

        # Find max score for final normalization (should be <= 1.0, but normalize to be safe)
        max_score = max(practices_scores.values()) if practices_scores else 1.0

        for practice, score in practices_scores.items():
            practice_idx = self.practices.index(practice)
            current_level = float(current_scores[practice_idx])

            # Skip if already maxed out (score >= 1.0 since normalized to 0-1)
            if current_level >= 1.0:
                continue

            # Normalize score to 0-1 range
            normalized_score = score / max_score if max_score > 0 else 0.0

            recommendations.append((practice, normalized_score, current_level))

        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:top_n]

    def get_recommendation_explanation(
        self, target_team: str, current_month: int, practice: str, recent_improvements_months: int = 3
    ) -> dict:
        """
        Explain why a practice was recommended.

        IMPORTANT: This method only uses data from months <= current_month to prevent
        data leakage. Future months are only used for validation, not prediction.

        Args:
            target_team (str): Team name
            current_month (int): Current month (yyyymmdd format)
            practice (str): Practice name
            recent_improvements_months (int): Months to check back for recent improvements (default 3)

        Returns:
            dict: Explanation details
        """
        # Learn sequences up to current_month (using sliding window)
        # This ensures sequences are only learned from months < current_month
        self.sequence_mapper.learn_sequences_up_to_month(current_month)

        # Get team history to check for recent improvements
        history = self.processor.get_team_history(target_team)
        if current_month not in history:
            raise ValueError(f"Team '{target_team}' has no data for month {current_month}")

        months_list = sorted(history.keys())
        current_idx = months_list.index(current_month)
        current_scores = history[current_month]

        # Check if sequence boost applies (similar to recommend method)
        recently_improved_practices = set()
        months_to_check = min(recent_improvements_months, current_idx)
        for months_back in range(1, months_to_check + 1):
            if current_idx - months_back < 0:
                break

            past_month = months_list[current_idx - months_back]
            past_scores = history[past_month]

            # Compare past month to current month to find improvements
            for j, (past, curr) in enumerate(zip(past_scores, current_scores)):
                if curr > past:  # Improved from past_month to current_month
                    practice_name = self.practices[j]
                    if practice_name not in recently_improved_practices:
                        recently_improved_practices.add(practice_name)

        # Check if the target practice gets a sequence boost from recently improved practices
        has_sequence_boost = False
        for recently_improved in recently_improved_practices:
            try:
                for next_practice, transition_prob in self.sequence_mapper.get_typical_next_practices(
                    recently_improved, top_n=3
                ):
                    if next_practice == practice:
                        has_sequence_boost = True
                        break
                if has_sequence_boost:
                    break
            except ValueError:
                pass

        similar_teams = self.similarity_engine.find_similar_teams(target_team, current_month, k=5)

        # Track which similar teams improved this practice and when
        # IMPORTANT: Only use past data - check what similar teams improved from their
        # historical_month to THEIR next 1-3 months, but only if those months are <= current_month
        # (not in the future). This prevents data leakage and captures improvements that don't
        # happen every month.
        improved_teams = []
        improved_count = 0

        # Note: similar_teams now returns (team_name, similarity_score, historical_month)
        # Use a dict to deduplicate by (team, month) - keep entry with highest similarity
        improved_teams_dict = {}

        for similar_team, similarity_score, historical_month in similar_teams:
            try:
                similar_history = self.processor.get_team_history(similar_team)

                # Check if this similar team has data at historical_month
                if historical_month not in similar_history:
                    continue

                # Get the similar team's months in chronological order
                similar_months = sorted(similar_history.keys())
                hist_idx = similar_months.index(historical_month)

                # Check up to 3 months ahead (but only use months <= current_month)
                # This captures improvements that don't happen every month
                max_months_ahead = 3
                practice_idx = self.practices.index(practice)
                hist_state = similar_history[historical_month][practice_idx]

                for months_ahead in range(1, max_months_ahead + 1):
                    if hist_idx + months_ahead >= len(similar_months):
                        break  # No more months available

                    similar_future_month = similar_months[hist_idx + months_ahead]

                    # CRITICAL: Only use improvements that occurred before or at current_month
                    # This ensures we only use past data for predictions (no data leakage)
                    if similar_future_month > current_month:
                        break  # Stop checking future months

                    # Check if this team improved the practice from historical_month to this future month
                    future_state = similar_history[similar_future_month][practice_idx]

                    if future_state > hist_state:
                        # Use (team, month) as key to deduplicate
                        key = (similar_team, similar_future_month)

                        # If we haven't seen this team/month combo, or this one has higher similarity, keep it
                        if key not in improved_teams_dict or similarity_score > improved_teams_dict[key]["similarity"]:
                            improved_teams_dict[key] = {
                                "team": similar_team,
                                "month": similar_future_month,
                                "similarity": float(similarity_score),
                                "similar_at_month": historical_month,
                            }
                        # Found an improvement, no need to check further months for this team
                        break
            except (KeyError, ValueError, IndexError):
                continue

        # Convert dict to list
        improved_teams = list(improved_teams_dict.values())
        improved_count = len(improved_teams)

        # Count total similar teams checked (regardless of whether they improved)
        total_similar_teams_checked = len(similar_teams)

        # Get sequence info (from sequences learned up to current_month)
        try:
            sequence_info = self.sequence_mapper.get_typical_next_practices(practice, top_n=1)
        except ValueError:
            # Sequences not learned yet (shouldn't happen, but handle gracefully)
            sequence_info = []

        return {
            "practice": practice,
            "similar_teams_improved": improved_count,
            "total_similar_teams_checked": total_similar_teams_checked,
            "similar_teams_list": improved_teams,
            "typical_sequence_follows": sequence_info[0][0] if sequence_info else None,
            "has_sequence_boost": has_sequence_boost,
        }
