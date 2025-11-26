"""
Web interface entry point for the Agile Practice Prediction System.

Usage:
    python src/web_main.py <path_to_excel_file>

Example:
    python src/web_main.py data/raw/combined_dataset.xlsx
"""

import logging
import os
import sys

# Configure logging to show INFO level and above, with timestamps
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Add project root to Python path to enable absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    When running as PyInstaller executable, resources are extracted to a temp folder
    and the path is stored in sys._MEIPASS. In development mode, use project root.
    
    Args:
        relative_path: Path relative to project root (e.g., 'data/raw/combined_dataset.xlsx')
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development mode: use project root
        base_path = project_root
    return os.path.join(base_path, relative_path)


def main() -> int:
    """
    Main entry point for the web interface of the Agile Practice Prediction System.

    Loads agile metrics data from an Excel file, validates and processes it,
    builds machine learning models, and starts a FastAPI web server with
    REST API endpoints and a web UI for generating practice recommendations.

    The system follows a 5-step initialization process:
    1. Load data from Excel file
    2. Validate data quality and filter practices with >90% missing values
    3. Process and normalize data (0-3 scale normalized to 0-1)
    4. Build ML models (similarity engine, sequence mapper, recommendation engine)
    5. Initialize FastAPI web server with API service

    Args:
        sys.argv[1] (str, optional): Path to Excel file containing agile metrics.
            If not provided, tries 'data/raw/combined_dataset.xlsx' first,
            then falls back to 'data/raw/20250204_Cleaned_Dataset.xlsx'.
            Expected format: Excel file with columns 'Team Name', 'Month', and
            practice columns with values 0-3 (maturity levels).

    Returns:
        int: Exit code. 0 for success, 1 for error.

    Raises:
        FileNotFoundError: If the specified Excel file does not exist.
        ValueError: If data validation fails or file format is invalid.
        KeyboardInterrupt: If server is stopped by user (Ctrl+C).
        Exception: Any other error during initialization or execution.

    Example:
        >>> # Run with default file
        >>> python src/web_main.py
        Starting Agile Practice Prediction System (Web Interface)...

        >>> # Run with custom file
        >>> python src/web_main.py data/raw/my_data.xlsx
        Starting Agile Practice Prediction System (Web Interface)...
           Loading: data/raw/my_data.xlsx

    Note:
        - Practices with >90% missing values are automatically excluded
        - Data is normalized from 0-3 scale to 0-1 for ML algorithms
        - Web server runs on http://localhost:8000
        - API documentation available at http://localhost:8000/docs
        - Server uses extended timeouts (5 min keep-alive) for long-running optimization requests
    """

    # Setup path
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        # Try bundled path first (PyInstaller executable mode), then relative path (development mode)
        excel_file = get_resource_path("data/raw/combined_dataset.xlsx")
        if not os.path.exists(excel_file):
            excel_file = get_resource_path("data/raw/20250204_Cleaned_Dataset.xlsx")
            if not os.path.exists(excel_file):
                # Fallback to relative path (for development)
                excel_file = "data/raw/combined_dataset.xlsx"
                if not os.path.exists(excel_file):
                    excel_file = "data/raw/20250204_Cleaned_Dataset.xlsx"
                    if not os.path.exists(excel_file):
                        print("Error: Usage: python src/web_main.py <path_to_excel_file>")
                        print(f"   File not found: {excel_file}")
                        return 1

    if not os.path.exists(excel_file):
        print(f"Error: File not found: {excel_file}")
        return 1

    print("Starting Agile Practice Prediction System (Web Interface)...")
    print(f"   Loading: {excel_file}")

    # Import components
    import time
    import webbrowser
    import uvicorn

    from src.api import APIService
    from src.api.main import create_app
    from src.data import DataLoader, DataProcessor, DataValidator
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

        # Get missing values details
        missing_details = validator.get_missing_values_details()
        if missing_details["total_missing"] > 0:
            print(f"\nMissing Values: {missing_details['total_missing']} total")
            print(f"   Practices with missing: {len(missing_details['practices_with_missing'])}")
            print(f"   Months with missing: {len(missing_details['months_with_missing'])}")

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

        # Step 5: Create API service and app
        print("\n[5/5] Initializing web interface...")
        service = APIService(recommender, processor)
        # Store filtered missing values details for API
        service.missing_values_details = filtered_missing_details
        app = create_app(service)

        print("\nSystem initialized successfully!")
        print("\n" + "=" * 60)
        print("Web Interface Ready")
        print("=" * 60)
        print("   Open your browser to: http://localhost:8000")
        print("   API documentation: http://localhost:8000/docs")
        print("   Press Ctrl+C to stop the server")
        print("=" * 60 + "\n")

        # Start server with increased timeout settings for long-running requests
        # Use threading to allow browser opening after server starts
        import threading
        
        def open_browser_after_delay():
            """Open browser after server has had time to start"""
            time.sleep(2.0)  # Wait for server to be ready
            try:
                webbrowser.open('http://localhost:8000')
            except Exception:
                # Browser opening failed, but continue anyway
                pass
        
        # Start browser opener in background thread
        browser_thread = threading.Thread(target=open_browser_after_delay, daemon=True)
        browser_thread.start()
        
        # Start server (this will block until Ctrl+C)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            timeout_keep_alive=300,  # 5 minutes keep-alive timeout
            timeout_graceful_shutdown=30,  # 30 seconds graceful shutdown
        )

    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
