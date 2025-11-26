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
        self.recommender = recommender_engine
        self.processor = processor
        self.formatter = OutputFormatter()
        self.missing_values_details = None  # Will be set by main.py

    def run(self) -> None:
        """
        Run the interactive command-line interface.

        Displays a menu-driven interface allowing users to:
        1. Get recommendations for specific teams
        2. Run backtest validation
        3. View system statistics
        4. View learned improvement sequences
        5. Find optimal configuration via grid search
        6. View latest optimization results
        7. Exit

        The interface runs in a loop until the user selects option 7 (Exit).
        All operations use the initialized recommender and processor instances.

        Returns:
            None: Runs interactively until user exits.

        Note:
            - Missing values details are displayed if available (set by main.py)
            - All user input is validated before processing
            - Errors are caught and displayed with helpful messages
        """
        self._show_header()

        while True:
            self._show_menu()
            choice = input("\nEnter choice (1-7): ").strip()

            if choice == "1":
                self._get_recommendations()
            elif choice == "2":
                self._validate_recommendations()
            elif choice == "3":
                self._show_system_stats()
            elif choice == "4":
                self._show_improvement_sequences()
            elif choice == "5":
                self._find_optimal_config()
            elif choice == "6":
                self._view_latest_optimization_results()
            elif choice == "7":
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
        print("5. Find Optimal Configuration")
        print("6. View Latest Optimization Results")
        print("7. Exit")
        print("-" * 60)

    def _find_teams_with_improvements(self) -> list[tuple[str, int, int, int]]:
        """
        Find teams and months where improvements occurred in the next month.

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

        for team in all_teams:
            history = self.processor.get_team_history(team)
            months = sorted(history.keys())

            # Check each month (except the last one, which has no next month)
            for i in range(len(months) - 1):
                current_month = months[i]
                next_month = months[i + 1]

                current_vector = history[current_month]
                next_vector = history[next_month]

                # Count improvements
                improvements = []
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
        2. Selecting a month to predict (must be month 3 or later)
        3. Displaying similar teams used for collaborative filtering
        4. Generating and displaying top 5 recommendations
        5. Validating recommendations against actual improvements
        6. Showing practice maturity profile

        The validation checks improvements in a 3-month window (predicted month,
        month+1, month+2) to account for adoption timelines.

        Returns:
            None: Prints results interactively. Returns early on error.

        Note:
            - Month to predict must be month 3 or later (need 2 months history)
            - Recommendations are generated using previous month as baseline
            - Validation accuracy is only calculated if improvements occurred
            - Practice profile shows current maturity levels grouped by level (0-3)
        """
        print("\n" + "=" * 60)
        print("GET RECOMMENDATIONS")
        print("=" * 60)

        try:
            # Find teams with improvements
            teams_with_improvements = self._find_teams_with_improvements()

            if not teams_with_improvements:
                print("\nWarning: No teams found with improvements in next month")
                print("   You can still get recommendations, but validation won't be available")
                use_filter = False
            else:
                print(f"\nFound {len(teams_with_improvements)} team/month combinations with improvements")
                print("   (These allow validation in the next month)")
                use_filter = input("\nShow only teams with improvements? (y/n, default=y): ").strip().lower()
                use_filter = use_filter != "n"

            if use_filter and teams_with_improvements:
                # Group by team and show options
                teams_dict = {}
                for team, month, next_month, num_improvements in teams_with_improvements:
                    if team not in teams_dict:
                        teams_dict[team] = []
                    teams_dict[team].append((month, next_month, num_improvements))

                # Sort teams by number of improvement months (descending)
                teams_sorted = sorted(teams_dict.items(), key=lambda x: (-len(x[1]), x[0]))

                print(f"\nTeams with improvements ({len(teams_sorted)} teams):")
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
                    if 0 <= team_idx < len(teams_sorted):
                        team_name = teams_sorted[team_idx][0]
                    else:
                        team_name = choice
                except ValueError:
                    team_name = choice

                if team_name not in teams_dict:
                    print(f"Error: Team '{team_name}' not found or has no improvements")
                    return

                # Show months to predict (only months 3+)
                # Month to predict starts from month 3 (we need months 1-2 as history)
                all_available_months = sorted(self.processor.get_all_months())
                if len(all_available_months) >= 3:
                    first_two_months = set(all_available_months[:2])  # Filter out months 1-2
                    # Filter to show only months 3+ as month to predict
                    months_list = [(m, n, num) for m, n, num in teams_dict[team_name] if m not in first_two_months]
                else:
                    months_list = []

                if not months_list:
                    print(f"Error: Team '{team_name}' has no months available for prediction")
                    print("   Need at least 3 months of data. Month to predict starts from month 3.")
                    return

                print(f"\nAvailable months to predict for {team_name} (with improvements):")
                for i, (month, next_month, num_imp) in enumerate(months_list):
                    print(f"  {i + 1}. Month to predict: {month} ({num_imp} improvements occurred)")

                month_choice = input("\nEnter month number or date (yyyymmdd): ").strip()

                # Try to parse as number
                try:
                    month_idx = int(month_choice) - 1
                    if 0 <= month_idx < len(months_list):
                        month_to_predict = months_list[month_idx][0]
                    else:
                        month_to_predict = int(month_choice)
                except ValueError:
                    month_to_predict = int(month_choice)

                history = self.processor.get_team_history(team_name)
                if month_to_predict not in history:
                    print(f"Error: No data for team on month {month_to_predict}")
                    return

                # Validate that month to predict is month 3 or later
                if len(all_available_months) >= 3:
                    first_two_months = set(all_available_months[:2])
                    if month_to_predict in first_two_months:
                        print("Error: Month to predict must be month 3 or later.")
                        print(f"   Month {month_to_predict} is in the first 2 months.")
                        print("   We need at least 2 months of history to make predictions.")
                        return

                # Find previous month to use as baseline
                months = sorted(history.keys())
                month_to_predict_idx = months.index(month_to_predict)
                if month_to_predict_idx == 0:
                    print(f"Error: Cannot predict month {month_to_predict} - no previous month available")
                    return

                prev_month = months[month_to_predict_idx - 1]  # Use previous month as baseline
                # Skip the month selection below since we already processed it
                month_already_selected = True
            else:
                # Original behavior - show all teams
                all_teams = self.processor.get_all_teams()

                # Sort teams by number of months they have data for (descending)
                teams_with_data = []
                for team in all_teams:
                    history = self.processor.get_team_history(team)
                    num_months = len(history)
                    teams_with_data.append((team, num_months))

                # Sort by number of months (descending), then alphabetically
                teams_with_data.sort(key=lambda x: (-x[1], x[0]))
                teams = [team for team, _ in teams_with_data]

                print(f"\nAvailable teams ({len(teams)} total, sorted by data availability):")
                for i, team in enumerate(teams[:10]):
                    num_months = teams_with_data[i][1]
                    print(f"  {team} ({num_months} months)")
                if len(teams) > 10:
                    print(f"  ... and {len(teams) - 10} more")

                team_name = input("\nEnter team name: ").strip()

                if team_name not in teams:
                    print(f"Error: Team '{team_name}' not found")
                    return

                month_already_selected = False

            # Get month to predict (only if not already selected from filtered path)
            if not month_already_selected:
                history = self.processor.get_team_history(team_name)
                all_months = sorted(history.keys())

                # Filter to show only months 3+ (month to predict starts from month 3)
                # We need at least 2 months of history, so month 3 is the first predictable month
                all_available_months = sorted(self.processor.get_all_months())
                if len(all_available_months) >= 3:
                    first_two_months = set(all_available_months[:2])  # Filter out months 1-2
                    months_to_predict = [m for m in all_months if m not in first_two_months]
                else:
                    months_to_predict = []

                if not months_to_predict:
                    print(f"Error: Team '{team_name}' has no months available for prediction")
                    print("   Need at least 3 months of data. Month to predict starts from month 3.")
                    return

                print(f"\nAvailable months to predict for {team_name} (starting from month 3):")
                print(f"   {months_to_predict}")
                if len(all_months) > len(months_to_predict):
                    filtered_out = [m for m in all_months if m not in months_to_predict]
                    print(f"   (Months {filtered_out} excluded - need at least 2 months of history)")

                month_to_predict = int(input("Enter month to predict (yyyymmdd): ").strip())

                if month_to_predict not in history:
                    print(f"Error: No data for team on month {month_to_predict}")
                    return

                # Validate that month to predict is month 3 or later
                if len(all_available_months) >= 3:
                    first_two_months = set(all_available_months[:2])
                    if month_to_predict in first_two_months:
                        print("Error: Month to predict must be month 3 or later.")
                        print(f"   Month {month_to_predict} is in the first 2 months.")
                        print("   We need at least 2 months of history to make predictions.")
                        return

                # Find previous month to use as baseline
                months = sorted(history.keys())
                if month_to_predict not in months:
                    print(f"Error: Month {month_to_predict} not found in team history")
                    return

                month_to_predict_idx = months.index(month_to_predict)
                if month_to_predict_idx == 0:
                    print(f"Error: Cannot predict month {month_to_predict} - no previous month available")
                    return

                prev_month = months[month_to_predict_idx - 1]  # Use previous month as baseline

            # Get team history and months (ensure they're defined)
            history = self.processor.get_team_history(team_name)
            months = sorted(history.keys())

            # Show similar teams before generating recommendations
            print("\nFinding similar teams...")
            print(f"   Using month {prev_month} as baseline to predict month {month_to_predict}")
            try:
                similar_teams = self.recommender.similarity_engine.find_similar_teams(team_name, prev_month, k=5)
                if similar_teams:
                    print(f"\nTop {len(similar_teams)} Similar Teams (for collaborative filtering):")
                    print("-" * 60)
                    for i, (similar_team, similarity_score, historical_month) in enumerate(similar_teams, 1):
                        similarity_pct = similarity_score * 100
                        print(
                            f"   {i}. {similar_team:30s} | {similarity_pct:5.1f}% similar (at month {historical_month})"
                        )
                    print("-" * 60)
                    print("\nNote: These teams' improvement patterns will be used to generate recommendations")
                else:
                    print("   Warning: No similar teams found")
            except Exception as e:
                print(f"   Warning: Could not find similar teams: {str(e)}")

            # Get recommendations
            print(f"\nGenerating recommendations for month {month_to_predict}...")

            # Check for actual improvements in the predicted month and next 2 months
            month_to_predict_idx = months.index(month_to_predict)
            prev_vector = history[prev_month]
            predicted_vector = history[month_to_predict]

            month_after = None
            month_after_2 = None
            actual_improvements = []  # List of (practice_name, improvement, improved_in_months)

            # Get what actually improved in the predicted month
            improvements_month1 = {}
            for j, (prev, pred) in enumerate(zip(prev_vector, predicted_vector)):
                if pred > prev:
                    practice_name = self.recommender.practices[j]
                    improvement = pred - prev
                    improvements_month1[practice_name] = improvement

            # Check if month_after exists and get improvements there too
            improvements_month2 = {}
            if month_to_predict_idx + 1 < len(months):
                month_after = months[month_to_predict_idx + 1]
                month_after_vector = history[month_after]

                for j, (prev, after) in enumerate(zip(prev_vector, month_after_vector)):
                    if after > prev:
                        practice_name = self.recommender.practices[j]
                        improvement = after - prev
                        improvements_month2[practice_name] = improvement

            # Check if month_after_2 exists and get improvements there too (third month ahead)
            improvements_month3 = {}
            if month_to_predict_idx + 2 < len(months):
                month_after_2 = months[month_to_predict_idx + 2]
                month_after_2_vector = history[month_after_2]

                for j, (prev, after2) in enumerate(zip(prev_vector, month_after_2_vector)):
                    if after2 > prev:
                        practice_name = self.recommender.practices[j]
                        improvement = after2 - prev
                        improvements_month3[practice_name] = improvement

            # Combine improvements from all 3 months (predicted month, month_after, month_after_2)
            all_practices = (
                set(improvements_month1.keys()) | set(improvements_month2.keys()) | set(improvements_month3.keys())
            )
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

            # Use optimized defaults: top_n=2, k_similar=19 (matches web interface)
            recommendations = self.recommender.recommend(team_name, prev_month, top_n=2, k_similar=19)

            # Display recommendations
            print(f"\nTop {len(recommendations)} Recommendations for {team_name} (Predicting month {month_to_predict}):")
            print("-" * 60)

            if not recommendations:
                print("\nWarning: No recommendations available")
                print("\nThis can happen when:")
                print("   • All practices are already at maximum maturity level, OR")
                print("   • Similar teams didn't improve any practices in the time window we can use")
                print("   • No sequence patterns apply to your team's recent improvements")
                print("\nNote: Try selecting a different month or team to see recommendations.")
                print("-" * 60)
                return

            print("\nUnderstanding the Output:")
            print("   • Current Level: Your team's maturity (0-1 scale, where 0.33=Level 1, 0.67=Level 2, 1.0=Level 3)")
            print("   • Recommendation Score: How strongly we recommend this (higher = more evidence)")
            print("   • Score combines: Similar teams' improvements (60%) + Natural sequences (40%)")

            recommended_practices = [r[0] for r in recommendations]

            for i, (practice, score, current_level) in enumerate(recommendations, 1):
                # Convert normalized level back to original 0-3 scale for display
                original_level = current_level * 3
                # Determine level number (0, 1, 2, or 3)
                if current_level < 0.17:
                    level_num = 0
                    level_description = "Not implemented"
                elif current_level < 0.5:
                    level_num = 1
                    level_description = "Basic level"
                elif current_level < 0.84:
                    level_num = 2
                    level_description = "Intermediate level"
                else:
                    level_num = 3
                    level_description = "Mature level"

                level_display = f"Level {level_num} ({level_description})"

                # Get explanation with similar teams details
                similar_teams_list = []
                similar_count = 0
                try:
                    explanation = self.recommender.get_recommendation_explanation(team_name, prev_month, practice)
                    similar_count = explanation.get("similar_teams_improved", 0)
                    similar_teams_list = explanation.get("similar_teams_list", [])
                except:
                    pass

                # Check if this was actually improved in next month or month after
                actually_improved = False
                improvement_amount = 0.0
                improved_in_months = []
                if next_month:
                    for actual_practice, improvement, improved_in in actual_improvements:
                        if actual_practice == practice:
                            actually_improved = True
                            improvement_amount = improvement
                            improved_in_months = improved_in
                            break

                print(f"\n{i}. {practice}")
                print(f"   Recommendation Score: {score:.3f} (range: 0.0-1.0, higher = stronger)")
                print(f"   Current Level: {level_display}")
                if similar_count > 0:
                    print(f"   Why: {similar_count} similar team(s) improved this practice")
                    if similar_teams_list:
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
                else:
                    print("   Why: Recommended based on improvement sequences")

                # Show validation if predicted month exists
                if month_to_predict:
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
            if month_to_predict:
                validation_months_text = f"Month {month_to_predict}"
                if month_after:
                    validation_months_text += f", {month_after}"
                if month_after_2:
                    validation_months_text += f", and {month_after_2}"
                print(f"\nValidation Summary (checking improvements in {validation_months_text}):")
                if actual_improvements:
                    print(f"   Practices that actually improved: {len(actual_improvements)}")
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
                    actual_set = set([p for p, _, _ in actual_improvements])
                    hits = len(recommended_set & actual_set)

                    if actual_improvements and recommended_set:
                        # Both improvements and recommendations exist - calculate accuracy
                        accuracy = hits / len(recommended_set) * 100
                        print(f"\n   Recommendation Accuracy: {hits}/{len(recommended_set)} = {accuracy:.1f}%")
                    elif not actual_improvements:
                        # No improvements occurred - don't calculate accuracy
                        print("\n   Note: Recommendation Accuracy: Not calculated (no improvements occurred)")
                        print(
                            "      This is not a model failure - the team didn't improve anything in the validation window."
                        )
                    elif not recommended_set:
                        # No recommendations generated
                        print("\n   Recommendation Accuracy: Not calculated (no recommendations generated)")
                else:
                    print(f"   Warning: No practices improved in {validation_months_text}")
                    print("\n   Note: Accuracy is not calculated when no improvements occurred.")
                    print("      This is not a model failure - it just means the team didn't improve")
                    print("      anything in the validation window (next 3 months).")
            else:
                print("\nValidation: No future month available for validation")

            # Display practice maturity profile
            print("\n" + "=" * 60)
            print("\nCurrent Practice Maturity Profile")
            print("-" * 60)
            practice_profile = self._get_practice_profile(team_name, prev_month)

            for level in [0, 1, 2, 3]:
                practices = practice_profile[level]
                if practices:
                    if level == 0:
                        level_name = "Not implemented"
                    elif level == 1:
                        level_name = "Basic level"
                    elif level == 2:
                        level_name = "Intermediate level"
                    else:
                        level_name = "Advanced level"

                    print(f"\nLevel {level} ({level_name}): {len(practices)} practices")
                    # Display practices in columns for better readability
                    practices_sorted = sorted(practices)
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
        Run rolling window backtest validation and display results.

        Executes a full backtest validation using the BacktestEngine, which tests
        the recommendation system on historical data using a time-series cross-validation
        approach. Results are displayed in a formatted, human-readable format.

        The backtest:
        - Tests each month starting from month 4
        - Uses all previous months for training (sliding window)
        - Validates predictions against actual improvements in a 3-month window
        - Calculates accuracy, random baseline, and improvement metrics

        Returns:
            None: Prints results to stdout. Returns early on error.

        Note:
            - Requires at least 4 months of data
            - May take several minutes depending on data size
            - Shows per-month results and overall summary
            - Displays improvement factor vs random baseline
        """
        print("\n" + "=" * 60)
        print("BACKTEST VALIDATION (Rolling Window)")
        print("=" * 60)
        print("\nRolling Window Approach:")
        print("   • For each month starting from month 4:")
        print("     - Train on all previous months")
        print("     - Predict what will happen in that month")
        print("     - Validate against actual data (checks that month, month+1, AND month+2)")
        print("   • Shows accuracy per month and overall average")
        print("   • Note: Validation checks 3 months ahead to account for adoption timelines")
        print("     (This aligns with recommendation logic which looks up to 3 months ahead)")

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
            for r in results["per_month_results"]:
                print(f"   Month {r['month']}:")
                print(
                    f"     Training: {len(r['train_months'])} months ({r['train_months'][0]} to {r['train_months'][-1]})"
                )
                print(f"     Predictions: {r['predictions']} | Correct: {r['correct']} | Accuracy: {r['accuracy']:.1%}")
                print(f"     Teams tested: {r['teams_tested']}")

            # Display overall results
            accuracy = results["overall_accuracy"]
            baseline = results["random_baseline"]
            improvement = results["improvement_factor"]

            print("\nOverall Results:")
            print(f"   Total Predictions: {results['total_predictions']} (team/month combinations)")
            print(f"   Correct: {results['correct_predictions']}")
            print(f"   Overall Accuracy: {accuracy:.1%} (average of all months)")
            print(f"   Random Baseline: {baseline:.1%}")
            print(f"   Improvement: {improvement:.1f}x better than random")
            print(f"   Months Tested: {len(results['per_month_results'])}")

        except Exception as e:
            print(f"Error during backtest: {str(e)}")
            import traceback

            traceback.print_exc()

    def _find_optimal_config(self) -> None:
        """
        Interactive workflow to find optimal configuration via grid search.

        Runs the OptimizationEngine to test parameter combinations and find the
        best configuration based on improvement_gap (difference between model accuracy
        and random baseline). Displays progress updates and final results.

        The optimization:
        - Tests all combinations of specified parameter ranges
        - Runs backtest validation for each combination
        - Tracks best configuration by improvement_gap
        - Can stop early if excellent solution found
        - Automatically saves results to JSON file

        Returns:
            None: Prints results interactively. Returns early on error or cancellation.

        Note:
            - May take 30+ minutes depending on parameter ranges
            - Shows progress every 10 combinations tested
            - Can be cancelled with Ctrl-C (shows partial results)
            - Results are saved to results/optimization_*.json
            - Displays top 10 configurations for comparison
        """
        print("\n" + "=" * 60)
        print("FIND OPTIMAL CONFIGURATION")
        print("=" * 60)
        print("\nThis will test multiple parameter combinations to find the best configuration.")
        print("This may take several minutes...")

        try:
            from src.validation import BacktestEngine, OptimizationEngine

            backtest = BacktestEngine(self.recommender, self.processor)
            optimizer = OptimizationEngine(backtest)

            # Progress callback to show updates
            def progress_callback(current, total, config):
                if current % 10 == 0 or current == 1:
                    percentage = (current / total * 100) if total > 0 else 0
                    print(f"   Progress: {current}/{total} ({percentage:.1f}%)")

            print("\nRunning optimization...")
            result = optimizer.find_optimal_config(min_accuracy=0.40, progress_callback=progress_callback)

            if result.get("cancelled", False):
                print("\nWarning: Optimization was cancelled.")
                if result.get("total_combinations_tested", 0) > 0:
                    print(
                        f"   Tested {result['total_combinations_tested']}/{result['total_combinations_available']} combinations"
                    )
                    print("   Showing partial results...")
                else:
                    print("   No results available.")
                    return

            if result.get("early_stopped", False):
                print("\nEarly stop: Found excellent solution!")

            if not result.get("optimal_config"):
                print("\nError: No optimal configuration found.")
                print(
                    f"   Tested {result.get('total_combinations_tested', 0)}/{result.get('total_combinations_available', 0)} combinations"
                )
                print(f"   Valid combinations: {result.get('valid_combinations', 0)}")
                print("   No configuration met the minimum accuracy threshold of 40%.")
                return

            config = result["optimal_config"]
            model_accuracy = result.get("model_accuracy", 0.0)
            random_baseline = result.get("random_baseline", 0.0)
            improvement_gap = result.get("improvement_gap", 0.0)
            improvement_factor = result.get("improvement_factor", 0.0)

            print("\n" + "=" * 60)
            print("OPTIMAL CONFIGURATION FOUND")
            print("=" * 60)

            print("\nOptimization Summary:")
            print(f"   Total Combinations Available: {result.get('total_combinations_available', 0)}")
            print(f"   Combinations Tested: {result.get('total_combinations_tested', 0)}")
            completion_pct = (
                (result.get("total_combinations_tested", 0) / result.get("total_combinations_available", 1) * 100)
                if result.get("total_combinations_available", 0) > 0
                else 0
            )
            print(f"   Completion: {completion_pct:.1f}%")
            if result.get("cancelled"):
                print("   Status: Cancelled (partial results)")
            elif result.get("early_stopped"):
                print("   Status: Early stopped (excellent solution found)")
            else:
                print("   Status: Completed")

            print("\nParameter Ranges Tested:")
            print("   • top_n: [2, 3, 4, 5] - Number of recommendations to generate")
            print("   • similarity_weight: [0.6, 0.7, 0.8] - Weight for similar teams (rest is sequence weight)")
            print("   • k_similar: [5, 10, 15, 19, 20] - Number of similar teams to consider")
            print("   • similar_teams_lookahead_months: [3] - How far ahead to check for improvements")
            print("   • recent_improvements_months: [3] - How recent improvements must be to trigger sequence boosts")
            print("   • min_similarity_threshold: [0.0, 0.5, 0.75] - Filter out low-similarity teams (0.0 = no filter)")

            print("\nOptimal Configuration:")
            print(f"   top_n: {config['top_n']} - Generate {config['top_n']} recommendations")
            print(
                f"   similarity_weight: {config['similarity_weight']:.2f} - {config['similarity_weight'] * 100:.0f}% weight on similar teams, {(1 - config['similarity_weight']) * 100:.0f}% on sequences"
            )
            print(f"   k_similar: {config['k_similar']} - Consider {config['k_similar']} most similar teams")
            print(
                f"   similar_teams_lookahead_months: {config['similar_teams_lookahead_months']} - Check {config['similar_teams_lookahead_months']} months ahead for improvements"
            )
            print(
                f"   recent_improvements_months: {config['recent_improvements_months']} - Consider improvements from last {config['recent_improvements_months']} months"
            )
            if config["min_similarity_threshold"] > 0:
                print(
                    f"   min_similarity_threshold: {config['min_similarity_threshold']:.2f} - Only consider teams with ≥{config['min_similarity_threshold'] * 100:.0f}% similarity"
                )
            else:
                print(
                    f"   min_similarity_threshold: {config['min_similarity_threshold']:.2f} - No similarity filter (consider all teams)"
                )

            print("\nResults:")
            print(f"   Model Accuracy: {model_accuracy:.1%}")
            print(f"   Random Baseline: {random_baseline:.1%}")
            print(f"   Improvement Gap: {improvement_gap:.1%}")
            print(f"   Improvement Factor: {improvement_factor:.1f}x")

            print("\nSummary:")
            print(
                f"   Total Combinations Tested: {result.get('total_combinations_tested', 0)}/{result.get('total_combinations_available', 0)}"
            )
            print(f"   Valid Combinations: {result.get('valid_combinations', 0)}")
            print(f"   Total Predictions: {result.get('total_predictions', 0)}")
            print(f"   Correct Predictions: {result.get('correct_predictions', 0)}")

            if result.get("results_file"):
                print(f"\nResults saved to: {result['results_file']}")

            # Show top 10 configurations
            all_results = result.get("all_results", [])
            if len(all_results) > 1:
                print("\n" + "-" * 60)
                print("TOP 10 CONFIGURATIONS")
                print("-" * 60)
                print(
                    f"{'Rank':<6} {'top_n':<8} {'sim_w':<8} {'k_sim':<8} {'min_sim':<10} {'Acc':<8} {'Random':<8} {'Gap':<8}"
                )
                print("-" * 60)
                for idx, r in enumerate(all_results[:10], 1):
                    print(
                        f"{idx:<6} {r['config']['top_n']:<8} {r['config']['similarity_weight']:<8.2f} "
                        f"{r['config']['k_similar']:<8} "
                        f"{r['config']['min_similarity_threshold']:<10.2f} {r['model_accuracy'] * 100:<7.1f}% "
                        f"{r['random_baseline'] * 100:<7.1f}% {r['improvement_gap'] * 100:<7.1f}%"
                    )

        except KeyboardInterrupt:
            print("\n\nWarning: Optimization cancelled by user (Ctrl-C)")
        except Exception as e:
            print(f"\nError during optimization: {str(e)}")
            import traceback

            traceback.print_exc()

    def _view_latest_optimization_results(self) -> None:
        """
        Display the latest optimization results from saved JSON file.

        Loads the most recent optimization results file from the results/ directory
        and displays them in a formatted, human-readable format. Useful for reviewing
        previous optimization runs without re-running the optimization.

        Returns:
            None: Prints results to stdout. Returns early if no results found.

        Note:
            - Looks for files matching pattern: optimization_*.json in results/ directory
            - Loads the most recently modified file
            - Displays same information as _find_optimal_config() results
            - Shows cancellation/early stop status if applicable
        """
        print("\n" + "=" * 60)
        print("VIEW LATEST OPTIMIZATION RESULTS")
        print("=" * 60)

        try:
            from src.validation.optimizer import OptimizationEngine

            results = OptimizationEngine.load_latest_results()
            if results is None:
                print("\nWarning: No optimization results found.")
                print("   Please run an optimization first (option 5).")
                return

            print(f"\nLoaded results from: {results.get('timestamp', 'unknown timestamp')}")

            if not results.get("optimal_config"):
                print("\nError: No optimal configuration found in saved results.")
                print(
                    f"   Tested {results.get('total_combinations_tested', 0)}/{results.get('total_combinations_available', 0)} combinations"
                )
                print(f"   Valid combinations: {results.get('valid_combinations', 0)}")
                return

            config = results["optimal_config"]
            model_accuracy = results.get("model_accuracy", 0.0)
            random_baseline = results.get("random_baseline", 0.0)
            improvement_gap = results.get("improvement_gap", 0.0)
            improvement_factor = results.get("improvement_factor", 0.0)

            print("\nOptimization Summary:")
            print(f"   Total Combinations Available: {results.get('total_combinations_available', 0)}")
            print(f"   Combinations Tested: {results.get('total_combinations_tested', 0)}")
            completion_pct = (
                (results.get("total_combinations_tested", 0) / results.get("total_combinations_available", 1) * 100)
                if results.get("total_combinations_available", 0) > 0
                else 0
            )
            print(f"   Completion: {completion_pct:.1f}%")
            if results.get("cancelled"):
                print("   Status: Cancelled (partial results)")
            elif results.get("early_stopped"):
                print("   Status: Early stopped (excellent solution found)")
            else:
                print("   Status: Completed")

            print("\nParameter Ranges Tested:")
            print("   • top_n: [2, 3, 4, 5] - Number of recommendations to generate")
            print("   • similarity_weight: [0.6, 0.7, 0.8] - Weight for similar teams (rest is sequence weight)")
            print("   • k_similar: [5, 10, 15, 19, 20] - Number of similar teams to consider")
            print("   • similar_teams_lookahead_months: [3] - How far ahead to check for improvements")
            print("   • recent_improvements_months: [3] - How recent improvements must be to trigger sequence boosts")
            print("   • min_similarity_threshold: [0.0, 0.5, 0.75] - Filter out low-similarity teams (0.0 = no filter)")

            print("\nOptimal Configuration:")
            print(f"   top_n: {config['top_n']} - Generate {config['top_n']} recommendations")
            print(
                f"   similarity_weight: {config['similarity_weight']:.2f} - {config['similarity_weight'] * 100:.0f}% weight on similar teams, {(1 - config['similarity_weight']) * 100:.0f}% on sequences"
            )
            print(f"   k_similar: {config['k_similar']} - Consider {config['k_similar']} most similar teams")
            print(
                f"   similar_teams_lookahead_months: {config['similar_teams_lookahead_months']} - Check {config['similar_teams_lookahead_months']} months ahead for improvements"
            )
            print(
                f"   recent_improvements_months: {config['recent_improvements_months']} - Consider improvements from last {config['recent_improvements_months']} months"
            )
            if config["min_similarity_threshold"] > 0:
                print(
                    f"   min_similarity_threshold: {config['min_similarity_threshold']:.2f} - Only consider teams with ≥{config['min_similarity_threshold'] * 100:.0f}% similarity"
                )
            else:
                print(
                    f"   min_similarity_threshold: {config['min_similarity_threshold']:.2f} - No similarity filter (consider all teams)"
                )

            print("\nResults:")
            print(f"   Model Accuracy: {model_accuracy:.1%}")
            print(f"   Random Baseline: {random_baseline:.1%}")
            print(f"   Improvement Gap: {improvement_gap:.1%}")
            print(f"   Improvement Factor: {improvement_factor:.1f}x")

            print("\nSummary:")
            print(
                f"   Total Combinations Tested: {results.get('total_combinations_tested', 0)}/{results.get('total_combinations_available', 0)}"
            )
            print(f"   Valid Combinations: {results.get('valid_combinations', 0)}")
            print(f"   Total Predictions: {results.get('total_predictions', 0)}")
            print(f"   Correct Predictions: {results.get('correct_predictions', 0)}")

            if results.get("cancelled"):
                print("\nWarning: Note: This optimization was cancelled.")
            elif results.get("early_stopped"):
                print("\nNote: This optimization stopped early (excellent solution found).")

            # Show top 10 configurations
            all_results = results.get("all_results", [])
            if len(all_results) > 1:
                print("\n" + "-" * 60)
                print("TOP 10 CONFIGURATIONS")
                print("-" * 60)
                print(
                    f"{'Rank':<6} {'top_n':<8} {'sim_w':<8} {'k_sim':<8} {'min_sim':<10} {'Acc':<8} {'Random':<8} {'Gap':<8}"
                )
                print("-" * 60)
                for idx, r in enumerate(all_results[:10], 1):
                    print(
                        f"{idx:<6} {r['config']['top_n']:<8} {r['config']['similarity_weight']:<8.2f} "
                        f"{r['config']['k_similar']:<8} "
                        f"{r['config']['min_similarity_threshold']:<10.2f} {r['model_accuracy'] * 100:<7.1f}% "
                        f"{r['random_baseline'] * 100:<7.1f}% {r['improvement_gap'] * 100:<7.1f}%"
                    )

        except Exception as e:
            print(f"\nError loading latest results: {str(e)}")
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

            sim_stats = (
                self.recommender.similarity_engine.get_similarity_stats()
                if hasattr(self.recommender.similarity_engine, "get_similarity_stats")
                else None
            )

            print("\nSimilarity Engine:")
            print("   Status: Ready")

            seq_stats = self.recommender.sequence_mapper.get_sequence_stats()
            print("\nSequence Mapper:")
            print(f"   Transition Types: {seq_stats.get('num_transition_types', 0)}")
            print(f"   Practices Improved: {seq_stats.get('practices_that_improved', 0)}")

            # Show missing values details if available
            if self.missing_values_details and self.missing_values_details["total_missing"] > 0:
                print("\nMissing Values Analysis:")
                print(f"   Total missing: {self.missing_values_details['total_missing']}")

                if self.missing_values_details["practices_with_missing"]:
                    print("\n   Top practices with missing values:")
                    top_practices = self.missing_values_details["practices_with_missing"][:5]
                    for practice in top_practices:
                        info = self.missing_values_details["by_practice"][practice]
                        print(f"     • {practice}: {info['count']} missing ({info['percentage']}%)")
                    if len(self.missing_values_details["practices_with_missing"]) > 5:
                        print(f"     ... and {len(self.missing_values_details['practices_with_missing']) - 5} more")

                if self.missing_values_details["months_with_missing"]:
                    print("\n   Months with missing values:")
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
            print(f"   Total Transition Patterns: {stats.get('num_transition_types', 0)}")
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
            for from_p, to_p, count, prob in sequences:
                if from_p not in from_practice_groups:
                    from_practice_groups[from_p] = []
                from_practice_groups[from_p].append((to_p, count, prob))

            # Sort groups by total transitions
            sorted_groups = sorted(from_practice_groups.items(), key=lambda x: sum(c for _, c, _ in x[1]), reverse=True)

            # Show top sequences
            max_to_show = 30
            shown = 0

            for from_practice, transitions in sorted_groups:
                if shown >= max_to_show:
                    remaining = sum(
                        len(v) for k, v in sorted_groups[sorted_groups.index((from_practice, transitions)) :]
                    )
                    print(f"\n   ... and {remaining} more sequences")
                    break

                print(f"\n   When '{from_practice}' improved:")
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
