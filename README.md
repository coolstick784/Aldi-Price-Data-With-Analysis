# Aldi Historical Price Data

Historical scraped price data from Aldi, plus a Streamlit app for browsing product price history.

Price analysis website: https://aldi-price-analysis.streamlit.app/

## Data

- Columns: brand, name, weight, price, date
- Source: Grocery data from aldi.us
- Timeframe: 2025-10-09 onward
- Latest archive folder currently checked in: 2026-05-22
- Latest non-empty combined snapshot currently checked in: 2026-04-24
- Latest actual product price date currently available: 2026-03-24
- Historical viewer sliding-window snapshot: 2026-03-24

Some recent scrape folders are present but contain header-only CSVs because the scraper stopped returning product rows. The Streamlit app now behaves as a historical price viewer: it uses the checked-in 30-day combined sliding-window CSV for March 24, 2026 instead of scanning every historical category CSV on each page load.

## App

Run the historical viewer with:

```bash
streamlit run "Dashboard Code/all_dashboard.py"
```

Use the sidebar's "As of date" selector to browse the pinned March 24, 2026 snapshot. Search for a product to open its price chart.

Feel free to use the data to your liking.

