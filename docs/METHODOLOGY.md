# Analytical methodology

The dashboard and notebook present historical observations for the active data
selection. They do not report scenario projections, annualized impacts, recovered
profit, realized savings, or causal effects.

## Data scope

The supplied data contains 9,994 transactions and 5,009 unique orders from
2011-01-04 through 2014-12-31. The raw and cleaned CSVs agree on Sales, Profit,
Discount, Order ID, Order Date, and Ship Date after parsing the raw dates as
day-month-year.

The production loader uses validated source columns and ignores notebook-derived
fields in the cleaned CSV. It checks required columns, missing and blank values,
finite numeric values, ISO dates, nonnegative Sales, and Discount in the inclusive
range [0, 1]. Invalid data raises a readable error rather than being silently
repaired or dropped.

## Metric definitions

- **Transaction:** one CSV row.
- **Unique order:** one distinct `Order ID` among selected rows. Category and
  similar filters can include only part of an order, so grouped order counts are
  not necessarily additive.
- **Profitable transaction rate:** `count(Profit > 0) / transaction count × 100`.
- **Loss-making transaction rate:** `count(Profit < 0) / transaction count × 100`.
  Zero-profit rows are break-even and remain in both rate denominators.
- **Discount groups:** `<25%` and `>=25%`. The exact-discount chart includes every
  observed value, including zero and 100%.
- **Observed gross loss exposure:** negative of the sum of negative Profit for
  rows where Discount is at least 25%.
- **High-discount group net profit:** sum of Profit across every row where Discount
  is at least 25%, including positive, negative, and break-even rows.
- **Profit margin:** `sum(Profit) / sum(Sales) × 100`. A zero-sales group displays
  0% as the documented fallback.
- **Customer value groups:** customers are ranked by selected-period net profit,
  descending, with Customer ID as the deterministic tie-breaker. The first group
  ends at `ceil(0.20 × N)` and the second at `ceil(0.50 × N)`.
- **Customer net-profit share:** group net profit divided by total selected net
  profit when the denominator is positive. Shares can be negative or exceed 100%
  when some customers have losses. A nonpositive denominator displays N/A.
- **Regional selected sales per order:** selected regional Sales divided by the
  number of distinct selected Order IDs.
- **Quarterly margin:** summed quarterly Profit divided by summed quarterly Sales.
  Calendar quarters are pooled over selected years.

## Interpretation boundaries

The data is descriptive sample data and does not identify an actual retailer's
realized business results. Discount associations do not establish causation.
Selected customer history is not a lifetime forecast. Product losses do not prove
retention effects. Partial periods do not provide equally exposed seasonal cohorts.
The 25% threshold is a descriptive cutoff rather than an experimentally established
optimal policy.

The dashboard does not infer discount dollars or list price from Sales. If Sales is
post-discount revenue, such a calculation would require assumptions and becomes
undefined at a 100% discount. Negative sales or return records would also require a
separately documented policy before inclusion.

## Reproduction and verification

```bash
python scripts/report_findings.py
python scripts/report_findings.py --check
python scripts/update_notebook_claims.py
python -m pytest -q
python -m ruff check streamlit_app.py src tests scripts
```

The Streamlit integration checks execute every dashboard tab and cover combined,
empty, and incomplete-date filters. Chart tests cover negative profit and zero-sales
behavior. The notebook executes from top to bottom with nbconvert and contains no
saved outputs, preventing old execution results from becoming repository claims.
