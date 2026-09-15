"""Optional local browser verification; requires Playwright and Chromium."""

import json
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Inspect every tab, exercise a filter, and save current screenshots."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1600, "height": 2400}, device_scale_factor=1
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("tab", name="Overview", exact=False).wait_for(timeout=30000)
        page.locator(".js-plotly-plot").first.wait_for(timeout=30000)
        page.get_by_text("Developed by Adeel Manaf", exact=False).wait_for(
            timeout=60000
        )
        page.get_by_test_id("stStatusWidget").wait_for(state="hidden", timeout=60000)
        screenshots = [
            "overview",
            "discount",
            "customers",
            "products",
            "regions",
            "findings",
        ]
        tabs = page.get_by_role("tab")
        for index, name in enumerate(screenshots):
            tabs.nth(index).click()
            page.wait_for_timeout(600)
            assert page.locator('[data-testid="stException"]').count() == 0
            assert page.locator(".katex").count() == 0, (
                f"Currency must not render as equations: {page.locator('.katex').all_text_contents()}"
            )
            footer = page.locator(".footer").bounding_box()
            page.screenshot(
                path=str(ROOT / "assets" / f"{name}_current.png"),
                clip={
                    "x": 0,
                    "y": 0,
                    "width": 1600,
                    "height": min(2400, int(footer["y"] + footer["height"] + 40)),
                },
            )
        # Filter rerender in an actual browser; AppTest covers precise numeric parity.
        page.get_by_role("combobox").nth(0).click()
        page.get_by_role("option", name="Furniture", exact=True).click()
        source = pd.read_csv(ROOT / "superstore_cleaned.csv")
        expected_sales = source.loc[source["Category"] == "Furniture", "Sales"].sum()
        page.get_by_test_id("stMetricValue").first.get_by_text(
            f"${expected_sales:,.0f}", exact=True
        ).wait_for(timeout=30000)
        page.get_by_test_id("stStatusWidget").wait_for(state="hidden", timeout=60000)
        assert page.locator('[data-testid="stException"]').count() == 0
        assert not errors, errors
        print(
            json.dumps(
                {
                    "tabs_checked": len(screenshots),
                    "page_errors": errors,
                    "category_filter": "Furniture",
                    "screenshots": "assets/*_current.png",
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    main()
