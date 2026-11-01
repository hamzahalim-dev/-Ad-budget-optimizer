"""
kpis.py — Single source of truth for KPI definitions (used by every notebook).

Rule: KPIs are always a RATIO OF TOTALS (total clicks / total impressions),
never an average of row-level ratios, which over-weights tiny rows and breaks
when a row has zero clicks or conversions.
"""
import numpy as np
import pandas as pd

METRICS = ["impressions", "clicks", "spend", "conversions", "revenue"]


def _div(a, b):
    return a / b.replace(0, np.nan)


def add_kpis(agg):
    """Add KPI columns to a DataFrame of summed base metrics."""
    t = agg.copy()
    t["CTR_%"] = 100 * _div(t["clicks"], t["impressions"])
    t["CPC"] = _div(t["spend"], t["clicks"])
    t["CVR_%"] = 100 * _div(t["conversions"], t["clicks"])
    t["CPA"] = _div(t["spend"], t["conversions"])
    t["ROAS"] = _div(t["revenue"], t["spend"])
    t["spend_share_%"] = 100 * t["spend"] / t["spend"].sum()
    t["revenue_share_%"] = 100 * t["revenue"] / t["revenue"].sum()
    return t


def kpi_table(df, by, sort_by="ROAS"):
    """Group by one or more columns, sum base metrics, add KPIs."""
    t = add_kpis(df.groupby(by, observed=True)[METRICS].sum())
    return t.sort_values(sort_by, ascending=False) if sort_by else t


def overall(df):
    """Headline KPIs for the whole dataset."""
    s = df[METRICS].sum()
    return pd.Series({
        "Total spend (Rs M)": s["spend"] / 1e6,
        "Total revenue (Rs M)": s["revenue"] / 1e6,
        "Impressions (M)": s["impressions"] / 1e6,
        "Clicks (M)": s["clicks"] / 1e6,
        "Conversions (K)": s["conversions"] / 1e3,
        "CTR %": 100 * s["clicks"] / s["impressions"],
        "CPC (Rs)": s["spend"] / s["clicks"],
        "Conversion rate %": 100 * s["conversions"] / s["clicks"],
        "CPA (Rs)": s["spend"] / s["conversions"],
        "ROAS": s["revenue"] / s["spend"],
    }).round(2)


def view(t):
    """Presentation-ready version of a kpi_table (Rs in millions, rounded)."""
    return pd.DataFrame({
        "Spend (Rs M)": t["spend"] / 1e6,
        "Revenue (Rs M)": t["revenue"] / 1e6,
        "Spend share %": t["spend_share_%"],
        "Revenue share %": t["revenue_share_%"],
        "CTR %": t["CTR_%"],
        "CPC (Rs)": t["CPC"],
        "Conv. rate %": t["CVR_%"],
        "CPA (Rs)": t["CPA"],
        "ROAS": t["ROAS"],
    }, index=t.index).round(2)
