"""Print the same full-data findings as the app; optionally check README parity."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import calculate_kpis  # noqa: E402
from src.data import load_data  # noqa: E402
from src.insights import generate_insights  # noqa: E402

START = "<!-- findings:start -->"
END = "<!-- findings:end -->"


def findings_markdown() -> str:
    """Use production functions and identical narrative wording."""
    df = load_data()
    kpis = calculate_kpis(df)
    lines = [
        f"Full supplied dataset: **{df['Order Date'].min():%Y-%m-%d} to "
        f"{df['Order Date'].max():%Y-%m-%d}**; "
        f"**{kpis['transaction_count']:,} transactions**, "
        f"**{kpis['unique_order_count']:,} unique orders**.",
        "",
        f"Total sales: **${kpis['sales']:,.2f}**. Total profit: **${kpis['profit']:,.2f}**. "
        f"Profit margin: **{kpis['profit_margin']:.2f}%**.",
    ]
    for title, narrative in generate_insights(df):
        lines.extend(["", f"### {title}", "", narrative])
    return "\n".join(lines).replace("$", r"\$")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if README findings differ"
    )
    args = parser.parse_args()
    findings = findings_markdown()
    if args.check:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        actual = readme.split(START, 1)[1].split(END, 1)[0].strip()
        if actual != findings:
            raise SystemExit(
                "README findings differ. Regenerate with scripts/report_findings.py."
            )
        print("README findings match production calculations.")
    else:
        print(findings)
