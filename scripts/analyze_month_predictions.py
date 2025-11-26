#!/usr/bin/env python3
"""
Analyze predictions for a specific month to understand accuracy issues.
Shows all teams eligible for predictions, their recommendations, actual improvements, and success/failure.
"""

import sys
sys.path.insert(0, '.')

from src.data import DataLoader, DataProcessor
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine

def analyze_month(month_to_analyze):
    """Analyze all teams eligible for predictions at a specific month."""
    
    # Load data
    print("Loading data...")
    loader = DataLoader('data/raw/combined_dataset.xlsx')
    df = loader.load()
    practices = loader.practices
    
    # Process
    processor = DataProcessor(df, practices)
    processor.process()
    
    # Build models
    similarity_engine = SimilarityEngine(processor)
    sequence_mapper = SequenceMapper(processor, practices)
    recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)
    
    months = sorted(processor.get_all_months())
    
    if month_to_analyze not in months:
        print(f"❌ Month {month_to_analyze} not found in data")
        return
    
    month_idx = months.index(month_to_analyze)
    prev_month = months[month_idx - 1] if month_idx > 0 else None
    
    if not prev_month:
        print(f"❌ No previous month available for {month_to_analyze}")
        return
    
    # Get validation months (3 months ahead)
    next_month = month_to_analyze
    month_after = months[month_idx + 1] if month_idx + 1 < len(months) else None
    month_after_2 = months[month_idx + 2] if month_idx + 2 < len(months) else None
    
    print("="*80)
    print(f"ANALYZING PREDICTIONS FOR MONTH: {month_to_analyze}")
    print("="*80)
    print(f"Baseline month: {prev_month}")
    print(f"Validation window: {next_month}, {month_after}, {month_after_2}")
    print()
    
    # Get all teams
    all_teams = processor.get_all_teams()
    
    # Filter teams eligible for predictions (have data for prev_month and month_to_analyze)
    eligible_teams = []
    for team in all_teams:
        history = processor.get_team_history(team)
        if prev_month in history and month_to_analyze in history:
            eligible_teams.append(team)
    
    print(f"Eligible teams: {len(eligible_teams)}")
    print()
    
    # Analyze each team
    results = []
    for team in eligible_teams:
        history = processor.get_team_history(team)
        prev_vector = history[prev_month]
        current_vector = history[month_to_analyze]
        
        # Get recommendations
        try:
            recommendations = recommender.recommend(team, prev_month, top_n=3, k_similar=5, allow_first_three_months=True)
            recommended_practices = [r[0] for r in recommendations]
        except Exception as e:
            recommended_practices = []
            print(f"⚠️  Error getting recommendations for {team}: {e}")
        
        # Check actual improvements in validation window
        actual_improvements = []
        improved_in_months = {}
        
        for check_month in [next_month, month_after, month_after_2]:
            if check_month and check_month in history:
                check_vector = history[check_month]
                for i, practice in enumerate(practices):
                    if check_vector[i] > prev_vector[i]:
                        improvement = check_vector[i] - prev_vector[i]
                        if practice not in improved_in_months:
                            improved_in_months[practice] = []
                        improved_in_months[practice].append(check_month)
                        # Only add once per practice (best improvement)
                        if practice not in [p for p, _, _ in actual_improvements]:
                            actual_improvements.append((practice, improvement, check_month))
        
        # Calculate success
        recommended_set = set(recommended_practices)
        actual_set = set([p for p, _, _ in actual_improvements])
        hits = recommended_set & actual_set
        is_success = len(hits) > 0 if recommended_practices else None
        
        results.append({
            'team': team,
            'recommendations': recommended_practices,
            'actual_improvements': [p for p, _, _ in actual_improvements],
            'hits': list(hits),
            'is_success': is_success,
            'num_recommendations': len(recommended_practices),
            'num_improvements': len(actual_improvements),
            'improved_in_months': improved_in_months
        })
    
    # Filter teams with improvements (for accuracy calculation)
    teams_with_improvements = [r for r in results if r['num_improvements'] > 0]
    teams_with_recommendations = [r for r in results if r['num_recommendations'] > 0]
    teams_with_both = [r for r in results if r['num_improvements'] > 0 and r['num_recommendations'] > 0]
    
    # Calculate accuracy
    correct_predictions = sum(1 for r in teams_with_both if r['is_success'])
    total_predictions = len(teams_with_both)
    accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total eligible teams: {len(eligible_teams)}")
    print(f"Teams with improvements: {len(teams_with_improvements)}")
    print(f"Teams with recommendations: {len(teams_with_recommendations)}")
    print(f"Teams with both (used for accuracy): {total_predictions}")
    print(f"Correct predictions: {correct_predictions}")
    print(f"Accuracy: {accuracy:.1f}%")
    print()
    
    # Show detailed breakdown
    print("="*80)
    print("DETAILED BREAKDOWN BY TEAM")
    print("="*80)
    print()
    
    # Group by outcome
    successful = [r for r in teams_with_both if r['is_success']]
    failed = [r for r in teams_with_both if not r['is_success']]
    no_recommendations = [r for r in teams_with_improvements if r['num_recommendations'] == 0]
    no_improvements = [r for r in teams_with_recommendations if r['num_improvements'] == 0]
    
    print(f"✅ SUCCESSFUL PREDICTIONS ({len(successful)}):")
    print("-"*80)
    for r in successful:
        print(f"\n{r['team']}:")
        print(f"  Recommendations: {', '.join(r['recommendations'])}")
        print(f"  Actual improvements: {', '.join(r['actual_improvements'])}")
        print(f"  ✅ Hits: {', '.join(r['hits'])}")
    
    print()
    print(f"❌ FAILED PREDICTIONS ({len(failed)}):")
    print("-"*80)
    for r in failed:
        print(f"\n{r['team']}:")
        print(f"  Recommendations: {', '.join(r['recommendations']) if r['recommendations'] else 'None'}")
        print(f"  Actual improvements: {', '.join(r['actual_improvements'])}")
        print(f"  ❌ No overlap - predicted wrong practices")
    
    print()
    print(f"⚠️  NO RECOMMENDATIONS GENERATED ({len(no_recommendations)}):")
    print("-"*80)
    for r in no_recommendations:
        print(f"\n{r['team']}:")
        print(f"  Actual improvements: {', '.join(r['actual_improvements'])}")
        print(f"  ❌ System couldn't generate recommendations (no similar teams/sequences)")
    
    print()
    print(f"ℹ️  NO IMPROVEMENTS ({len(no_improvements)}):")
    print("-"*80)
    for r in no_improvements:
        print(f"\n{r['team']}:")
        print(f"  Recommendations: {', '.join(r['recommendations'])}")
        print(f"  ℹ️  Team didn't improve anything (excluded from accuracy)")
    
    # Show top failure reasons
    print()
    print("="*80)
    print("FAILURE ANALYSIS")
    print("="*80)
    
    if failed:
        print(f"\nTop practices that were recommended but NOT improved ({len(failed)} teams):")
        recommended_but_not_improved = {}
        for r in failed:
            for practice in r['recommendations']:
                if practice not in recommended_but_not_improved:
                    recommended_but_not_improved[practice] = 0
                recommended_but_not_improved[practice] += 1
        
        for practice, count in sorted(recommended_but_not_improved.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {practice}: recommended to {count} teams, none improved it")
        
        print(f"\nTop practices that improved but were NOT recommended ({len(failed)} teams):")
        improved_but_not_recommended = {}
        for r in failed:
            for practice in r['actual_improvements']:
                if practice not in improved_but_not_recommended:
                    improved_but_not_recommended[practice] = 0
                improved_but_not_recommended[practice] += 1
        
        for practice, count in sorted(improved_but_not_recommended.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {practice}: improved by {count} teams, but not recommended")
    
    # Detailed analysis of top failure cases
    print()
    print("="*80)
    print("DETAILED ANALYSIS OF TOP FAILURE CASES")
    print("="*80)
    
    # Analyze top 3 failed predictions
    top_failures = failed[:3]
    for r in top_failures:
        team = r['team']
        print(f"\n{team}:")
        print("-"*80)
        
        # Get recommendations with explanations
        history = processor.get_team_history(team)
        try:
            recommendations = recommender.recommend(team, prev_month, top_n=3, k_similar=5, allow_first_three_months=True)
            
            print(f"Recommended practices:")
            for practice, score, level in recommendations:
                explanation = recommender.get_recommendation_explanation(team, prev_month, practice)
                print(f"  - {practice} (score: {score:.4f}):")
                similar_teams_list = explanation.get('similar_teams_list', [])
                similar_teams_count = explanation.get('similar_teams_improved', 0)
                if similar_teams_list:
                    print(f"    Similar teams evidence: {similar_teams_count} teams improved this")
                    for st in similar_teams_list[:2]:
                        team_name = st.get('team', 'Unknown')
                        similarity = st.get('similarity', 0)
                        month = st.get('month', 'Unknown')
                        similar_at = st.get('similar_at_month', 'Unknown')
                        if similar_at != month:
                            print(f"      • {team_name}: {similarity:.1%} similar (at {similar_at}, improved in {month})")
                        else:
                            print(f"      • {team_name}: {similarity:.1%} similar (improved in {month})")
                else:
                    print(f"    Similar teams evidence: None")
                
                sequence_follows = explanation.get('typical_sequence_follows')
                if sequence_follows:
                    print(f"    Sequence pattern: {practice} typically followed by {sequence_follows}")
                else:
                    print(f"    Sequence pattern: None")
            
            print(f"\nActual improvements:")
            for practice in r['actual_improvements']:
                # Check why this wasn't recommended
                practice_idx = practices.index(practice)
                current_level = history[prev_month][practice_idx]
                max_level = 3.0
                
                if current_level >= max_level:
                    reason = f"Already at max level ({current_level:.1f})"
                else:
                    # Check if similar teams improved this
                    similar_teams = similarity_engine.find_similar_teams(team, prev_month, k=5)
                    similar_improved_this = []
                    for sim_team, sim_score, hist_month in similar_teams:
                        sim_history = processor.get_team_history(sim_team)
                        if hist_month in sim_history:
                            sim_vector = sim_history[hist_month]
                            # Check if they improved this practice up to 3 months ahead
                            for lookahead in range(1, 4):
                                check_month_idx = months.index(hist_month) + lookahead if hist_month in months else -1
                                if check_month_idx < len(months):
                                    check_month = months[check_month_idx]
                                    if check_month <= month_to_analyze and check_month in sim_history:
                                        check_vector = sim_history[check_month]
                                        if check_vector[practice_idx] > sim_vector[practice_idx]:
                                            similar_improved_this.append((sim_team, sim_score, check_month))
                                            break
                    
                    if similar_improved_this:
                        reason = f"Similar teams improved it: {', '.join([st[0] for st in similar_improved_this[:2]])}"
                    else:
                        reason = "No similar teams improved it (or no similar teams found)"
                
                print(f"  - {practice}: {reason}")
        except Exception as e:
            print(f"  Error analyzing: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_month_predictions.py <month>")
        print("Example: python analyze_month_predictions.py 20201005")
        sys.exit(1)
    
    month = int(sys.argv[1])
    analyze_month(month)

