#get_prices.py
# Fast historical price lookups from the checked-in 30-day sliding-window CSV.
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1] / "data"
LAST_PRICE_DATE = date(2026, 3, 24)


def normalize_end_date(end_date=None):
    if end_date is None:
        return LAST_PRICE_DATE
    if isinstance(end_date, str):
        parsed = datetime.strptime(end_date, "%Y%m%d").date()
        return min(parsed, LAST_PRICE_DATE)
    return min(end_date, LAST_PRICE_DATE)


def get_window_path(end_date=None):
    end = normalize_end_date(end_date)
    folder = BASE_DIR / end.strftime("%Y%m%d")
    matches = sorted(folder.glob("combined*.csv"))
    if not matches:
        raise FileNotFoundError(f"No combined CSV found in {folder}")
    return matches[0]


@st.cache_data(show_spinner=False)
def load_price_window(end_date_str=None):
    end = normalize_end_date(end_date_str)
    path = get_window_path(end)
    df = pd.read_csv(
        path,
        usecols=["brand", "name", "weight", "price", "date"],
    )

    df["price"] = (
        df["price"]
        .astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .astype(float)
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df["date"] <= end]

    for col in ["brand", "name", "weight"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df.sort_values(["brand", "name", "date"], kind="mergesort")


def get_prices(TARGET_BRAND, TARGET_NAME, end_date=None):
    end = normalize_end_date(end_date)
    df = load_price_window(end.strftime("%Y%m%d"))

    brand = TARGET_BRAND.replace("(no brand)", "").strip()
    name = TARGET_NAME.strip()
    if brand:
        mask = (df["brand"] == brand) & (df["name"] == name)
    else:
        mask = df["name"] == name

    out = df.loc[mask, ["date", "price", "weight"]].copy()
    out["source_csv"] = "combined"
    return out.sort_values("date")
