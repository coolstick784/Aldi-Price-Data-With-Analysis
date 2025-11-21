import os, re, glob
import pandas as pd
from datetime import date


def concat_data():
    # --- Config ---
    BASE_DIR = r"C:\Users\cools\grocery\aldi\data"

    today = date.today()


    # 30 days ago (inclusive) as yyyymmdd string
    start_date = today - timedelta(days=30)
    START_STR = start_date.strftime("%Y%m%d")
    END_STR = date.today().strftime("%Y%m%d")  # auto today
    USECOLS = ["brand", "name", "weight", "price"]

    # --- Helpers ---
    def is_date_folder(name):
        return bool(re.fullmatch(r"\d{8}", name))

    # --- Find date folders ---
    date_folders = [
        os.path.join(BASE_DIR, f)
        for f in os.listdir(BASE_DIR)
        if is_date_folder(f) and START_STR <= f <= END_STR
    ]

    # --- Load and combine ---
    frames = []
    for folder in sorted(date_folders):
        for csv_path in glob.glob(os.path.join(folder, "*.csv")):
            
            if "combined" in str(csv_path) or "anomalies" in str(csv_path):
                print("continuing")
                continue
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                
                continue

            # normalize column names
            df.columns = [c.lower().strip() for c in df.columns]

            # we only *require* name + price; brand can be missing
            if not {"name", "price"}.issubset(df.columns):
                continue

            # make sure all USECOLS exist; fill missing brand/weight as empty string
            for col in USECOLS:
                if col not in df.columns:
                    if col in ["brand", "name", "weight"]:
                        df[col] = ""
                    else:
                        df[col] = pd.NA

            # keep only the columns we care about (now guaranteed to exist)
            df = df[USECOLS].copy()

            # add date from folder name
            df["date"] = pd.to_datetime(os.path.basename(folder), format="%Y%m%d").date()

            # clean price column
            df["price"] = (
                df["price"]
                .astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .str.strip()
            )
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
           

            frames.append(df)

    if not frames:
        raise SystemExit("No data found in range.")

    combined = pd.concat(frames, ignore_index=True)

    # allow missing brand; just make sure it's a string
    if "brand" in combined.columns:
        combined["brand"] = combined["brand"].fillna("")

    # we only require name + price to be present
    combined = combined.dropna(subset=["name", "price"])

    # --- Save output in today’s folder ---
    today_folder = os.path.join(BASE_DIR, END_STR)
    os.makedirs(today_folder, exist_ok=True)

    output_path = os.path.join(today_folder, f"combined_{START_STR}_to_{END_STR}.csv")
    combined.to_csv(output_path, index=False)
    print("Combined CSV saved to:")
    print(output_path)


import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from pandas.api.types import is_categorical_dtype
def get_anomalies():

    # ----------------------------
    # 1) Paths (auto-adjust to today's date)
    # ----------------------------
    BASE_DIR = r"C:\Users\cools\grocery\aldi"


    today = date.today()
    today_str = today.strftime("%Y%m%d")
    start_date = today - timedelta(days=30)
    START_STR = start_date.strftime("%Y%m%d")
    folder = os.path.join(BASE_DIR, today_str)
    csv_path = os.path.join(folder, f"combined_{START_STR}_to_{today_str}.csv")

    # ----------------------------
    # 2) Load data efficiently
    # ----------------------------
    def _parse_price(x: str):
        if pd.isna(x):
            return pd.NA
        return float(str(x).replace("$", "").replace(",", "").strip())

    usecols = ["brand", "name", "weight", "price", "date"]
    dtypes = {
        "brand": "category",
        "name": "category",
        "weight": "category",
    }

    df = pd.read_csv(
        csv_path,
        usecols=usecols,
        dtype=dtypes,
        converters={"price": _parse_price},
        parse_dates=["date"],
        engine="c",
    )

    df = df.dropna(subset=["price", "date"])

    # --- Make sure missing brands are handled instead of dropped in groupby ---
    missing_brand_label = "(no brand)"

    if is_categorical_dtype(df["brand"]):
        # Add the placeholder to the categories, then fillna
        df["brand"] = df["brand"].cat.add_categories([missing_brand_label]).fillna(missing_brand_label)
    else:
        df["brand"] = df["brand"].fillna(missing_brand_label)

    # Optionally, normalize empty strings to the same placeholder
    df["brand"] = df["brand"].replace("", missing_brand_label)

    df = df.sort_values(["brand", "name", "date"], kind="mergesort")

    # ----------------------------
    # 3) Detect anomalies for the latest price of each (brand, name)
    #    - Compare latest price against all UNIQUE prices in the last 30 days
    # ----------------------------
    results = []
    manual_threshold_pct = 30.0  # e.g. 30%+ drop or spike will be caught

    for (brand, name), sub in df.groupby(["brand", "name"], sort=False):
        # Need enough history overall
        if len(sub) < 3:
            continue

        sub = sub.sort_values("date", kind="mergesort")
        latest_row = sub.iloc[-1]
        latest_price = float(latest_row["price"])
        latest_date = latest_row["date"].date()
        latest_weight = str(latest_row["weight"])

        # 30-day window ending at latest_date (inclusive)
        window_start = latest_date - timedelta(days=30)
        #print("window start", window_start)
        window_mask = (sub["date"].dt.date >= window_start) & (sub["date"].dt.date <= latest_date)
        window_sub = sub.loc[window_mask]

        if window_sub.empty:
            continue
        
        # Unique prices in that 30-day window (including the latest day)
        unique_prices = window_sub["price"].dropna().unique()
        if window_sub.iloc[0]['name'] == "Black Forest Bacon, 12 oz":
            print(unique_prices)

        # If only one unique price and latest equals it, there's nothing "weird"
        if len(unique_prices) == 1 and np.isclose(latest_price, unique_prices[0]):
            continue

        # If we don't have at least a few distinct levels, ML isn't helpful
        if len(unique_prices) < 3:
            # Simple % diff vs median of window
            median_price = float(np.median(unique_prices))
            pct_diff_vs_median = (latest_price - median_price) / median_price * 100.0
            is_manual_flag = abs(pct_diff_vs_median) >= manual_threshold_pct
            is_model_anom = False
        else:
            # --- IsolationForest on UNIQUE prices in last 30 days
            X = unique_prices.reshape(-1, 1)

            iso = IsolationForest(
                contamination=0.01,   # very small anomaly fraction
                n_estimators=80,
                max_samples="auto",
                random_state=42,
                n_jobs=1,
            )
            iso.fit(X)

            # Ask the model if the *current* price is weird compared to the unique set
            pred_latest = iso.predict([[latest_price]])[0]  # -1 = anomaly
            is_model_anom = (pred_latest == -1)

            # Manual rule: compare latest price to median of unique prices in the window
            median_price = float(np.median(unique_prices))
            pct_diff_vs_median = (latest_price - median_price) / median_price * 100.0
            is_manual_flag = abs(pct_diff_vs_median) >= manual_threshold_pct

        is_anomaly = is_model_anom or is_manual_flag
        if not is_anomaly:
            continue  # only save true anomalies

        # Direction relative to median of last-30-day unique prices
        if pct_diff_vs_median > 0:
            direction = "higher_vs_30d_median"
        elif pct_diff_vs_median < 0:
            direction = "lower_vs_30d_median"
        else:
            direction = "no_change"

        reasons = []
        if is_model_anom:
            reasons.append("model_30d_unique")
        if is_manual_flag:
            reasons.append(f"median_diff_{manual_threshold_pct:.0f}pct")

        results.append({
            "brand": str(brand),
            "name": str(name),
            "weight": latest_weight,
            "latest_date": latest_date,
            "latest_price": latest_price,
            "median_price_30d": round(median_price, 2),
            "pct_diff_vs_30d_median": round(pct_diff_vs_median, 2),
            "direction": direction,
            "reason": "|".join(reasons),
        })

    # ----------------------------
    # 4) Output anomalies only
    # ----------------------------
    out = pd.DataFrame(results)
    out_path = os.path.join(folder, f"price_anomalies_{today_str}.csv")

    if not out.empty:
        out.to_csv(out_path, index=False)
        print(f"{len(out)} anomalies saved to {out_path}")
        print(out)
    else:
        print("No anomalies detected for latest prices (vs unique prices in last 30 days).")
