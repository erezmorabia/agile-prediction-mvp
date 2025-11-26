"""Quick script to inspect Excel file structure and extract best practices."""
import pandas as pd

file_path = 'data/raw/20200107_AIM_Heatmap.xlsx'

print("=== Reading Excel file (row 1 = column headers) ===")
df = pd.read_excel(file_path, header=None)

# Row 1 (index 1) contains the column headers
header_row = df.iloc[1]
print(f"Header row has {len(header_row)} columns")

# Find Product Owner and customer engagement columns
product_owner_idx = None
customer_engagement_idx = None

print("\n=== Searching for column range ===")
for i, val in enumerate(header_row):
    if pd.notna(val):
        val_str = str(val).strip()
        val_lower = val_str.lower()
        
        if 'product owner' in val_lower and product_owner_idx is None:
            product_owner_idx = i
            print(f"✓ Found 'Product Owner' at column index {i}: '{val_str}'")
        
        if 'customer engagement' in val_lower and customer_engagement_idx is None:
            customer_engagement_idx = i
            print(f"✓ Found 'customer engagement' at column index {i}: '{val_str}'")

if product_owner_idx is not None and customer_engagement_idx is not None:
    print(f"\n=== Best Practices (columns {product_owner_idx} to {customer_engagement_idx}) ===")
    practices = []
    for i in range(product_owner_idx, customer_engagement_idx + 1):
        val = header_row.iloc[i]
        if pd.notna(val):
            practices.append(str(val).strip())
    
    print(f"\nFound {len(practices)} best practices:")
    for idx, practice in enumerate(practices, 1):
        print(f"  {idx:2d}. {practice}")
    
    print(f"\n=== Summary ===")
    print(f"Start column: {product_owner_idx} ('{practices[0]}')")
    print(f"End column: {customer_engagement_idx} ('{practices[-1]}')")
    print(f"Total practices: {len(practices)}")
else:
    print("\n❌ Could not find both 'Product Owner' and 'customer engagement' columns")
    if product_owner_idx is None:
        print("   Missing: 'Product Owner'")
    if customer_engagement_idx is None:
        print("   Missing: 'customer engagement'")

