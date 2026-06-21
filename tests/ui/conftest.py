"""
Session-level fixture that boots the real FastAPI app (with real data) on port 8001
so Playwright tests can run against an actual server.

Mirrors the startup sequence in src/web_main.py — any change there should be
reflected here too.

Skip the entire UI test session if the data file is absent.
"""

import os
import sys
import threading
import time

import pytest
import requests

# Add project root so src.* imports work from inside tests/ui/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_DATA_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "raw", "combined_dataset.xlsx"
)
_TEST_PORT = 8001
_BASE_URL = f"http://localhost:{_TEST_PORT}"


def pytest_configure(config):
    if not os.path.exists(_DATA_FILE):
        pytest.skip(
            "UI tests require data/raw/combined_dataset.xlsx — file not found",
            allow_module_level=True,
        )


@pytest.fixture(scope="session")
def live_server():
    """Build the FastAPI app from real data and serve it for the test session."""
    import uvicorn

    from src.api import APIService
    from src.api.main import create_app
    from src.data import DataLoader, DataProcessor, DataValidator
    from src.ml import RecommendationEngine, SequenceMapper, SimilarityEngine

    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    docs_path = os.path.join(project_root, "docs", "PROJECT_DOCUMENTATION.md")

    loader = DataLoader(_DATA_FILE)
    df = loader.load()
    practices = loader.practices

    validator = DataValidator(df, practices)
    validator.validate()
    filtered_practices, _ = validator.filter_high_missing_practices(practices, threshold=90.0)
    practices = filtered_practices
    missing_details = validator.get_missing_values_details_for_practices(practices)

    processor = DataProcessor(df, practices)
    processor.process()

    similarity_engine = SimilarityEngine(processor)
    sequence_mapper = SequenceMapper(processor, practices)
    sequence_mapper.learn_sequences()
    recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)

    service = APIService(recommender, processor)
    service.missing_values_details = missing_details
    service.data_file_path = os.path.abspath(_DATA_FILE)
    service.docs_path = docs_path

    app = create_app(service)

    config = uvicorn.Config(app, host="127.0.0.1", port=_TEST_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Poll until the server responds (up to 60 s — data loading takes ~10-20 s)
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            requests.get(f"{_BASE_URL}/api/stats", timeout=2)
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError(f"UI test server did not start within 60 s on port {_TEST_PORT}")

    yield _BASE_URL

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="session")
def base_url(live_server):
    """Override pytest-playwright's base_url to point at our test server."""
    return live_server
