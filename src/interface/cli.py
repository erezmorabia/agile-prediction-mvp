"""
CLIInterface: Command-line interface for the recommendation system.
"""

from .formatter import OutputFormatter


class CLIInterface:
    """Provide interactive command-line interface for recommendations."""

    def __init__(self, recommender_engine, processor):
        """
        Initialize CLIInterface.

        Args:
            recommender_engine: RecommendationEngine instance
            processor: DataProcessor instance
        """
        # The RecommendationEngine used to generate practice recommendations.
        self.recommender = recommender_engine

        # Gives access to team histories, used to look up teams/months for menu options.
        self.processor = processor

        # Formats results for display in the terminal.
        self.formatter = OutputFormatter()

        # Filled in later by main.py with details about missing/dropped data,
        # shown to the user in the statistics menu option.
        self.missing_values_details = None

    def run(self) -> None:
        """
        Run the interactive command-line interface.

        Displays a menu-driven interface allowing users to:
        1. Get recommendations for specific teams
        2. Run backtest validation
        3. View system statistics
        4. View learned improvement sequences
        5. Exit

        The interface runs in a loop until the user selects option 5 (Exit).
        All operations use the initialized recommender and processor instances.
        Both recommendations and the backtest use the same global two-month adaptive
        blend policy engine as the web interface - there are no user-adjustable model
        parameters and no static "optimal configuration" search.

        Returns:
            None: Runs interactively until user exits.

        Note:
            - Missing values details are displayed if available (set by main.py)
            - All user input is validated before processing
            - Errors are caught and displayed with helpful messages
        """
        self._show_header()

        # Keep showing the menu and handling one choice at a time, until the user exits.
        while True:
            self._show_menu()
            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                self._get_recommendations()
            elif choice == "2":
                self._validate_recommendations()
            elif choice == "3":
                self._show_system_stats()
            elif choice == "4":
                self._show_improvement_sequences()
            elif choice == "5":
                print("\nGoodbye!")
                break
            else:
                print("Error: Invalid choice. Please try again.")

    def _show_header(self) -> None:
        """
        Display the application header banner.

        Shows the system name and description at startup.

        Returns:
            None: Prints header to stdout.
        """
        print("\n" + "=" * 60)
        print("AGILE PRACTICE PREDICTION SYSTEM")
        print("MVP - Collaborative Filtering + Sequence Learning")
        print("=" * 60)

    def _show_menu(self) -> None:
        """
        Display the main menu options.

        Shows numbered options for all available operations.

        Returns:
            None: Prints menu to stdout.
        """
        print("\n" + "-" * 60)
        print("MAIN MENU")
        print("-" * 60)
        print("1. Get Recommendations for a Team")
        print("2. Validate Recommendations (Backtest)")
        print("3. View System Statistics")
        print("4. View Improvement Sequences")
        print("5. Exit")
        print("-" * 60)

    def _find_teams_with_improvements(self) -> list[tuple[str, int, int, int]]:
        """
        Find teams and months where improvements were observed in the subsequent recorded month.

        Scans all teams and identifies consecutive month pairs where practices improved.
        Used to filter teams for recommendation display (shows teams with validation data).

        Returns:
            List[Tuple[str, int, int, int]]: List of tuples, each containing:
                - team (str): Team name
                - month (int): Baseline month (yyyymmdd format)
                - next_month (int): Month where improvements occurred (yyyymmdd format)
                - num_improvements (int): Number of practices that improved
            Sorted by team name and month.

        Note:
            - Only considers consecutive months (no gaps)
            - Counts any practice with increased score as an improvement
            - Used to identify teams with validation data available
        """
        teams_with_improvements = []
        all_teams = self.processor.get_all_teams()

        # Check every team, one at a time, for month-to-month improvements.
        for team in all_teams:
            history = self.processor.get_team_history(team)
            months = sorted(history.keys())

            # Check each month (except the last one, which has no subsequent recorded month)
            for i in range(len(months) - 1):
                current_month = months[i]
                next_month = months[i + 1]

                current_vector = history[current_month]
                next_vector = history[next_month]

                # Count improvements
                improvements = []
                # Compare this month's scores to the subsequent recorded month's, practice by practice.
                for j, (curr, nxt) in enumerate(zip(current_vector, next_vector)):
                    if nxt > curr:
                        improvements.append(self.recommender.practices[j])

                if improvements:
                    teams_with_improvements.append((team, current_month, next_month, len(improvements)))

        return teams_with_improvements

    def _get_recommendations(self) -> None:
        """
        Interactive workflow to get recommendations for a specific team.

        Guides the user through:
        1. Selecting a team (with option to filter by teams with improvements)
        2. Selecting a month to predict (must be a valid prediction month)
        3. Generating recommendations using that month's globally selected policy
           (the same PolicyEngine the web interface uses)
        4. Validating recommendations against actual improvements
        5. Showing practice maturity profile

        The validation checks improvements in a 3-snapshot window (predicted month,
        next observed snapshot, following observed snapshot) to account for adoption
        timelines.

        Returns:
            None: Prints results interactively. Returns early on error.

        Note:
            - Month to predict must be a valid prediction month (global index 3+)
            - Recommendations are generated using the team's own baseline snapshot
            - Validation accuracy is only calculated if improvements occurred
            - Practice profile shows current maturity levels grouped by level (0-3)
        """
        print("\n" + "=" * 60)
        print("GET RECOMMENDATIONS")
        print("=" * 60)

        engine = self.recommender.policy_engine
        valid_prediction_months = set(engine.prediction_months())

        try:
            # Find teams with improvements
            teams_with_improvements = self._find_teams_with_improvements()

            if not teams_with_improvements:
                print("\nWarning: No teams found with subsequently observed improvements")
                print("   You can still get recommendations, but validation won't be available")
                use_filter = False
            else:
                print(f"\nFound {len(teams_with_improvements)} team/month combinations with improvements")
                print("   (These allow validation against subsequently observed improvements)")
                use_filter = input("\nShow only teams with improvements? (y/n, default=y): ").strip().lower()
                use_filter = use_filter != "n"

            if use_filter and teams_with_improvements:
                # Group by team and show options
                teams_dict = {}
                # Group the flat improvement list by team name.
                for team, month, next_month, num_improvements in teams_with_improvements:
                    teams_dict.setdefault(team, []).append((month, next_month, num_improvements))

                # Sort teams by number of improvement months (descending)
                teams_sorted = sorted(teams_dict.items(), key=lambda x: (-len(x[1]), x[0]))

                print(f"\nTeams with improvements ({len(teams_sorted)} teams):")
                # Print one numbered line per team, up to the first 15.
                for i, (team, months_list) in enumerate(teams_sorted[:15]):
                    months_str = ", ".join([f"{m[0]}→{m[1]}({m[2]} imp.)" for m in months_list])
                    print(f"  {i + 1:2d}. {team}: {months_str}")
                if len(teams_sorted) > 15:
                    print(f"  ... and {len(teams_sorted) - 15} more teams")

                # Let user choose by number or name
                choice = input("\nEnter team name or number: ").strip()

                # Try to parse as number
                try:
                    team_idx = int(choice) - 1
                    team_name = teams_sorted[team_idx][0] if 0 <= team_idx < len(teams_sorted) else choice
                except ValueError:
                    team_name = choice

                if team_name not in teams_dict:
                    print(f"Error: Team '{team_name}' not found or has no improvements")
                    return

                # Show months to predict (only valid prediction months)
                months_list = [(m, n, num) for m, n, num in teams_dict[team_name] if m in valid_prediction_months]

                if not months_list:
                    print(f"Error: Team '{team_name}' has no months available for prediction")
                    print("   Need at least 3 months of history before the prediction month.")
                    return

                print(f"\nAvailable months to predict for {team_name} (with improvements):")
                # Print one numbered line per selectable month.
                for i, (month, next_month, num_imp) in enumerate(months_list):
                    print(f"  {i + 1}. Month to predict: {month} ({num_imp} improvements occurred)")

                month_choice = input("\nEnter month number or date (yyyymmdd): ").strip()

                # Try to parse as number
                try:
                    month_idx = int(month_choice) - 1
                    month_to_predict = months_list[month_idx][0] if 0 <= month_idx < len(months_list) else int(month_choice)
                except ValueError:
                    month_to_predict = int(month_choice)

                history = self.processor.get_team_history(team_name)
                if month_to_predict not in history:
                    print(f"Error: No data for team on month {month_to_predict}")
                    return
            else:
                # Original behavior - show all teams
                all_teams = self.processor.get_all_teams()

                # Sort teams by number of months they have data for (descending)
                teams_with_data = [(team, len(self.processor.get_team_history(team))) for team in all_teams]
                teams_with_data.sort(key=lambda x: (-x[1], x[0]))
                teams = [team for team, _ in teams_with_data]

                print(f"\nAvailable teams ({len(teams)} total, sorted by data availability):")
                # Print one line per team, up to the first 10.
                for i, team in enumerate(teams[:10]):
                    print(f"  {team} ({teams_with_data[i][1]} months)")
                if len(teams) > 10:
                    print(f"  ... and {len(teams) - 10} more")

                team_name = input("\nEnter team name: ").strip()

                if team_name not in teams:
                    print(f"Error: Team '{team_name}' not found")
                    return

                history = self.processor.get_team_history(team_name)
                all_months = sorted(history.keys())
                months_to_predict = [m for m in all_months if m in valid_prediction_months]

                if not months_to_predict:
                    print(f"Error: Team '{team_name}' has no months available for prediction")
                    print("   Need at least 3 months of history before the prediction month.")
                    return

                print(f"\nAvailable months to predict for {team_name} (starting from month 4):")
                print(f"   {months_to_predict}")
                if len(all_months) > len(months_to_predict):
                    filtered_out = [m for m in all_months if m not in months_to_predict]
                    print(f"   (Months {filtered_out} excluded - need at least 3 months of history)")

                month_to_predict = int(input("Enter month to predict (yyyymmdd): ").strip())

                if month_to_predict not in history:
                    print(f"Error: No data for team on month {month_to_predict}")
                    return

            if month_to_predict not in valid_prediction_months:
                print("Error: Month to predict must be a valid prediction month.")
                print(f"   Month {month_to_predict} is not eligible (need at least 3 months of history).")
                return

            if engine.baseline_month_for(team_name, month_to_predict) is None:
                print(f"Error: Cannot predict month {month_to_predict} - no previous month available")
                return

            # Get recommendations using this month's globally selected policy - the same
            # PolicyEngine instance the web interface and the backtest use.
            print(f"\nGenerating recommendations for month {month_to_predict}...")
            result = self.recommender.recommend(team_name, month_to_predict)

            selected = result.selected_policy
            policy = selected.policy
            print("\nSelected policy for this month:")
            if selected.is_bootstrap:
                print("   Bootstrap (no completed prior months yet): 100% popularity")
                print(f"   Popularity recency: {policy.recency_weight * 100:.0f}% recent / {100 - policy.recency_weight * 100:.0f}% historical")
            else:
                print(
                    f"   Similarity {policy.similarity_weight * 100:.0f}% · Sequence {policy.sequence_weight * 100:.0f}% "
                    f"· Popularity {policy.popularity_weight * 100:.0f}%"
                )
                print(
                    f"   Peer pool: {policy.peer_count} teams, min similarity {policy.min_similarity * 100:.0f}% · "
                    f"Popularity recency: {policy.recency_weight * 100:.0f}% recent"
                )
                print(f"   Selected from {len(selected.completed_prior_months)} completed prior month(s)")
            print("   Fixed component windows: 2 observed snapshots (similarity look-ahead and sequence recency)")

            if result.insufficient_practices:
                print(f"\nWarning: Team '{team_name}' has fewer than two practices left to improve.")
                return

            prev_month = result.baseline_month

            # Check for actual improvements in the predicted month and next 2 months
            history = self.processor.get_team_history(team_name)
            months = sorted(history.keys())
            month_to_predict_idx = months.index(month_to_predict)
            prev_vector = history[prev_month]
            predicted_vector = history[month_to_predict]

            month_after = None
            month_after_2 = None
            actual_improvements = []  # List of (practice_name, improvement, improved_in_months)

            # Get what actually improved in the predicted month
            improvements_month1 = {}
            # Compare the baseline month to the predicted month, practice by practice.
            for j, (prev, pred) in enumerate(zip(prev_vector, predicted_vector)):
                if pred > prev:
                    improvements_month1[self.recommender.practices[j]] = pred - prev

            # Check if month_after exists and get improvements there too
            improvements_month2 = {}
            if month_to_predict_idx + 1 < len(months):
                month_after = months[month_to_predict_idx + 1]
                month_after_vector = history[month_after]

                # Same comparison, one month further out.
                for j, (prev, after) in enumerate(zip(prev_vector, month_after_vector)):
                    if after > prev:
                        improvements_month2[self.recommender.practices[j]] = after - prev

            # Check if month_after_2 exists and get improvements there too (third month ahead)
            improvements_month3 = {}
            if month_to_predict_idx + 2 < len(months):
                month_after_2 = months[month_to_predict_idx + 2]
                month_after_2_vector = history[month_after_2]

                # Same comparison, two months further out.
                for j, (prev, after2) in enumerate(zip(prev_vector, month_after_2_vector)):
                    if after2 > prev:
                        improvements_month3[self.recommender.practices[j]] = after2 - prev

            # Combine improvements from all 3 months (predicted month, month_after, month_after_2)
            all_practices = set(improvements_month1) | set(improvements_month2) | set(improvements_month3)
            # Merge the 3 months' worth of improvements into one entry per practice,
            # keeping whichever month showed the biggest improvement.
            for practice_name in all_practices:
                improved_in_months = []
                improvement = 0.0

                if practice_name in improvements_month1:
                    improved_in_months.append(month_to_predict)
                    improvement = max(improvement, improvements_month1[practice_name])

                if practice_name in improvements_month2:
                    improved_in_months.append(month_after)
                    improvement = max(improvement, improvements_month2[practice_name])

                if practice_name in improvements_month3:
                    improved_in_months.append(month_after_2)
                    improvement = max(improvement, improvements_month3[practice_name])

                actual_improvements.append((practice_name, improvement, improved_in_months))

            # Display recommendations
            print(f"\nTop {len(result.practices)} Recommendations for {team_name} (Predicting month {month_to_predict}):")
            print("-" * 60)

            print("\nUnderstanding the Output:")
            print("   • Current Level: Your team's maturity (0-1 scale, where 0.33=Level 1, 0.67=Level 2, 1.0=Level 3)")
            print("   • Recommendation Score: How strongly we recommend this (higher = more evidence)")
            print("   • Score blends similarity, sequence, and time-aware popularity evidence (see policy above)")

            recommended_practices = list(result.practices)

            # Print full detail (score, level, why, validation) for each recommendation.
            for i, practice in enumerate(result.practices, 1):
                score = result.scores[practice]
                current_level = result.current_levels[practice]
                # Determine level number (0, 1, 2, or 3)
                if current_level < 0.17:
                    level_num, level_description = 0, "Not implemented"
                elif current_level < 0.5:
                    level_num, level_description = 1, "Basic level"
                elif current_level < 0.84:
                    level_num, level_description = 2, "Intermediate level"
                else:
                    level_num, level_description = 3, "Mature level"

                level_display = f"Level {level_num} ({level_description})"

                # Get explanation with similar teams details
                explanation = self.recommender.get_recommendation_explanation(team_name, month_to_predict, practice)
                similar_count = explanation.get("similar_teams_improved", 0)
                similar_teams_list = explanation.get("similar_teams_list", [])
                no_peers = explanation.get("no_similar_teams_found", False)
                has_sequence_boost = explanation.get("has_sequence_boost", False)

                # Check whether this practice showed a subsequently observed improvement.
                actually_improved = False
                improvement_amount = 0.0
                improved_in_months = []
                # Look for this recommended practice among what actually improved.
                for actual_practice, improvement, improved_in in actual_improvements:
                    if actual_practice == practice:
                        actually_improved = True
                        improvement_amount = improvement
                        improved_in_months = improved_in
                        break

                print(f"\n{i}. {practice}")
                print(f"   Recommendation Score: {score:.3f} (range: 0.0-1.0, higher = stronger)")
                print(f"   Current Level: {level_display}")
                if similar_count > 0 and has_sequence_boost:
                    print(f"   Why: {similar_count} similar team(s) improved this practice + sequence patterns")
                elif similar_count > 0:
                    print(f"   Why: {similar_count} similar team(s) improved this practice")
                elif has_sequence_boost:
                    print("   Why: Recommended based on improvement sequences")
                elif no_peers:
                    print("   Why: No comparable team was found; recommended based on organization-wide popularity and improvement sequences")
                else:
                    print("   Why: Recommended based on organization-wide popularity")
                if similar_teams_list:
                    # Print one line per similar team that improved this practice.
                    for st in similar_teams_list:
                        similar_at = st.get("similar_at_month", st["month"])
                        if similar_at != st["month"]:
                            print(
                                f"      • {st['team']} (similar at {similar_at}) improved in {st['month']} ({(st['similarity'] * 100):.0f}% similar)"
                            )
                        else:
                            print(
                                f"      • {st['team']} improved in {st['month']} ({(st['similarity'] * 100):.0f}% similar)"
                            )

                # Show validation
                if actually_improved:
                    improvement_pct = improvement_amount * 100
                    if len(improved_in_months) == 3:
                        print(
                            f"   Validated: Actually improved in month {improved_in_months[0]}, {improved_in_months[1]}, AND {improved_in_months[2]} (+{improvement_pct:.1f}%)"
                        )
                    elif len(improved_in_months) == 2:
                        print(
                            f"   Validated: Actually improved in month {improved_in_months[0]} AND {improved_in_months[1]} (+{improvement_pct:.1f}%)"
                        )
                    else:
                        print(
                            f"   Validated: Actually improved in month {improved_in_months[0]} (+{improvement_pct:.1f}%)"
                        )
                else:
                    validation_text = f"month {month_to_predict}"
                    if month_after:
                        validation_text += f", {month_after}"
                    if month_after_2:
                        validation_text += f", or {month_after_2}"
                    print(f"   Warning: Validation: Not improved in {validation_text}")

            print("\n" + "-" * 60)

            # Show validation summary
            validation_months_text = f"Month {month_to_predict}"
            if month_after:
                validation_months_text += f", {month_after}"
            if month_after_2:
                validation_months_text += f", and {month_after_2}"
            print(f"\nValidation Summary (checking improvements in {validation_months_text}):")
            if actual_improvements:
                print(f"   Practices that actually improved: {len(actual_improvements)}")
                # Print one line per practice that actually improved, flagging
                # whether it was one of the recommendations.
                for practice, improvement, improved_in in actual_improvements:
                    improvement_pct = improvement * 100
                    status = "Recommended" if practice in recommended_practices else "Not recommended"
                    if len(improved_in) == 3:
                        print(
                            f"     • {practice}: +{improvement_pct:.1f}% (improved in {improved_in[0]}, {improved_in[1]}, AND {improved_in[2]}) {status}"
                        )
                    elif len(improved_in) == 2:
                        print(
                            f"     • {practice}: +{improvement_pct:.1f}% (improved in {improved_in[0]} AND {improved_in[1]}) {status}"
                        )
                    else:
                        print(f"     • {practice}: +{improvement_pct:.1f}% (improved in {improved_in[0]}) {status}")

                # Calculate accuracy only if there were actual improvements
                # If no improvements occurred, don't calculate accuracy - this isn't a model failure,
                # it just means the team didn't improve anything in the validation window
                recommended_set = set(recommended_practices)
                actual_set = {p for p, _, _ in actual_improvements}
                hits = len(recommended_set & actual_set)

                if recommended_set:
                    accuracy = hits / len(recommended_set) * 100
                    print(f"\n   Recommendation Accuracy: {hits}/{len(recommended_set)} = {accuracy:.1f}%")
            else:
                print(f"   Warning: No practices improved in {validation_months_text}")
                print("\n   Note: Accuracy is not calculated when no improvements occurred.")
                print("      This is not a model failure - it just means the team didn't improve")
                print("      anything in the validation window.")

            # Display practice maturity profile
            print("\n" + "=" * 60)
            print("\nCurrent Practice Maturity Profile")
            print("-" * 60)
            practice_profile = self._get_practice_profile(team_name, prev_month)

            # Print each maturity level's practices as its own section.
            for level in [0, 1, 2, 3]:
                practices = practice_profile[level]
                if practices:
                    level_name = ["Not implemented", "Basic level", "Intermediate level", "Advanced level"][level]

                    print(f"\nLevel {level} ({level_name}): {len(practices)} practices")
                    # Display practices in columns for better readability
                    practices_sorted = sorted(practices)
                    # Print 3 practice names per line.
                    for i in range(0, len(practices_sorted), 3):
                        chunk = practices_sorted[i : i + 3]
                        print(f"   {', '.join(chunk)}")

            print("\n" + "=" * 60)

        except ValueError as e:
            print(f"Error: {str(e)}")
        except Exception as e:
            print(f"Error: Unexpected error: {str(e)}")

    def _get_practice_profile(self, team_name: str, current_month: int) -> dict[int, list[str]]:
        """
        Get practice maturity profile for a team at a specific month.

        Categorizes all practices into 4 maturity levels based on their normalized scores.
        Practices are grouped and sorted alphabetically within each level.

        Maturity Levels:
        - Level 0: Not implemented (< 0.17 normalized, < 0.5 original)
        - Level 1: Basic level (0.17-0.5 normalized, 0.5-1.5 original)
        - Level 2: Intermediate level (0.5-0.84 normalized, 1.5-2.5 original)
        - Level 3: Mature level (>= 0.84 normalized, >= 2.5 original)

        Args:
            team_name (str): Name of the team to get profile for.
                Must exist in the processor's team list.
            current_month (int): Month in yyyymmdd format (e.g., 20200107).
                Must exist in the team's history.

        Returns:
            Dict[int, List[str]]: Dictionary with keys 0, 1, 2, 3, each containing
                a sorted list of practice names at that maturity level.
                Returns empty lists for all levels if team/month not found.

        Example:
            >>> profile = cli._get_practice_profile("Team Alpha", 20200107)
            >>> profile[0]  # Not implemented practices
            ['Practice A', 'Practice B']
            >>> profile[3]  # Mature practices
            ['Practice C']
        """
        history = self.processor.get_team_history(team_name)
        if current_month not in history:
            return {0: [], 1: [], 2: [], 3: []}

        practice_vector = history[current_month]
        profile = {0: [], 1: [], 2: [], 3: []}

        # Sort each practice's score into its maturity level bucket.
        for j, normalized_value in enumerate(practice_vector):
            practice_name = self.recommender.practices[j]
            # Convert normalized (0-1) back to original scale (0-3)
            original_value = normalized_value * 3

            # Group by level
            if normalized_value < 0.17:  # < 0.5 original
                profile[0].append(practice_name)
            elif normalized_value < 0.5:  # 0.5-1.5 original
                profile[1].append(practice_name)
            elif normalized_value < 0.84:  # 1.5-2.5 original
                profile[2].append(practice_name)
            else:  # >= 2.5 original
                profile[3].append(practice_name)

        return profile

    def _validate_recommendations(self) -> None:
        """
        Run the global two-month adaptive blend backtest and display results.

        Executes a full backtest validation using the BacktestEngine, which tests
        the recommendation system on historical data using a time-series cross-validation
        approach. There are no user-adjustable model parameters - the monthly policy,
        selected from earlier completed prediction months, is the only configuration
        authority.

        Returns:
            None: Prints results to stdout. Returns early on error.

        Note:
            - Requires at least 4 months of data
            - Shows per-month results plus separate primary and sensitivity aggregates
            - Primary aggregates cover only months with a complete 3-snapshot outcome
              window; sensitivity covers every prediction month
        """
        print("\n" + "=" * 60)
        print("BACKTEST VALIDATION (Rolling Window)")
        print("=" * 60)
        print("\nRolling Window Approach:")
        print("   • For each prediction month:")
        print("     - Select one global policy from earlier prediction months whose full")
        print("       3-snapshot outcome window has already closed")
        print("     - Identify likely next practices for every eligible team using that month's policy")
        print("     - Validate against actual data (checks that month, the next observed")
        print("       snapshot, and the one after that)")
        print("   • Shows accuracy per month, split into primary and sensitivity results")
        print("   • There are no user-adjustable model parameters")

        try:
            from src.validation import BacktestEngine

            backtest = BacktestEngine(self.recommender, self.processor)
            results = backtest.run_backtest()

            if "error" in results:
                print(f"\nError: {results['error']}")
                return

            print(f"\nRunning backtest on {len(self.processor.get_all_teams())} teams...")

            # Display per-month results
            print("\nPer-Month Results:")
            print("-" * 60)
            # Print one summary block per tested month.
            for r in results["per_month_results"]:
                scope = "Primary" if r["full_outcome_window"] else "Sensitivity"
                policy = r["selected_policy"]
                if policy["is_bootstrap"]:
                    policy_text = "Bootstrap (100% popularity)"
                else:
                    policy_text = (
                        f"Sim {policy['similarity_weight'] * 100:.0f}% / Seq {policy['sequence_weight'] * 100:.0f}% / "
                        f"Pop {policy['popularity_weight'] * 100:.0f}% (peers={policy['peer_count']}, "
                        f"min_sim={policy['min_similarity'] * 100:.0f}%, recency={policy['popularity_recency_weight'] * 100:.0f}%)"
                    )
                print(f"   Month {r['month']} [{scope}]:")
                print(f"     Evaluable cases: {r['evaluable_cases']} | Correct: {r['correct']} | Blend Accuracy: {r['accuracy']:.1%}")
                print(
                    f"     Time-Aware Popularity: {r['time_aware_popularity_accuracy']:.1%} | "
                    f"Diff: {r['blend_minus_popularity'] * 100:+.1f}pp"
                )
                print(f"     Selected policy: {policy_text}")

            def print_scope(label: str, scope: dict) -> None:
                print(f"\n{label} Results:")
                if scope["months_included"] == 0:
                    print("   Not enough completed months to report this scope.")
                    return
                print(f"   Months Included: {scope['months_included']}")
                print(f"   Total Predictions: {scope['total_predictions']} (team/month combinations)")
                print(f"   Correct: {scope['correct_predictions']}")
                print(f"   Overall Accuracy: {scope['overall_accuracy']:.1%} (average of all months)")
                print(f"   Random Baseline: {scope['random_baseline']:.1%}")
                print(f"   Improvement: {scope['improvement_factor']:.1f}x better than random")
                popularity_diff = scope["blend_minus_popularity"] * 100
                comparison = "beats" if popularity_diff >= 0 else "trails"
                print(
                    f"   Time-Aware Popularity: {scope['time_aware_popularity_accuracy']:.1%} "
                    f"(blend {comparison} it by {abs(popularity_diff):.1f}pp)"
                )

            print_scope("Primary", results["primary"])
            print_scope("Sensitivity", results["sensitivity"])

        except Exception as e:
            print(f"Error during backtest: {str(e)}")
            import traceback

            traceback.print_exc()

    def _show_system_stats(self) -> None:
        """
        Display comprehensive system statistics.

        Shows information about:
        - Data overview (teams, practices, months, observations)
        - ML model statistics (similarity engine, sequence mapper)
        - Missing values analysis (if available)

        Returns:
            None: Prints statistics to stdout.

        Note:
            - Missing values details are displayed if set by main.py
            - Shows top practices and months with missing values
            - Displays sequence learning statistics
        """
        print("\n" + "=" * 60)
        print("SYSTEM STATISTICS")
        print("=" * 60)

        try:
            teams = self.processor.get_all_teams()
            months = self.processor.get_all_months()
            practices = self.recommender.practices

            print("\nData Overview:")
            print(f"   Teams: {len(teams)}")
            print(f"   Practices: {len(practices)}")
            print(f"   Time Periods: {len(months)}")
            print(f"   Total Observations: {len(teams) * len(months)}")

            print("\nML Model Statistics:")

            print("\nSimilarity Engine:")
            print("   Status: Ready")

            seq_stats = self.recommender.sequence_mapper.get_sequence_stats()
            print("\nSequence Mapper:")
            print(f"   Source Practices With Transitions: {seq_stats.get('num_transition_types', 0)}")
            print(f"   Practices Improved: {seq_stats.get('practices_that_improved', 0)}")

            # Show missing values details if available
            if self.missing_values_details and self.missing_values_details["total_missing"] > 0:
                print("\nMissing Values Analysis:")
                print(f"   Total missing: {self.missing_values_details['total_missing']}")

                if self.missing_values_details["practices_with_missing"]:
                    print("\n   Top practices with missing values:")
                    top_practices = self.missing_values_details["practices_with_missing"][:5]
                    # Print one line per practice with missing data, worst 5 only.
                    for practice in top_practices:
                        info = self.missing_values_details["by_practice"][practice]
                        print(f"     • {practice}: {info['count']} missing ({info['percentage']}%)")
                    if len(self.missing_values_details["practices_with_missing"]) > 5:
                        print(f"     ... and {len(self.missing_values_details['practices_with_missing']) - 5} more")

                if self.missing_values_details["months_with_missing"]:
                    print("\n   Months with missing values:")
                    # Print one line per month with missing data, worst 5 only.
                    for month in self.missing_values_details["months_with_missing"][:5]:
                        info = self.missing_values_details["by_month"][month]
                        print(f"     • {month}: {info['count']} missing ({info['percentage']}%)")
                    if len(self.missing_values_details["months_with_missing"]) > 5:
                        print(f"     ... and {len(self.missing_values_details['months_with_missing']) - 5} more")

            print("\n" + "=" * 60)

        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback

            traceback.print_exc()

    def _show_improvement_sequences(self) -> None:
        """
        Display learned improvement sequences and transition patterns.

        Shows the sequence patterns learned from all teams' improvement history,
        grouped by the "from" practice. Displays transition probabilities and
        frequencies to help understand which practices typically follow others.

        Returns:
            None: Prints sequences to stdout. Returns early if no sequences learned.

        Note:
            - Sequences are learned from all teams and all historical data
            - Shows top 30 sequences by frequency
            - Groups sequences by "from" practice for readability
            - Displays transition probabilities and occurrence counts
        """
        print("\n" + "=" * 60)
        print("IMPROVEMENT SEQUENCES")
        print("=" * 60)

        try:
            sequence_mapper = self.recommender.sequence_mapper

            # Get all sequences
            sequences = sequence_mapper.get_all_sequences(min_count=1)

            if not sequences:
                print("\nWarning: No improvement sequences learned yet.")
                return

            # Get stats
            stats = sequence_mapper.get_sequence_stats()

            print("\nSequence Learning Overview:")
            print(f"   Source Practices With Transitions: {stats.get('num_transition_types', 0)}")
            print(f"   Total Transitions Observed: {stats.get('total_transitions', 0)}")
            print(f"   Practices That Improved: {stats.get('practices_that_improved', 0)}")

            if stats.get("most_improved_practice"):
                most_improved, count = stats["most_improved_practice"]
                print(f"   Most Improved Practice: {most_improved} ({count} times)")

            print("\nWhat This Means:")
            print("   The system analyzed ALL teams and ALL practices to learn")
            print("   which practices typically follow others when teams improve.")
            print("   This creates a network of improvement patterns across the organization.")

            print("\nImprovement Sequences (sorted by frequency):")
            print("   Format: 'Practice A' → 'Practice B' (occurred X times, Y% probability)")
            print("\n" + "-" * 60)

            # Group by from_practice for better readability
            from_practice_groups = {}
            # Bucket every learned sequence under the practice it starts from.
            for from_p, to_p, count, prob in sequences:
                if from_p not in from_practice_groups:
                    from_practice_groups[from_p] = []
                from_practice_groups[from_p].append((to_p, count, prob))

            # Sort groups by total transitions
            sorted_groups = sorted(from_practice_groups.items(), key=lambda x: sum(c for _, c, _ in x[1]), reverse=True)

            # Show top sequences
            max_to_show = 30
            shown = 0

            # Print groups of sequences, from-practice by from-practice, stopping
            # once max_to_show individual sequences have been printed.
            for from_practice, transitions in sorted_groups:
                if shown >= max_to_show:
                    remaining = sum(
                        len(v) for k, v in sorted_groups[sorted_groups.index((from_practice, transitions)) :]
                    )
                    print(f"\n   ... and {remaining} more sequences")
                    break

                print(f"\n   When '{from_practice}' improved:")
                # Print this practice's top 5 "followed by" sequences.
                for to_practice, count, prob in transitions[:5]:  # Top 5 for each practice
                    if shown >= max_to_show:
                        break
                    print(f"      → '{to_practice}' ({count} times, {prob * 100:.1f}% probability)")
                    shown += 1

                if len(transitions) > 5:
                    print(f"      ... and {len(transitions) - 5} more transitions from '{from_practice}'")

            print("\n" + "-" * 60)
            print("\nInterpretation:")
            print("   • These sequences are learned from ALL 87 teams' improvement history")
            print("   • They show which practices naturally follow others")
            print("   • Higher probability = more common pattern across the organization")
            print("   • The system uses these patterns to boost recommendations")

            print("\n" + "=" * 60)

        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback

            traceback.print_exc()
