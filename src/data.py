"""Repository-relative loading, validation, and inclusive dashboard filters."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "superstore_cleaned.csv"
REQUIRED_COLUMNS = (
    "Order ID",
    "Order Date",
    "Ship Date",
    "Sales",
    "Profit",
    "Discount",
    "Category",
    "Sub-Category",
    "Region",
    "Segment",
    "Customer ID",
    "Customer Name",
    "Product Name",
)
NUMERIC_COLUMNS = ("Sales", "Profit", "Discount")
DATE_COLUMNS = ("Order Date", "Ship Date")


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a typed copy or raise a readable error; never silently drop rows."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    result = df.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in REQUIRED_COLUMNS:
        if result[column].isna().any():
            raise ValueError(f"Dataset contains missing values in '{column}'.")
    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
        if not np.isfinite(result[column]).all():
            raise ValueError(f"Dataset requires finite numeric values in '{column}'.")
    if not result["Discount"].between(0, 1).all():
        raise ValueError("Discount must be a fraction between 0 and 1 inclusive.")
    if (result["Sales"] < 0).any():
        raise ValueError("Sales must be nonnegative for this dashboard.")
    for column in DATE_COLUMNS:
        result[column] = pd.to_datetime(
            result[column], format="ISO8601", errors="coerce"
        )
        if result[column].isna().any():
            raise ValueError(f"Dataset contains invalid dates in '{column}'.")
    for column in set(REQUIRED_COLUMNS) - set(NUMERIC_COLUMNS) - set(DATE_COLUMNS):
        result[column] = result[column].astype(str).str.strip()
        if result[column].eq("").any():
            raise ValueError(f"Dataset contains blank values in '{column}'.")
    return result


def load_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load only source columns; legacy notebook-derived metrics are ignored."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Restore superstore_cleaned.csv."
        )
    return validate_data(pd.read_csv(path))


def filter_data(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
    category: str | None = None,
    region: str | None = None,
    segment: str | None = None,
) -> pd.DataFrame:
    """Filter line items with inclusive calendar dates and optional dimensions."""
    mask = pd.Series(True, index=df.index)
    if start_date is not None:
        mask &= df["Order Date"] >= pd.Timestamp(start_date).normalize()
    if end_date is not None:
        mask &= df["Order Date"] < pd.Timestamp(end_date).normalize() + pd.Timedelta(
            days=1
        )
    for column, value in (
        ("Category", category),
        ("Region", region),
        ("Segment", segment),
    ):
        if value is not None:
            mask &= df[column].eq(value)
    return df.loc[mask].copy()
