from get_prices import get_prices
import streamlit as st
from datetime import timedelta, date
import pandas as pd
import plotly.express as px

# --- Page + styling (applies the "card" look)
st.set_page_config(layout="wide")
st.markdown("""
<style>
.card {
  background: white;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 14px;
  padding: 10px 24px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.06);
  margin-bottom: 10px;
}
h1, h2, h3 { margin: 0.1rem 0 0.6rem 0; }
.note { font-size: 18px; color: #374151; }
.badge {
  display:inline-block; padding: 6px 10px; border-radius:10px;
  background: #F3F4F6; font-weight:600; margin-right:8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Default: light mode → black text */
.card-title,
.card-subtitle,
.card-price {
    color: #000000;
}

/* Dark mode → white text */
@media (prefers-color-scheme: dark) {
    .card-title,
    .card-subtitle,
    .card-price {
        color: #ffffff !important;
    }
}
</style>
""", unsafe_allow_html=True)


def make_dashboard(brand,name):
    brand = brand.replace("(no brand)", '')
    prices = get_prices(brand, name)
    #st.write(prices)

    START_FALLBACK = date(2025, 10, 9)

    # Ensure proper types
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    prices = prices.dropna(subset=["price"])

    if prices.empty:
        st.warning("No valid prices to show.")
    else:
        hist = prices.sort_values("date")
        cur_row = hist.iloc[-1]
        cur_date = cur_row["date"]
        cur_price = float(cur_row["price"])
        cur_weight = cur_row['weight']

        window_start = cur_date - timedelta(days=30)
        last_month = hist[(hist["date"] > window_start) & (hist["date"] <= cur_date)]
        avg_30 = float(last_month["price"].mean()) if not last_month.empty else None

        max_price = float(hist["price"].max())
        min_price = float(hist["price"].min())

        def last_strict_breach(is_higher: bool):
            earlier = hist[hist["date"] < cur_date]
            if earlier.empty:
                return None
            comp = (earlier["price"] > cur_price) if is_higher else (earlier["price"] < cur_price)
            breach = earlier[comp]
            if breach.empty:
                return None
            return (cur_date - breach.iloc[-1]["date"]).days

        msg = ""
        if cur_price > hist.iloc[-2]['price']:
            days = last_strict_breach(True)
            if days:
                day_text = "1 day" if days == 1 else f"{days} days"
                msg = f"It’s the highest price over the last {day_text}."
            else:
                msg = f"It’s the highest price since at least {START_FALLBACK.strftime('%B %d, %Y')}."
        elif cur_price < hist.iloc[-2]['price']:
            days = last_strict_breach(False)
            if days:
                day_text = "1 day" if days == 1 else f"{days} days"
                msg = f"It’s the lowest price over the last {day_text}."
            else:
                msg = f"It’s the lowest price since at least {START_FALLBACK.strftime('%B %d, %Y')}."


        html = f"""
        <div class="card">
        <h1 style="color:#000000;">
            {brand} {name} (Approximate Weight: {cur_weight})
        </h1>
        <h2 style="margin-bottom:0;color:#000000;">
            Current price (as of {cur_date}): 
            <span style="font-weight:900;color:#000000;">
                ${cur_price:,.2f}
            </span>
        </h2>
        </div>
        """


        if avg_30 is not None and avg_30 != 0:
            diff_pct = (cur_price - avg_30) / avg_30 * 100
            down = cur_price < avg_30
            emoji = "⬇️" if down else ("⬆️" if diff_pct > 0.03 else "➖")
            color = "#16a34a" if down else ("#dc2626" if diff_pct > 0.03 else "#6b7280")
            html += f"""
        <span style="margin-left:12px; font-size:30px; color:{color}; font-weight:700;">
        {emoji}{diff_pct:+.1f}%
        </span>
        <span class="note" style="margin-left:6px; font-size:30px;">
        vs 30-day avg (${avg_30:,.2f})
        </span>
            """
        else:
            html += """<span style='font-size:18px; margin-left:8px;'>Not enough data for 30-day average.</span>"""

        html += "</h2>"

        if msg:
            html += f"<div style='font-size:22px; font-weight:700; margin-top:10px;'>{msg}</div>"

        html += "</div>"

        st.markdown(html, unsafe_allow_html=True)



    st.header("Price Plot")

    hist_plot = hist.copy()
    hist_plot["date"] = pd.to_datetime(hist_plot["date"])
    hist_plot["price"] = pd.to_numeric(hist_plot["price"])

    fig = px.line(
        hist_plot,
        x="date",
        y="price",
        labels={"date": "Date", "price": "Price ($)"},
    )

    fig.update_traces(
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Price: %{y:$,.2f}<extra></extra>",
        mode="lines+markers",
        marker=dict(size=8, line=dict(width=1.5, color="white")),
        line=dict(width=4),
    )

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(size=20),
        hoverlabel=dict(font_size=18),
        xaxis=dict(title_font=dict(size=22), tickfont=dict(size=18)),
        yaxis=dict(title_font=dict(size=22), tickfont=dict(size=18), tickprefix="$"),
    )

    st.plotly_chart(fig, use_container_width=True)
