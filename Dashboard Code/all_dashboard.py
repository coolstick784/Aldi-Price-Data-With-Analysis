import os
import glob
from datetime import date, timedelta

import re

from single_dashboard import make_dashboard
import pandas as pd
import streamlit as st

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1] / "data" 



def get_today_folder():
    today = date.today()
    today_str = today.strftime("%Y%m%d")
    today_folder = os.path.join(BASE_DIR, today_str)

    if os.path.isdir(today_folder):
        return today_folder

    # Fall back to yesterday if today's folder doesn't exist
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y%m%d")
    yesterday_folder = os.path.join(BASE_DIR, yesterday_str)

    if os.path.isdir(yesterday_folder):
        return yesterday_folder


def find_csv_with_prefix(folder, prefix):
    pattern = os.path.join(folder, f"{prefix}*.csv")
    matches = glob.glob(pattern)
    return matches[0] if matches else None

st.write("Today is", date.today().strftime("%Y%m%d"))

folder_today = get_today_folder()

combined_path = find_csv_with_prefix(folder_today, "combined")
anomalies_path = find_csv_with_prefix(folder_today, "price_anomalies")

if combined_path is None:
    st.error(f"No combined CSV found in {folder_today} (expected file starting with 'combined').")
    st.stop()

if anomalies_path is None:
    st.error(f"No price_anomalies CSV found in {folder_today} (expected file starting with 'price_anomalies').")
    st.stop()

# Read combined data
combined = pd.read_csv(combined_path)

# Clean up price and date
if "price" in combined.columns:
    combined["price"] = (
        combined["price"]
        .astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .astype(float)
    )

if "date" in combined.columns:
    combined["date"] = pd.to_datetime(combined["date"]).dt.date

# Make a display column for search
for col in ["brand", "name"]:
    if col not in combined.columns:
        combined[col] = ""

combined["brand"] = combined["brand"].fillna("")
combined["name"] = combined["name"].fillna("")
combined["display"] = (combined["brand"] + " " + combined["name"]).str.strip()

products = combined[["brand", "name", "display"]].drop_duplicates().reset_index(drop=True)
def normalize_text_to_tokens(text: str):
    # lower case
    text = str(text).lower()
    # normalize & ↔ and
    text = text.replace("&", " and ")
    # keep only letters/numbers, turn others into spaces
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t]
    return set(tokens)

# Precompute tokens for each product display string
products["tokens"] = products["display"].apply(normalize_text_to_tokens)


# Read anomalies data
anoms = pd.read_csv(anomalies_path)

# Ensure expected columns exist
expected_cols = [
    "brand",
    "name",
    "weight",
    "latest_date",
    "latest_price",
    "median_price_30d",
    "pct_diff_vs_30d_median",
    "direction",
    "reason",
]
missing = [c for c in expected_cols if c not in anoms.columns]
if missing:
    st.error(f"Missing expected columns in anomalies CSV: {missing}")
    st.stop()

# Clean pct_diff_vs_30d_median and latest_price
anoms["pct_diff_vs_30d_median"] = (
    anoms["pct_diff_vs_30d_median"]
    .astype(str)
    .str.replace("%", "", regex=False)
    .astype(float)
)
anoms["latest_price"] = (
    anoms["latest_price"]
    .astype(str)
    .str.replace(r"[$,]", "", regex=True)
    .astype(float)
)



st.set_page_config(layout="wide")
st.title("Aldi Price Browser")



st.markdown("---")


st.header("Search products")

query = st.text_input(
    "Search by words in brand and name (order and case don’t matter, partial words allowed):",
    placeholder="e.g. chicken breast, blueberries pint, clancy and chips...",
    key="search_query",
)




def product_matches_tokens(product_tokens: set[str], query_tokens: set[str]) -> bool:
    """
    Return True if every query token has at least one matching product token.

    Matching rules:
    - case-insensitive (handled by normalize_text_to_tokens)
    - for short words (len <= 3): require exact match
    - for longer words: allow partial match via prefix in either direction
      e.g., 'fillet' matches 'fillets' and vice versa
    """
    if not query_tokens:
        return False

    for q in query_tokens:
        found_for_q = False
        for t in product_tokens:
            if len(q) <= 3:
                # short words: exact match only
                if t == q:
                    found_for_q = True
                    break
            else:
                # longer words: prefix-based partial match
                if t.startswith(q) or q.startswith(t):
                    found_for_q = True
                    break

        if not found_for_q:
            return False

    return True


if query.strip():
    # Turn query into token set with same rules as products
    query_tokens = normalize_text_to_tokens(query)

    if not query_tokens:
        results = products.iloc[0:0].copy()
    else:
        # A product matches only if it matches ALL query tokens (with partial-token logic)
        mask = products["tokens"].apply(
            lambda ts: product_matches_tokens(ts, query_tokens)
        )
        results = products[mask].copy()
else:
    results = products.iloc[0:0].copy()

if not results.empty:
    st.write(f"Found **{len(results)}** matching product(s).")

    max_show = 50
    show_df = results.sort_values("display").head(max_show)
    display_options = show_df["display"].tolist()

    selected_display = st.selectbox(
        "Pick a product:",
        options=[""] + display_options,  # "" = no selection yet
        index=0,
        key="product_select",
    )

    if selected_display:
        chosen_row = show_df[show_df["display"] == selected_display].iloc[0]
        chosen_brand = chosen_row["brand"]
        chosen_name = chosen_row["name"]
        make_dashboard(chosen_brand, chosen_name)



else:
    if query.strip():
        st.info("No matches found. Try changing or removing a word.")


st.header("Recent price movers (based on 30-day median)")


LIST_HEIGHT = 300  

st.markdown(
    f"""
    <style>
    /* Make Streamlit columns scroll vertically once they exceed LIST_HEIGHT */
    div[data-testid="stLayoutWrapper"] {{
        max-height: {LIST_HEIGHT}px;
        overflow-y: auto;
        padding-right: 4px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_price_cards(df, kind: str):
    """
    kind = 'deal' or 'hike'
    Renders up to 30 rows from df as clickable cards.
    Clicking a card's button stores the chosen brand + name in session_state.
    """
    is_deal = (kind == "deal")
    color = "#16a34a" if is_deal else "#dc2626"  # green / red
    label_text = "Good deal" if is_deal else "Price hike"

    keep_cols = [
        "brand",
        "name",
        "weight",
        "latest_price",
        "median_price_30d",
        "pct_diff_vs_30d_median",
    ]
    if "reason" in df.columns:
        keep_cols.append("reason")

    df = df[keep_cols].reset_index(drop=True).head(30)

    for i, row in df.iterrows():
        brand = row["brand"]
        name = row["name"]
        weight = row.get("weight", "")
        latest_price = row["latest_price"]
        median_price_30d = row["median_price_30d"]
        pct_diff = row["pct_diff_vs_30d_median"]

        pct_str = f"{pct_diff:.0f}%"  # e.g. -33 -> "-33%"

        reason_html = ""
        if "reason" in row and pd.notna(row["reason"]):
            reason_html = f"""
            <div style="margin-top:4px;font-size:12px;color:#6b7280;">
                {row["reason"]}
            </div>
            """

        st.markdown(
            f"""
            <div style="
                border-radius:12px;
                padding:10px 14px;
                margin-bottom:10px;
                border:1px solid #e5e7eb;
                box-shadow:0 1px 3px rgba(0,0,0,0.06);
                background-color:white;
            ">
              <div style="font-weight:600;margin-bottom:2px;">
                {brand}
              </div>
              <div style="font-size:20px;margin-bottom:4px;">
                {name}
              </div>

              <div style="margin-top:4px;font-size:20px;">
                <span>Current:</span>
                <span style="font-weight:600;">${latest_price:.2f}</span>
                <span style="font-size:16px;color:#6b7280;">
                    (30d median ${median_price_30d:.2f})
                </span>
              </div>
              <div style="margin-top:4px;font-size:20px;">
                <span style="font-weight:600;color:{color};">
                    {label_text}: {pct_str}
                </span>
              </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "View dashboard",
            key=f"{kind}_card_btn_{i}",
            help=f"Open dashboard for {brand} - {name}",
            use_container_width=True,
        ):
            st.session_state["selected_brand"] = brand
            st.session_state["selected_name"] = name


header_deal, header_hike = st.columns(2)
with header_deal:
    st.subheader("Best deals (cheaper than usual)")
with header_hike:
    st.subheader("Biggest jumps (more expensive than usual)")
col_deals, col_hikes = st.columns(2)

with col_deals:
    
    deals = (
        anoms[anoms["pct_diff_vs_30d_median"] < 0]
        .sort_values("pct_diff_vs_30d_median")  # most negative first
    )

    if deals.empty:
        st.write("There are no great deals right now.")
    else:
        render_price_cards(deals, kind="deal")

with col_hikes:
    hikes = (
        anoms[anoms["pct_diff_vs_30d_median"] > 0]
        .sort_values("pct_diff_vs_30d_median", ascending=False)
    )

    if hikes.empty:
        st.write("There were no recent price hikes.")
    else:
        render_price_cards(hikes, kind="hike")


# ----------------- FULL-WIDTH DASHBOARD AREA ----------------- #

st.markdown("---")

if "selected_brand" in st.session_state and "selected_name" in st.session_state:
    chosen_brand = st.session_state["selected_brand"]
    chosen_name = st.session_state["selected_name"]

    make_dashboard(chosen_brand, chosen_name)
else:
    st.info("Click a product card above to open its dashboard.")
