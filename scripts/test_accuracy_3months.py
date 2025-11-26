#!/usr/bin/env python3
"""
Test accuracy with 3-month lookahead implementation.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine
from src.validation import BacktestEngine

def main():
    # Load data
    excel_file = 'data/raw/combined_dataset.xlsx'
    print(f"Loading data from: {excel_file}")
    
    loader = DataLoader(excel_file)
    df = loader.load()
    practices = loader.practices
    
    print(f"✅ Loaded: {len(df['Team Name'].unique())} teams, {len(practices)} practices, {len(df['Month'].unique())} months")
    
    # Validate
    validator = DataValidator(df, practices)
    validator.validate()
    
    # Process
    processor = DataProcessor(df, practices)
    processor.process()
    
    # Build models
    similarity_engine = SimilarityEngine(processor)
    sequence_mapper = SequenceMapper(processor, practices)
    sequence_mapper.learn_sequences()
    recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)
    
    # Run backtest
    backtest = BacktestEngine(recommender, processor)
    results = backtest.run_backtest(train_ratio=0.5)
    
    # Display results
    print("\n" + "="*60)
    print("BACKTEST RESULTS (with 3-month lookahead)")
    print("="*60)
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    months = processor.get_all_months()
    split_point = int(len(months) * 0.5)
    train_months = months[:split_point]
    test_months = months[split_point + 1:]  # Leave gap
    
    print(f"\n📊 Data Split:")
    print(f"   Total months: {len(months)}")
    print(f"   Training months: {len(train_months)} ({train_months[0]} to {train_months[-1]})")
    print(f"   Gap month: {months[split_point]}")
    print(f"   Test months: {len(test_months)} ({test_months[0]} to {test_months[-1]})")
    
    accuracy = results['overall_accuracy']
    baseline = results['random_baseline']
    improvement = accuracy / baseline if baseline > 0 else 0
    
    print(f"\n📈 Accuracy Results:")
    print(f"   Total Predictions: {results['total_predictions']}")
    print(f"   Correct: {results['correct_predictions']}")
    print(f"   Accuracy: {accuracy*100:.1f}%")
    print(f"   Random Baseline: {baseline*100:.1f}%")
    print(f"   Improvement: {improvement:.1f}x better than random")
    print(f"   Teams Tested: {results['teams_tested']}")
    
    print(f"\n💡 Key Changes:")
    print(f"   • Now checking up to 3 months ahead for similar teams' improvements")
    print(f"   • This captures improvements that don't happen every month")
    print(f"   • Still only using past data (no data leakage)")

if __name__ == '__main__':
    main()

