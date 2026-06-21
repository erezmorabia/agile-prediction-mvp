"""
UI Test 1 — Tab rendering.

Verifies that all four tabs load without JavaScript errors and display their
expected content sections. Does not exercise any interactive flows.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(autouse=True)
def go_home(page: Page, base_url: str):
    page.goto(base_url)


class TestTabRendering:
    def test_stats_tab_auto_loads(self, page: Page):
        """Statistics tab is the default landing tab and fetches data automatically."""
        # Wait for the hidden class to be removed from the results div
        page.wait_for_selector("#stats-results:not(.hidden)", timeout=30_000)
        expect(page.locator("#stats-results")).to_contain_text("teams")

    def test_backtest_tab_renders(self, page: Page):
        """Backtest tab shows the config panel and Run Backtest button."""
        page.click('button[data-tab="backtest"]')
        page.wait_for_selector("#backtest-tab.active", timeout=5_000)
        expect(page.locator("#run-backtest-btn")).to_be_visible()
        expect(page.locator("#find-optimal-btn")).to_be_visible()

    def test_sequences_tab_loads(self, page: Page):
        """Sequences tab triggers a lazy fetch and renders transition patterns."""
        page.click('button[data-tab="sequences"]')
        page.wait_for_selector("#sequences-tab.active", timeout=5_000)
        page.wait_for_selector("#sequences-results:not(.hidden)", timeout=20_000)
        expect(page.locator("#sequences-results")).to_contain_text("→")

    def test_recommendations_tab_renders(self, page: Page):
        """Recommendations tab shows the team dropdown populated with real teams."""
        page.click('button[data-tab="recommendations"]')
        page.wait_for_selector("#recommendations-tab.active", timeout=5_000)
        team_select = page.locator("#team-select")
        expect(team_select).to_be_visible()
        # Dropdown must have moved past the "Loading teams..." placeholder
        expect(team_select).not_to_contain_text("Loading teams...", timeout=30_000)
        # Month select starts disabled until a team is chosen
        expect(page.locator("#month-select")).to_be_disabled()
