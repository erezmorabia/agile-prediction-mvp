"""
UI Test 2 — UC-01 Get Recommendations golden path.

Selects the first available team and month, requests recommendations,
and verifies that recommendation cards are rendered.
"""

from playwright.sync_api import Page, expect


def test_recommendations_golden_path(page: Page, base_url: str):
    page.goto(base_url)
    page.click('button[data-tab="recommendations"]')
    page.wait_for_selector("#recommendations-tab.active", timeout=5_000)

    # Wait for the team dropdown to be populated with real data
    team_select = page.locator("#team-select")
    expect(team_select).not_to_contain_text("Loading teams...", timeout=30_000)

    # Pick the first real team (index 1 skips the disabled placeholder)
    first_team = team_select.locator("option").nth(1)
    team_value = first_team.get_attribute("value")
    team_select.select_option(value=team_value)

    # Month dropdown should become enabled and populated
    month_select = page.locator("#month-select")
    expect(month_select).to_be_enabled(timeout=10_000)
    expect(month_select).not_to_contain_text("Select a team first", timeout=10_000)

    # Pick the first available month
    first_month = month_select.locator("option").nth(0)
    month_value = first_month.get_attribute("value")
    month_select.select_option(value=month_value)

    # Button should now be enabled
    get_btn = page.locator("#get-recommendations-btn")
    expect(get_btn).to_be_enabled(timeout=5_000)
    get_btn.click()

    # Results section should appear with recommendation cards
    page.wait_for_selector("#recommendations-results:not(.hidden)", timeout=30_000)

    # At least one numbered recommendation card must be present
    expect(page.locator("#recommendations-results .rec-number").first).to_be_visible(timeout=10_000)
