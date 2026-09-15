"""Keep the analysis notebook aligned with the production calculations."""

import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "SuperStore_Sales_Data_Analysis.ipynb"


def test_notebook_has_no_saved_outputs():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    assert all(
        cell.get("execution_count") is None
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )


def test_notebook_uses_production_analytics_and_correct_terms():
    source = NOTEBOOK.read_text(encoding="utf-8")
    assert "from src.analytics import calculate_discount_profitability" in source
    assert "from src.analytics import calculate_customer_value_segments" in source
    assert "from src.analytics import calculate_quarterly_performance" in source
    assert "1,348" not in source  # Calculated at runtime rather than duplicated.
    assert "A **transaction** is one dataframe row" in source
    assert "**2011–2014**" in source
