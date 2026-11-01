"""
adgen.py — Synthetic digital-advertising data generator
Project: Digital Advertising Budget Optimizer (Big Data Analytics)

Grain: one row = one campaign's performance for one audience segment
(age x gender x city x device) on one day.

Every dataset size is produced by the SAME market rules below, so business
KPIs (CTR, CPC, CPA, ROAS) stay stable as the data grows; only volume changes.
"""
from __future__ import annotations

import json
import math
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

# ----------------------------------------------------------------------------
# 1. Market rules (the hidden "ground truth" of the simulation)
# ----------------------------------------------------------------------------
SEED = 42
START_DATE = "2025-11-01"
END_DATE = "2026-10-31"

COLUMNS = ["date", "campaign", "platform", "impressions", "clicks", "spend",
           "conversions", "revenue", "age", "gender", "city", "device"]

# Baseline economics per platform at normal budget pressure.
#   cpm  = cost per 1,000 impressions (Rs)     ctr = clicks / impressions
#   cvr  = conversions / clicks                 aov = average order value (Rs)
#   beta = diminishing-returns exponent (revenue ~ spend^beta; 1.0 = no saturation)
#   hist_share = how the company has historically split its ad budget
PLATFORMS = {
    "Facebook":  {"code": "FB", "hist_share": 0.30, "cpm": 150, "ctr": 0.012, "cvr": 0.020, "aov": 2000, "beta": 0.80},
    "Instagram": {"code": "IG", "hist_share": 0.25, "cpm": 180, "ctr": 0.010, "cvr": 0.020, "aov": 3200, "beta": 0.75},
    "Google":    {"code": "GG", "hist_share": 0.20, "cpm": 900, "ctr": 0.030, "cvr": 0.040, "aov": 3400, "beta": 0.65},
    "TikTok":    {"code": "TT", "hist_share": 0.15, "cpm": 70,  "ctr": 0.008, "cvr": 0.010, "aov": 2300, "beta": 0.85},
    "YouTube":   {"code": "YT", "hist_share": 0.10, "cpm": 100, "ctr": 0.004, "cvr": 0.012, "aov": 3800, "beta": 0.80},
}

AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["Male", "Female"]
CITIES = ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad",
          "Multan", "Peshawar", "Hyderabad", "Quetta", "Sialkot"]
DEVICES = ["Mobile", "Desktop", "Tablet"]
CAMPAIGN_TYPES = ["Prospecting", "Retargeting", "Brand", "Promo"]
CAMPAIGNS_PER_TYPE = [3, 2, 1, 2]          # 8 campaigns per platform, 40 total

# Audience mix per platform (probabilities, same order as the lists above)
AGE_MIX = {
    "Facebook":  [0.22, 0.34, 0.22, 0.13, 0.09],
    "Instagram": [0.38, 0.37, 0.15, 0.07, 0.03],
    "Google":    [0.18, 0.32, 0.26, 0.15, 0.09],
    "TikTok":    [0.55, 0.30, 0.10, 0.04, 0.01],
    "YouTube":   [0.28, 0.33, 0.20, 0.12, 0.07],
}
GENDER_MIX = {
    "Facebook": [0.68, 0.32], "Instagram": [0.55, 0.45], "Google": [0.62, 0.38],
    "TikTok":   [0.60, 0.40], "YouTube":   [0.70, 0.30],
}
DEVICE_MIX = {
    "Facebook": [0.88, 0.09, 0.03], "Instagram": [0.95, 0.03, 0.02],
    "Google":   [0.70, 0.27, 0.03], "TikTok":    [0.98, 0.01, 0.01],
    "YouTube":  [0.80, 0.12, 0.08],
}
CITY_MIX = [0.24, 0.22, 0.10, 0.08, 0.08, 0.06, 0.07, 0.05, 0.04, 0.06]
CAMPAIGN_TYPE_MIX = [0.45, 0.20, 0.15, 0.20]

# Performance multipliers (1.0 = average)
AGE_CTR = [1.15, 1.05, 0.95, 0.90, 0.85]
AGE_CVR = [0.75, 1.10, 1.20, 1.05, 0.85]
GENDER_CVR = [0.95, 1.10]
CITY_CVR = [1.05, 1.08, 1.20, 1.00, 0.92, 0.88, 0.90, 0.85, 0.80, 0.95]
CITY_AOV = [1.10, 1.10, 1.25, 1.00, 0.90, 0.88, 0.90, 0.85, 0.85, 0.95]
DEVICE_CTR = [1.05, 0.85, 0.95]
DEVICE_CVR = [0.92, 1.45, 1.05]
CTYPE_CTR = [1.00, 1.30, 0.70, 1.15]
CTYPE_CVR = [0.80, 1.90, 0.45, 1.20]
WEEKDAY_CVR = [1.00, 1.00, 1.00, 1.00, 0.95, 1.05, 1.10]   # Mon..Sun (Friday Jummah dip)

# Seasonal budget pressure: the company spends more around these events
SEASONS = [
    ("2025-11-07", "2025-11-30", 1.40, "11.11 / Black Friday"),
    ("2025-12-01", "2025-12-31", 1.15, "Winter & wedding season"),
    ("2026-02-18", "2026-03-09", 1.30, "Ramadan"),
    ("2026-03-10", "2026-03-21", 1.60, "Eid ul-Fitr shopping"),
    ("2026-05-20", "2026-05-27", 1.25, "Eid ul-Adha"),
    ("2026-06-15", "2026-07-31", 0.85, "Summer lull"),
    ("2026-08-08", "2026-08-14", 1.30, "Independence Day sales"),
]

ROW_SPEND_MEDIAN = 1500     # Rs per row (segment-day)
ROW_SPEND_SIGMA = 0.70
DAILY_NOISE_SIGMA = 0.25    # random day-to-day budget swings per platform

NAMES = list(PLATFORMS)


# ----------------------------------------------------------------------------
# 2. Building blocks
# ----------------------------------------------------------------------------
def _noise(rng, sigma, n):
    """Log-normal noise with mean exactly 1."""
    return rng.lognormal(-sigma ** 2 / 2, sigma, n)


def build_market_calendar(seed=SEED):
    """Daily budget-pressure index per platform (mean 1.0).
    Identical for every dataset size, so all sizes share one market history."""
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    season = np.ones(len(dates))
    for start, end, mult, _ in SEASONS:
        season[(dates >= start) & (dates <= end)] = mult
    rng = np.random.default_rng(seed + 1000)
    pressure = np.empty((len(NAMES), len(dates)))
    for i in range(len(NAMES)):
        p = season * rng.lognormal(0, DAILY_NOISE_SIGMA, len(dates))
        pressure[i] = p / p.mean()
    return dates, pressure


def _normalisers():
    """Scale CTR and CVR so each platform's average CTR and ROAS match its baseline,
    regardless of its audience mix."""
    out = {}
    wk = np.mean(WEEKDAY_CVR)
    city_val = np.dot(CITY_MIX, np.multiply(CITY_CVR, CITY_AOV))
    for name in NAMES:
        a, d = np.array(AGE_MIX[name]), np.array(DEVICE_MIX[name])
        g, c = np.array(GENDER_MIX[name]), np.array(CAMPAIGN_TYPE_MIX)
        e_ctr = np.dot(a, AGE_CTR) * np.dot(d, DEVICE_CTR) * np.dot(c, CTYPE_CTR)
        e_val = (np.dot(a, np.multiply(AGE_CTR, AGE_CVR))
                 * np.dot(d, np.multiply(DEVICE_CTR, DEVICE_CVR))
                 * np.dot(c, np.multiply(CTYPE_CTR, CTYPE_CVR))
                 * np.dot(g, GENDER_CVR) * city_val * wk)
        out[name] = (1 / e_ctr, e_ctr / e_val)
    return out


def _campaign_names():
    names = []
    for name in NAMES:
        code = PLATFORMS[name]["code"]
        for ctype, k in zip(CAMPAIGN_TYPES, CAMPAIGNS_PER_TYPE):
            names += [f"{code}_{ctype}_{j + 1:02d}" for j in range(k)]
    return names


def _draw(rng, p_idx, mix_by_platform):
    """Vectorised categorical draw where probabilities depend on the platform."""
    cdf = np.cumsum(np.array([mix_by_platform[n] for n in NAMES]), axis=1)
    cdf[:, -1] = 1.0
    u = rng.random(len(p_idx))
    return (u[:, None] > cdf[p_idx]).sum(axis=1).astype(np.int8)


def _dict_col(codes, categories):
    return pa.DictionaryArray.from_arrays(pa.array(codes.astype(np.int8)), pa.array(categories))


# ----------------------------------------------------------------------------
# 3. Chunk generator
# ----------------------------------------------------------------------------
class _Market:
    def __init__(self, seed=SEED):
        self.dates, self.pressure = build_market_calendar(seed)
        n_days = len(self.dates)
        share = np.array([PLATFORMS[n]["hist_share"] for n in NAMES])
        probs = (share[:, None] * self.pressure / n_days).ravel()
        self.cell_probs = probs / probs.sum()
        self.n_days = n_days
        self.date_values = self.dates.values.astype("datetime64[D]")
        self.weekday = self.dates.dayofweek.values
        self.norms = _normalisers()
        self.campaigns = _campaign_names()
        self.p = {k: np.array([PLATFORMS[n][k] for n in NAMES], dtype=float)
                  for k in ["cpm", "ctr", "cvr", "aov", "beta"]}
        self.ctr_norm = np.array([self.norms[n][0] for n in NAMES])
        self.cvr_norm = np.array([self.norms[n][1] for n in NAMES])


def _generate_chunk(n, rng, mk):
    """Generate n rows as a pyarrow Table (categoricals dictionary-encoded)."""
    cell = rng.choice(len(mk.cell_probs), size=n, p=mk.cell_probs)
    p_idx, d_idx = cell // mk.n_days, cell % mk.n_days
    m = mk.pressure[p_idx, d_idx]

    age = _draw(rng, p_idx, AGE_MIX)
    gender = _draw(rng, p_idx, GENDER_MIX)
    device = _draw(rng, p_idx, DEVICE_MIX)
    city = _draw(rng, p_idx, {k: CITY_MIX for k in NAMES})
    ctype = _draw(rng, p_idx, {k: CAMPAIGN_TYPE_MIX for k in NAMES})

    per_type = np.array(CAMPAIGNS_PER_TYPE)
    offset = np.concatenate([[0], np.cumsum(per_type)[:-1]])
    k = (rng.random(n) * per_type[ctype]).astype(int)
    camp = p_idx * per_type.sum() + offset[ctype] + k

    spend = np.round(rng.lognormal(math.log(ROW_SPEND_MEDIAN), ROW_SPEND_SIGMA, n), 2)
    impressions = np.maximum(1, np.round(spend / mk.p["cpm"][p_idx] * 1000 * _noise(rng, 0.15, n))).astype(np.int64)

    ctr = (mk.p["ctr"][p_idx] * mk.ctr_norm[p_idx]
           * np.take(AGE_CTR, age) * np.take(DEVICE_CTR, device) * np.take(CTYPE_CTR, ctype)
           * _noise(rng, 0.20, n))
    clicks = rng.binomial(impressions, np.clip(ctr, 0, 0.5)).astype(np.int64)

    cvr = (mk.p["cvr"][p_idx] * mk.cvr_norm[p_idx]
           * np.take(AGE_CVR, age) * np.take(GENDER_CVR, gender) * np.take(CITY_CVR, city)
           * np.take(DEVICE_CVR, device) * np.take(CTYPE_CVR, ctype)
           * np.take(WEEKDAY_CVR, mk.weekday[d_idx])
           * m ** (mk.p["beta"][p_idx] - 1)            # diminishing returns
           * _noise(rng, 0.25, n))
    conversions = rng.binomial(clicks, np.clip(cvr, 0, 0.9)).astype(np.int64)
    revenue = np.round(conversions * mk.p["aov"][p_idx] * np.take(CITY_AOV, city) * _noise(rng, 0.30, n), 2)

    return pa.table({
        "date": pa.array(mk.date_values[d_idx], type=pa.date32()),
        "campaign": _dict_col(camp, mk.campaigns),
        "platform": _dict_col(p_idx, NAMES),
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "conversions": conversions,
        "revenue": revenue,
        "age": _dict_col(age, AGE_BANDS),
        "gender": _dict_col(gender, GENDERS),
        "city": _dict_col(city, CITIES),
        "device": _dict_col(device, DEVICES),
    })


def _decode(table):
    """Turn dictionary columns into plain strings (needed for CSV)."""
    cols = [c.cast(c.type.value_type) if pa.types.is_dictionary(c.type) else c for c in table.columns]
    return pa.table(cols, names=table.column_names)


# ----------------------------------------------------------------------------
# 4. Public API
# ----------------------------------------------------------------------------
def preview(n=10, seed=SEED):
    """Small in-memory sample as a pandas DataFrame."""
    return _generate_chunk(n, np.random.default_rng(seed), _Market(seed)).to_pandas()


def _dir_mb(path):
    path = Path(path)
    files = [path] if path.is_file() else path.rglob("*")
    return sum(f.stat().st_size for f in files if f.is_file()) / 1e6


def generate_dataset(n_rows, out_dir, label, chunk_size=1_000_000, seed=SEED, overwrite=False):
    """Write n_rows to <out_dir>/csv/ads_<label>.csv and <out_dir>/parquet/ads_<label>/part-*.parquet.
    Generated in chunks, so RAM use stays flat no matter how big n_rows is."""
    out_dir = Path(out_dir)
    csv_path = out_dir / "csv" / f"ads_{label}.csv"
    pq_dir = out_dir / "parquet" / f"ads_{label}"
    if csv_path.exists() and pq_dir.exists() and not overwrite:
        print(f"[skip] {label}: already exists (set overwrite=True to rebuild)")
        return {"label": label, "rows": n_rows, "csv_mb": _dir_mb(csv_path),
                "parquet_mb": _dir_mb(pq_dir), "seconds": None}

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if pq_dir.exists():
        shutil.rmtree(pq_dir)
    pq_dir.mkdir(parents=True)

    mk = _Market(seed)
    n_chunks = math.ceil(n_rows / chunk_size)
    seeds = np.random.SeedSequence([seed, n_rows]).spawn(n_chunks)
    opts = pacsv.WriteOptions(include_header=False, quoting_style="none")
    t0, writer = time.time(), None
    sink = open(csv_path, "wb")
    sink.write((",".join(COLUMNS) + "\n").encode())          # clean, unquoted header
    try:
        for i, ss in enumerate(seeds):
            n = min(chunk_size, n_rows - i * chunk_size)
            table = _generate_chunk(n, np.random.default_rng(ss), mk)
            pq.write_table(table, pq_dir / f"part-{i:05d}.parquet", compression="snappy")
            plain = _decode(table)
            if writer is None:
                writer = pacsv.CSVWriter(sink, plain.schema, write_options=opts)
            writer.write_table(plain)
            print(f"  {label}: chunk {i + 1}/{n_chunks} ({(i * chunk_size + n):,} rows)", end="\r")
    finally:
        if writer is not None:
            writer.close()
        sink.close()
    secs = time.time() - t0
    print(f"[done] {label}: {n_rows:,} rows in {secs:.1f}s" + " " * 20)
    return {"label": label, "rows": n_rows, "csv_mb": _dir_mb(csv_path),
            "parquet_mb": _dir_mb(pq_dir), "seconds": round(secs, 1)}


def export_config(path, seed=SEED):
    """Save the market rules (answer key) as JSON, used later to validate the engine."""
    platforms = {}
    for name, p in PLATFORMS.items():
        roas = 1000 / p["cpm"] * p["ctr"] * p["cvr"] * p["aov"]
        platforms[name] = {**p, "baseline_cpc": round(p["cpm"] / 1000 / p["ctr"], 2),
                           "baseline_cpa": round(p["cpm"] / 1000 / p["ctr"] / p["cvr"], 2),
                           "baseline_roas": round(roas, 3)}
    cfg = {
        "seed": seed, "date_range": [START_DATE, END_DATE], "grain": "campaign x segment x day",
        "platforms": platforms,
        "seasons": [{"start": s, "end": e, "budget_multiplier": m, "event": n} for s, e, m, n in SEASONS],
        "row_spend": {"median_rs": ROW_SPEND_MEDIAN, "lognormal_sigma": ROW_SPEND_SIGMA},
        "daily_noise_sigma": DAILY_NOISE_SIGMA,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cfg, indent=2))
    return cfg


def quick_kpis(parquet_dir):
    """Platform-level KPIs straight from Parquet (used for sanity checks)."""
    cols = ["platform", "impressions", "clicks", "spend", "conversions", "revenue"]
    df = pq.read_table(parquet_dir, columns=cols).to_pandas()
    g = df.groupby("platform", observed=True)[cols[1:]].sum()
    return pd.DataFrame({
        "spend_share_%": 100 * g.spend / g.spend.sum(),
        "CTR_%": 100 * g.clicks / g.impressions,
        "CPC_Rs": g.spend / g.clicks,
        "CVR_%": 100 * g.conversions / g.clicks,
        "CPA_Rs": g.spend / g.conversions,
        "ROAS": g.revenue / g.spend,
    }).round(2)
