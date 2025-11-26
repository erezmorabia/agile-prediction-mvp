"""
Main entry point for the Agile Practice Prediction MVP.

Usage:
    python main.py <path_to_excel_file>

Example:
    python main.py data/raw/20250204_Cleaned_Dataset.xlsx
"""

import os
import sys

# Add project root to Python path to enable absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def main() -> int:
    """
    Main entry point for the CLI interface of the Agile Practice Prediction System.

    Loads agile metrics data from an Excel file, validates and processes it,
    builds machine learning models (similarity engine, sequence mapper, and
    recommendation engine), and starts an interactive CLI for generating
    practice recommendations.

    The system follows a 5-step initialization process:
    1. Load data from Excel file
    2. Validate data quality and filter practices with >90% missing values
    3. Process and normalize data (0-3 scale normalized to 0-1)
    4. Build ML models (similarity engine, sequence mapper, recommendation engine)
    5. Start interactive CLI interface

    Args:
        sys.argv[1] (str, optional): Path to Excel file containing agile metrics.
            If not provided, defaults to 'data/raw/20250204_Cleaned_Dataset.xlsx'.
            Expected format: Excel file with columns 'Team Name', 'Month', and
            practice columns with values 0-3 (maturity levels).

    Returns:
        int: Exit code. 0 for success, 1 for error.

    Raises:
        FileNotFoundError: If the specified Excel file does not exist.
        ValueError: If data validation fails or file format is invalid.
        Exception: Any other error during initialization or execution.

    Example:
        >>> # Run with default file
        >>> python main.py
        Starting Agile Practice Prediction System MVP...

        >>> # Run with custom file
        >>> python main.py data/raw/my_data.xlsx
        Starting Agile Practice Prediction System MVP...
           Loading: data/raw/my_data.xlsx

    Note:
        - Practices with >90% missing values are automatically excluded
        - Data is normalized from 0-3 scale to 0-1 for ML algorithms
        - The CLI provides interactive menu for recommendations, validation, and analysis
    """

    # Setup path
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        # Look for file in data/raw directory
        excel_file = "data/raw/20250204_Cleaned_Dataset.xlsx"
        if not os.path.exists(excel_file):
            print("Error: Usage: python main.py <path_to_excel_file>")
            print(f"   File not found: {excel_file}")
            return

    if not os.path.exists(excel_file):
        print(f"Error: File not found: {excel_file}")
        return

    print("Starting Agile Practice Prediction System MVP...")
    print(f"   Loading: {excel_file}")

    # Import components
    from src.data import DataLoader, DataProcessor, DataValidator
    from src.interface import CLIInterface
    from src.ml import RecommendationEngine, SequenceMapper, SimilarityEngine

    try:
        # Step 1: Load data
        print("\n[1/5] Loading data...")
        loader = DataLoader(excel_file)
        df = loader.load()
        practices = loader.practices

        # Step 2: Validate data
        print("\n[2/5] Validating data...")
        validator = DataValidator(df, practices)
        validation_passed = validator.validate()

        # Show detailed missing values information
        missing_details = validator.get_missing_values_details()
        if missing_details["total_missing"] > 0:
            print("\nMissing Values Breakdown:")
            print(f"   Total missing: {missing_details['total_missing']}")

            # Show top practices with missing values
            if missing_details["practices_with_missing"]:
                print(f"\n   Practices with missing values ({len(missing_details['practices_with_missing'])}):")
                top_practices = missing_details["practices_with_missing"][:10]
                for practice in top_practices:
                    info = missing_details["by_practice"][practice]
                    print(f"     • {practice}: {info['count']} missing ({info['percentage']}%)")
                if len(missing_details["practices_with_missing"]) > 10:
                    print(f"     ... and {len(missing_details['practices_with_missing']) - 10} more")

            # Show months with missing values
            if missing_details["months_with_missing"]:
                print(f"\n   Months with missing values ({len(missing_details['months_with_missing'])}):")
                for month in missing_details["months_with_missing"][:10]:
                    info = missing_details["by_month"][month]
                    print(f"     • {month}: {info['count']} missing ({info['percentage']}%)")
                if len(missing_details["months_with_missing"]) > 10:
                    print(f"     ... and {len(missing_details['months_with_missing']) - 10} more")

        if not validation_passed:
            print("Warning: Continuing despite validation warnings...")

        # Step 2.5: Filter out practices with >90% missing values
        print("\n[2.5/5] Filtering practices with high missing values...")
        filtered_practices, excluded_practices = validator.filter_high_missing_practices(practices, threshold=90.0)
        if excluded_practices:
            print(f"   Warning: Excluding {len(excluded_practices)} practices with >90% missing values:")
            for practice in excluded_practices:
                print(f"      - {practice}")
            print(f"   Using {len(filtered_practices)} practices for analysis")
        else:
            print(f"   All {len(filtered_practices)} practices have sufficient data")

        # Update practices list to use filtered version
        practices = filtered_practices

        # Recalculate missing values details for filtered practices only
        filtered_missing_details = validator.get_missing_values_details_for_practices(practices)

        # Step 3: Process data
        print("\n[3/5] Processing data...")
        processor = DataProcessor(df, practices)
        processor.process()

        # Step 4: Build ML models
        print("\n[4/5] Building ML models...")

        # Similarity engine (will be built on demand)
        similarity_engine = SimilarityEngine(processor)

        # Sequence mapper
        sequence_mapper = SequenceMapper(processor, practices)
        sequence_mapper.learn_sequences()

        # Recommendation engine
        recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)

        # Step 5: Start CLI
        print("\n[5/5] Starting user interface...")
        cli = CLIInterface(recommender, processor)

        # Store filtered missing values details for CLI display
        cli.missing_values_details = filtered_missing_details

        print("\nSystem initialized successfully!")
        print("   Type your commands or select from the menu")

        cli.run()

    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
