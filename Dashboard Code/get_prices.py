import re
import csv
from pathlib import Path
from datetime import datetime, date
import pandas as pd


def get_prices(TARGET_BRAND, TARGET_NAME):

    BASE_DIR = Path(__file__).resolve().parents[1] / "data" 
    START = date(2025, 10, 9)


    END = date.today()  # inclusive



    def parse_date_folder(folder_name: str):
        """Return a date from a 'YYYYMMDD' folder name or None if not valid."""
        if not re.fullmatch(r"\d{8}", folder_name):
            return None
        try:
            return datetime.strptime(folder_name, "%Y%m%d").date()
        except ValueError:
            return None

    def clean_price(val):
        """Convert prices like '$2.49', '2,49', '2.49 ' -> float. Returns None if not parseable."""
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        # Normalize thousands/commas and currency symbols
        s = s.replace("$", "").replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    def read_csv_any_encoding(path: Path) -> pd.DataFrame:
        """Try a few common encodings and return a DataFrame (empty if all fail)."""
        for enc in ("utf-8", "utf-8-sig", "cp1252"):
            try:
                return pd.read_csv(path, encoding=enc)
            except Exception:
                continue
        # Last resort: Python's csv with latin-1 then to DataFrame
        try:
            with path.open("r", encoding="latin-1", newline="") as f:
                reader = list(csv.reader(f))
            if not reader:
                return pd.DataFrame()
            header, *rows = reader
            return pd.DataFrame(rows, columns=header)
        except Exception:
            return pd.DataFrame()

    def find_price_in_folder(folder: Path):
        """Search all CSVs in a folder for the target item; return (price_float, source_file) or (None, None)."""
        for csv_file in sorted(folder.glob("*.csv")):
            if "combined" in str(csv_file):
                continue
            df = read_csv_any_encoding(csv_file)
            
            if df.empty:
                continue

            # Ensure required columns exist (case-sensitive as given)
            required = {"brand", "name", "weight", "price"}
            if not required.issubset(df.columns):
                # Try lowercase-normalization if needed
                lower_map = {c.lower(): c for c in df.columns}
                if not required.issubset(lower_map.keys()):
                    continue
                df = df.rename(columns={lower_map[k]: k for k in required})

            # Strip spaces just in case
            df["brand"] = df["brand"].astype(str).str.strip()
            df["name"]  = df["name"].astype(str).str.strip()
            df['weight'] = df["weight"].astype(str).str.strip()
            if TARGET_BRAND != '':
                mask = (df["brand"] == TARGET_BRAND) & (df["name"] == TARGET_NAME)
            else:
                mask = df['name'] == TARGET_NAME
            if mask.any():
                hit = df.loc[mask].iloc[0]
                price_val = clean_price(hit.get("price"))
                weight_val = hit.get("weight")
                return price_val, str(csv_file.name), weight_val
        return None, None, None


    rows = []
    for sub in sorted(BASE_DIR.iterdir(), key=lambda p: p.name):
        if not sub.is_dir():
            continue
        d = parse_date_folder(sub.name)
        if d is None or d < START or d > END:
            continue

        price, src, weight = find_price_in_folder(sub)
        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "price": price,
            "weight": weight,
            "source_csv": src
        })

    out = pd.DataFrame(rows).sort_values("date")
    return out