"""
Example usage of the Agile Prediction MVP.

This script demonstrates programmatic usage of the system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine
from src.validation import BacktestEngine


def example_1_load_data():
    """Example 1: Load and validate data."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Load and Validate Data")
    print("="*60)
    
    excel_file = 'data/raw/20250204_Cleaned_Dataset.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"❌ File not found: {excel_file}")
        return None, None
    
    # Load
    loader = DataLoader(excel_file)
    df = loader.load()
    
    # Get summary
    summary = loader.get_summary()
    print(f"\nData Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Validate
    validator = DataValidator(df, loader.practices)
    is_valid = validator.validate()
    
    return loader, df


def example_2_build_models(df, loader):
    """Example 2: Build ML models."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Build ML Models")
    print("="*60)
    
    # Process
    print("\nProcessing data...")
    processor = DataProcessor(df, loader.practices)
    processor.process()
    
    stats = processor.get_statistics()
    print(f"Processed statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
    
    # Build similarity engine
    print("\nBuilding similarity engine...")
    similarity_engine = SimilarityEngine(processor)
    
    # Learn sequences
    print("Learning sequences...")
    sequence_mapper = SequenceMapper(processor, loader.practices)
    sequence_mapper.learn_sequences()
    
    seq_stats = sequence_mapper.get_sequence_stats()
    print(f"Sequence statistics:")
    for key, value in seq_stats.items():
        print(f"  {key}: {value}")
    
    # Build recommender
    print("Building recommendation engine...")
    recommender = RecommendationEngine(similarity_engine, sequence_mapper, loader.practices)
    
    return processor, recommender


def example_3_get_recommendations(processor, recommender):
    """Example 3: Get recommendations for specific teams."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Get Recommendations")
    print("="*60)
    
    teams = processor.get_all_teams()
    months = processor.get_all_months()
    
    # Get recommendations for first 3 teams
    for team in teams[:3]:
        print(f"\n Team: {team}")
        try:
            history = processor.get_team_history(team)
            team_months = sorted(history.keys())
            
            if len(team_months) < 2:
                print(f"  ⚠️  Not enough months for this team")
                continue
            
            current_month = team_months[0]
            
            recommendations = recommender.recommend(
                team, current_month, top_n=3, k_similar=5
            )
            
            print(f"  Month: {current_month}")
            print(f"  Recommendations:")
            for i, (practice, score, level) in enumerate(recommendations, 1):
                print(f"    {i}. {practice:40s} Score: {score:.3f}  Level: {level:.2f}")
        except ValueError as e:
            print(f"  ⚠️  {str(e)}")


def example_4_find_similar_teams(processor, recommender):
    """Example 4: Find similar teams."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Find Similar Teams")
    print("="*60)
    
    teams = processor.get_all_teams()
    months = processor.get_all_months()
    
    target_team = teams[0]
    current_month = months[0]
    
    print(f"\nFinding teams similar to: {target_team} at month {current_month}")
    
    try:
        similar = recommender.similarity_engine.find_similar_teams(
            target_team, current_month, k=5
        )
        
        print(f"\nMost similar teams (across all historical months):")
        for i, (team, similarity, historical_month) in enumerate(similar, 1):
            print(f"  {i}. {team:30s} Similarity: {similarity:.3f} (similar at month {historical_month})")
    except ValueError as e:
        print(f"  ⚠️  {str(e)}")


def example_5_backtest(processor, recommender):
    """Example 5: Run backtest validation."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Backtest Validation")
    print("="*60)
    
    backtest = BacktestEngine(recommender, processor)
    
    print("\nRunning backtest...")
    results = backtest.run_backtest(train_ratio=0.6)
    
    if 'error' in results:
        print(f"  ❌ Error: {results['error']}")
    else:
        summary = backtest.get_accuracy_summary(results)
        print(summary)


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("AGILE PREDICTION MVP - EXAMPLE USAGE")
    print("="*80)
    
    # Example 1: Load data
    loader, df = example_1_load_data()
    if loader is None:
        return
    
    # Example 2: Build models
    processor, recommender = example_2_build_models(df, loader)
    
    # Example 3: Get recommendations
    example_3_get_recommendations(processor, recommender)
    
    # Example 4: Find similar teams
    example_4_find_similar_teams(processor, recommender)
    
    # Example 5: Backtest
    example_5_backtest(processor, recommender)
    
    print("\n" + "="*80)
    print("✅ Examples complete!")
    print("="*80)
    print("\nTo run interactive mode:")
    print("  python src/main.py data/raw/20250204_Cleaned_Dataset.xlsx")


if __name__ == '__main__':
    main()
