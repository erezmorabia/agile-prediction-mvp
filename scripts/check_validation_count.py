"""Check how many validations would run in backtest."""
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
print(f"Months: {months}")

# Simulate backtest logic
train_ratio = 0.6
split_point = int(len(months) * train_ratio)
train_months = months[:split_point]
test_months = months[split_point + 1:]  # Leave gap

print(f"\nTrain months ({len(train_months)}): {train_months}")
print(f"Test months ({len(test_months)}): {test_months}")

# Count potential validations
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

print(f"\n{'='*60}")
print(f"Potential validations (teams × test_months where data exists): {total_potential}")
print(f"Actual validations (where team improved): {actual_validations}")
print(f"Simple calculation (teams × test_months): {len(teams) * len(test_months)}")
print(f"\nNote: Actual validations < Potential because:")
print(f"  - Not all teams have data for all test months")
print(f"  - Not all teams have a previous month for each test month")
print(f"  - Not all teams improved something in each test month")

