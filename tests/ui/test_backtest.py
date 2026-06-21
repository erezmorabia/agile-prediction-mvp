"""
UI Test 3 — UC-02 Run Backtest Validation golden path.

Clicks Run Backtest with default parameters and verifies that the
per-month results table and overall accuracy metrics are rendered.
"""

from playwright.sync_api import Page, expect


def test_backtest_golden_path(page: Page, base_url: str):
    page.goto(base_url)
    page.click('button[data-tab="backtest"]')
    page.wait_for_selector("#backtest-tab.active", timeout=5_000)

    page.click("#run-backtest-btn")

    # Backtest runs through all historical months — give it up to 90 seconds
    page.wait_for_selector("#backtest-results:not(.hidden)", timeout=90_000)

    # Per-month results table should be present
    expect(page.locator("#backtest-results .per-month-results")).to_be_visible(timeout=10_000)

    # Overall accuracy metric must show a percentage value
    expect(page.locator("#backtest-results")).to_contain_text("%", timeout=5_000)
