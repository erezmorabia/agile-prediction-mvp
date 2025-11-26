"""Analyze different train/test split scenarios to see validation counts."""
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data import DataLoader, DataProcessor

# Load data
loader = DataLoader('data/raw/combined_dataset.xlsx')
df = loader.load()

processor = DataProcessor(df, loader.practices)
processor.process()

teams = processor.get_all_teams()
months = processor.get_all_months()

print(f"Total teams: {len(teams)}")
print(f"Total months: {len(months)}")
print(f"Months: {months}\n")

# Test different train/test split scenarios
scenarios = [
    (0.5, "50/50 split"),
    (0.55, "55/45 split"),
    (0.6, "60/40 split (current)"),
    (0.65, "65/35 split"),
    (0.7, "70/30 split"),
]

print("="*70)
print("VALIDATION COUNT ANALYSIS - Different Train/Test Splits")
print("="*70)

for train_ratio, description in scenarios:
    split_point = int(len(months) * train_ratio)
    train_months = months[:split_point]
    test_months = months[split_point + 1:] if split_point + 1 < len(months) else months[split_point:]
    
    if not test_months:
        continue
    
    # Count validations
    total_potential = 0
    actual_validations = 0
    
    for team in teams:
        history = processor.get_team_history(team)
        team_months = sorted([m for m in months if m in history])
        
        for test_month in test_months:
            if test_month not in history:
                continue
            
            test_idx = team_months.index(test_month) if test_month in team_months else -1
            if test_idx <= 0:
                continue
            
            prev_month = team_months[test_idx - 1]
            
            # Check if team actually improved
            prev_vector = history[prev_month]
            test_vector = history[test_month]
            
            improved = False
            for p, t in zip(prev_vector, test_vector):
                if t > p:
                    improved = True
                    break
            
            total_potential += 1
            if improved:
                actual_validations += 1
    
    print(f"\n{description}")
    print(f"  Train months: {len(train_months)} ({train_months[0]} to {train_months[-1]})")
    print(f"  Test months: {len(test_months)} ({test_months[0]} to {test_months[-1]})")
    print(f"  Potential validations: {total_potential}")
    print(f"  Actual validations: {actual_validations}")
    print(f"  Improvement rate: {actual_validations/total_potential*100:.1f}%")

# Statistical significance analysis
print("\n" + "="*70)
print("STATISTICAL SIGNIFICANCE ANALYSIS")
print("="*70)

# Using current scenario (60/40 split)
train_ratio = 0.6
split_point = int(len(months) * train_ratio)
test_months = months[split_point + 1:]

actual_validations = 54  # From previous run

# For a binomial test with 35 practices
# Random baseline = 1/35 ≈ 2.9%
# If we get 68% accuracy, that's 23.8x better than random

print(f"\nCurrent scenario (60/40 split):")
print(f"  Test months: {len(test_months)}")
print(f"  Actual validations: {actual_validations}")
print(f"\nStatistical considerations:")
print(f"  - Minimum for statistical significance: ~30-50 validations")
print(f"  - Your current count: {actual_validations} validations")
print(f"  - Status: {'✅ SUFFICIENT' if actual_validations >= 30 else '⚠️  MAY BE LOW'}")
print(f"\nRecommendations:")
if actual_validations < 50:
    print(f"  - Consider using more test months to reach 50+ validations")
    print(f"  - This would improve confidence in the accuracy metric")
else:
    print(f"  - Current validation count is statistically sound")
    print(f"  - 50+ validations provides good confidence in results")

