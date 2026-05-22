#get_prices.py
# Fast historical price lookups from checked-in 30-day sliding-window CSVs.
from pathlib import Path
from datetime import date, datetime, timedelta
import re

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1] / "data"
FIRST_PRICE_DATE = date(2025, 10, 9)
LAST_PRICE_DATE = date(2026, 3, 24)


def normalize_end_date(end_date=None):
    if end_date is None:
        return LAST_PRICE_DATE
    if isinstance(end_date, str):
        parsed = datetime.strptime(end_date, "%Y%m%d").date()
        return min(parsed, LAST_PRICE_DATE)
    return min(end_date, LAST_PRICE_DATE)


def parse_date_folder(folder_name):
    try:
        return datetime.strptime(folder_name, "%Y%m%d").date()
    except ValueError:
        return None


@st.cache_data(show_spinner=False)
def get_available_snapshots():
    snapshots = []
    for folder in sorted(BASE_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        if not folder.is_dir():
            continue
        folder_date = parse_date_folder(folder.name)
        if folder_date is None or folder_date > LAST_PRICE_DATE:
            continue
        matches = sorted(folder.glob("combined*.csv"))
        if not matches or matches[0].stat().st_size <= 100:
            continue
        snapshots.append({
            "date": folder_date,
            "folder": str(folder),
            "combined_path": str(matches[0]),
        })
    return snapshots


def get_window_path(end_date=None):
    end = normalize_end_date(end_date)
    folder = BASE_DIR / end.strftime("%Y%m%d")
    matches = sorted(folder.glob("combined*.csv"))
    if not matches:
        raise FileNotFoundError(f"No combined CSV found in {folder}")
    return matches[0]


def parse_combined_window(path):
    match = re.search(r"combined_(\d{8})_to_(\d{8})\.csv$", str(path))
    if not match:
        return None, None
    return (
        datetime.strptime(match.group(1), "%Y%m%d").date(),
        datetime.strptime(match.group(2), "%Y%m%d").date(),
    )


def get_history_window_paths(end_date=None):
    current_end = normalize_end_date(end_date)
    snapshots = {
        snapshot["date"]: snapshot["combined_path"]
        for snapshot in get_available_snapshots()
        if snapshot["date"] <= current_end
    }

    paths = []
    while snapshots:
        available_dates = [d for d in snapshots if d <= current_end]
        if not available_dates:
            break
        window_end = max(available_dates)
        path = snapshots[window_end]
        window_start, _ = parse_combined_window(path)
        if window_start is None:
            break

        paths.append(path)
        current_end = window_start - timedelta(days=1)

    ordered_paths = list(reversed(paths))
    all_snapshots = get_available_snapshots()
    if ordered_paths and all_snapshots:
        earliest_path = all_snapshots[-1]["combined_path"]
        earliest_start, _ = parse_combined_window(earliest_path)
        first_start, _ = parse_combined_window(ordered_paths[0])
        if earliest_start and first_start and earliest_start < first_start:
            ordered_paths.insert(0, earliest_path)

    return ordered_paths


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


@st.cache_data(show_spinner=False)
def load_full_product_history(brand, name, end_date_str):
    end = normalize_end_date(end_date_str)
    brand = brand.replace("(no brand)", "").strip()
    name = name.strip()

    frames = []
    history_paths = get_history_window_paths(end)
    first_window_start = None
    if history_paths:
        first_window_start, _ = parse_combined_window(history_paths[0])

    if first_window_start:
        for folder in sorted(BASE_DIR.iterdir(), key=lambda p: p.name):
            folder_date = parse_date_folder(folder.name)
            if (
                folder_date is None
                or folder_date < FIRST_PRICE_DATE
                or folder_date >= first_window_start
                or folder_date > end
            ):
                continue

            for csv_path in sorted(folder.glob("*.csv")):
                if "combined" in csv_path.name or "anomalies" in csv_path.name:
                    continue
                try:
                    df = pd.read_csv(
                        csv_path,
                        usecols=["brand", "name", "weight", "price"],
                    )
                except Exception:
                    continue

                df["brand"] = df["brand"].fillna("").astype(str).str.strip()
                df["name"] = df["name"].fillna("").astype(str).str.strip()
                if brand:
                    mask = (df["brand"] == brand) & (df["name"] == name)
                else:
                    mask = df["name"] == name
                hit = df.loc[mask].copy()
                if hit.empty:
                    continue

                hit["price"] = (
                    hit["price"]
                    .astype(str)
                    .str.replace(r"[$,]", "", regex=True)
                    .astype(float)
                )
                hit["date"] = folder_date
                hit["weight"] = hit["weight"].fillna("").astype(str).str.strip()
                frames.append(hit[["date", "price", "weight"]])

    for path in history_paths:
        df = pd.read_csv(
            path,
            usecols=["brand", "name", "weight", "price", "date"],
        )
        df["brand"] = df["brand"].fillna("").astype(str).str.strip()
        df["name"] = df["name"].fillna("").astype(str).str.strip()
        if brand:
            mask = (df["brand"] == brand) & (df["name"] == name)
        else:
            mask = df["name"] == name
        hit = df.loc[mask].copy()
        if hit.empty:
            continue

        hit["price"] = (
            hit["price"]
            .astype(str)
            .str.replace(r"[$,]", "", regex=True)
            .astype(float)
        )
        hit["date"] = pd.to_datetime(hit["date"]).dt.date
        hit = hit[(hit["date"] >= FIRST_PRICE_DATE) & (hit["date"] <= end)]
        hit["weight"] = hit["weight"].fillna("").astype(str).str.strip()
        frames.append(hit[["date", "price", "weight"]])

    if not frames:
        return pd.DataFrame(columns=["date", "price", "weight", "source_csv"])

    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["price"])
    out = out.drop_duplicates(subset=["date"], keep="last")
    out["source_csv"] = "combined"
    return out.sort_values("date")


def get_prices(TARGET_BRAND, TARGET_NAME, end_date=None):
    end = normalize_end_date(end_date)
    return load_full_product_history(
        TARGET_BRAND,
        TARGET_NAME,
        end.strftime("%Y%m%d"),
    )
