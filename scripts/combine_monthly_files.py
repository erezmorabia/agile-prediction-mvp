"""
Script to combine multiple monthly Excel files into one unified file.

Usage: python scripts/combine_monthly_files.py
"""

import pandas as pd
import os
import re
from pathlib import Path

def extract_month_from_filename(filename: str) -> int:
    """
    Extract month in yyyymmdd format from filename.
    
    Filename format: yyyymmdd_AIM_Heatmap.xlsx
    Returns: yyyymmdd (full 8 digits)
    
    Example: 20200107_AIM_Heatmap.xlsx -> 20200107
    """
    # Extract date pattern (8 digits at start)
    match = re.match(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        # Return full yyyymmdd format
        return int(date_str)  # Keep all 8 digits
    raise ValueError(f"Could not extract date from filename: {filename}")

def combine_monthly_files(input_dir: str = 'data/raw', output_file: str = 'data/raw/combined_dataset.xlsx'):
    """
    Combine multiple monthly Excel files into one unified file.
    
    Args:
        input_dir: Directory containing monthly Excel files
        output_file: Path to output unified Excel file
    """
    input_path = Path(input_dir)
    
    # Get all Excel files matching the pattern (exclude the existing combined file and temp lock files)
    excel_files = sorted([
        f for f in input_path.glob('*_AIM*.xls*')
        if 'combined' not in f.name.lower() 
        and 'cleaned' not in f.name.lower()
        and not f.name.startswith('~$')  # Exclude Excel temporary lock files
    ])
    
    if not excel_files:
        raise ValueError(f"No matching Excel files found in {input_dir}")
    
    print(f"Found {len(excel_files)} Excel files to combine:")
    for f in excel_files:
        print(f"  - {f.name}")
    
    all_data = []
    processed_files = 0
    errors = []
    
    # Column indices (from inspection)
    PRODUCT_OWNER_COL = 14  # Column index for "Product Owner"
    CUSTOMER_ENGAGEMENT_COL = 48  # Column index for "Customer engagement"
    TEAM_NAME_COL = 1  # Column index for "Team Name" (row 1, column 1)
    HEADER_ROW = 1  # Row 1 (0-indexed) contains column headers
    
    # Canonical practice names (from Product Owner to Customer engagement)
    CANONICAL_PRACTICES = [
        'Product Owner', 'Scrum Master', 'Multi function team', 'Multi component team',
        'DoD', 'DoR', 'AIM ceremonies', 'Scrum area', 'Story Points', 'Tasking',
        'Backlog grooming (sprint)', 'Backlog grooming (release)', 'Demo', 'Retro',
        'Unified backlog', 'Personas', 'Story mapping', 'User story template',
        'Tech story template', 'Spikes template', 'Tech debt strategy',
        'Defect management strategy', 'AIM JIRA structure', 'Release tracker',
        'Sprint burndown', 'Time to Value Delivery', 'BDD', 'TDD', 'Test automation',
        'CI/CD', 'Shift-left adoption', 'Single branch strategy', 'Reducing WIP',
        'Engineering 360', 'Customer engagement'
    ]
    
    for file_path in excel_files:
        try:
            print(f"\nProcessing: {file_path.name}")
            
            # Read Excel file with no header (we'll use row 1 as headers)
            df_raw = pd.read_excel(file_path, sheet_name=0, header=None)
            
            # Extract month from filename
            month = extract_month_from_filename(file_path.name)
            
            # Get header row (row 1, index 1)
            header_row = df_raw.iloc[HEADER_ROW]
            
            # Find Team Name column index
            team_name_col_idx = None
            for i, val in enumerate(header_row):
                if pd.notna(val) and 'team' in str(val).lower() and 'name' in str(val).lower():
                    team_name_col_idx = i
                    break
            
            if team_name_col_idx is None:
                # Fallback: use column 1 (based on inspection)
                team_name_col_idx = TEAM_NAME_COL
                print(f"  Using default Team Name column index: {team_name_col_idx}")
            else:
                print(f"  Found Team Name at column index: {team_name_col_idx}")
            
            # Dynamically find practice columns by searching for their names in headers
            # This handles cases where column positions change between months
            practice_col_indices = {}
            practice_names = CANONICAL_PRACTICES
            
            for practice_name in practice_names:
                # Try to find the best match for this practice
                best_match = None
                best_score = 0
                
                for col_idx, header_val in enumerate(header_row):
                    if pd.notna(header_val):
                        header_str = str(header_val).strip()
                        header_lower = header_str.lower()
                        practice_lower = practice_name.lower()
                        
                        # Normalize both strings (remove extra spaces, handle common variations)
                        header_normalized = ' '.join(header_lower.split())
                        practice_normalized = ' '.join(practice_lower.split())
                        
                        # Score 1: Exact match (case-insensitive, normalized)
                        if header_normalized == practice_normalized:
                            best_match = col_idx
                            best_score = 100  # Highest priority
                            break
                        
                        # Score 2: Contains match (practice name is contained in header)
                        # This handles "Multi Component team" matching "Multi component team"
                        if practice_normalized in header_normalized and len(header_str) > 3:
                            # Prefer longer, more specific matches
                            score = len(practice_normalized) / len(header_normalized) * 50
                            if score > best_score:
                                best_match = col_idx
                                best_score = score
                        
                        # Score 3: Header is contained in practice name
                        # This handles abbreviations or shorter names
                        elif header_normalized in practice_normalized and len(header_str) > 3:
                            score = len(header_normalized) / len(practice_normalized) * 30
                            if score > best_score:
                                best_match = col_idx
                                best_score = score
                
                if best_match is not None and best_score >= 30:  # Only accept good matches
                    practice_col_indices[practice_name] = best_match
                else:
                    print(f"  ⚠️  Warning: Could not find column for '{practice_name}' (best score: {best_score:.1f})")
            
            # Sort practices by their column index to maintain order
            sorted_practices = sorted(practice_col_indices.items(), key=lambda x: x[1])
            practice_names_found = [p[0] for p in sorted_practices]
            practice_cols_found = [p[1] for p in sorted_practices]
            
            print(f"  Found {len(practice_names_found)}/{len(CANONICAL_PRACTICES)} practices")
            if len(practice_names_found) < len(CANONICAL_PRACTICES):
                missing = set(CANONICAL_PRACTICES) - set(practice_names_found)
                print(f"  Missing practices: {missing}")
            
            # Select columns: Team Name + Practice columns (in order)
            selected_cols = [team_name_col_idx] + practice_cols_found
            df_selected = df_raw.iloc[2:, selected_cols].copy()  # Skip rows 0 and 1, start from row 2
            
            # Set column names using the found practice names (in order)
            df_selected.columns = ['Team Name'] + practice_names_found
            
            # Remove rows where Team Name is NaN
            df_selected = df_selected[df_selected['Team Name'].notna()].copy()
            
            # Add Month column
            df_selected['Month'] = month
            
            # Convert practice columns to numeric (they should be 0-3 scores)
            for col in practice_names_found:
                df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')
            
            # Ensure Month is integer
            df_selected['Month'] = df_selected['Month'].astype(int)
            
            print(f"  ✓ Rows: {len(df_selected)}, Teams: {df_selected['Team Name'].nunique()}, Month: {month}")
            print(f"  ✓ Practices: {len(practice_names_found)}")
            all_data.append(df_selected)
            processed_files += 1
            
        except Exception as e:
            error_msg = f"  ❌ Error processing {file_path.name}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
            import traceback
            traceback.print_exc()
            continue
    
    if not all_data:
        raise ValueError("No valid data loaded from any files")
    
    print(f"\n{'='*60}")
    print(f"Combining {len(all_data)} files...")
    
    # Find all unique practice columns across all files
    all_practice_columns = set()
    for df in all_data:
        practice_cols = [c for c in df.columns if c not in ['Team Name', 'Month']]
        all_practice_columns.update(practice_cols)
    
    # Use canonical order, but only include practices that were found in at least one file
    # This ensures we have all practices, even if some are missing in some months
    canonical_order = ['Team Name'] + CANONICAL_PRACTICES + ['Month']
    # Filter to only include columns that exist in our data
    expected_columns = [c for c in canonical_order if c in ['Team Name', 'Month'] or c in all_practice_columns]
    
    print(f"  Expected columns: {len(expected_columns)} (Team Name + {len([c for c in expected_columns if c not in ['Team Name', 'Month']])} practices + Month)")
    print(f"  Practices found across all files: {len(all_practice_columns)}")
    
    # Ensure all dataframes have the same columns in the same order
    # Add missing columns as NaN for files that don't have them
    aligned_data = []
    for i, df in enumerate(all_data):
        df_aligned = df.copy()
        
        # Add missing columns (will be NaN)
        for col in expected_columns:
            if col not in df_aligned.columns:
                df_aligned[col] = pd.NA
        
        # Reorder to match expected order
        df_aligned = df_aligned[expected_columns].copy()
        aligned_data.append(df_aligned)
    
    # Combine all dataframes
    combined_df = pd.concat(aligned_data, ignore_index=True)
    
    # Sort by Team Name and Month
    combined_df = combined_df.sort_values(['Team Name', 'Month']).reset_index(drop=True)
    
    # Remove duplicate rows (if any)
    initial_rows = len(combined_df)
    combined_df = combined_df.drop_duplicates()
    if len(combined_df) < initial_rows:
        print(f"  Removed {initial_rows - len(combined_df)} duplicate rows")
    
    # Save to Excel
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_excel(output_path, index=False)
    
    print(f"\n{'='*60}")
    print(f"✅ Combined file created: {output_path}")
    print(f"   Total rows: {len(combined_df):,}")
    print(f"   Teams: {combined_df['Team Name'].nunique()}")
    print(f"   Months: {sorted(combined_df['Month'].unique())}")
    print(f"   Practices: {len([c for c in combined_df.columns if c not in ['Team Name', 'Month']])}")
    
    if errors:
        print(f"\n⚠️  {len(errors)} file(s) had errors:")
        for error in errors:
            print(f"   {error}")
    
    return combined_df

if __name__ == '__main__':
    import sys
    
    # Default paths
    input_dir = 'data/raw'
    output_file = 'data/raw/combined_dataset.xlsx'
    
    # Allow override via command line
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    try:
        combine_monthly_files(input_dir, output_file)
        print("\n✅ Success! You can now use the combined file:")
        print(f"   python src/main.py {output_file}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

