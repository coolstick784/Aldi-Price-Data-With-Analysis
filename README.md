# Aldi Historical Price Data

Historical scraped price data from Aldi, plus a Streamlit app for browsing product price history.

Price analysis website: https://aldi-price-analysis.streamlit.app/

## Data

- Columns: brand, name, weight, price, date
- Source: Grocery data from aldi.us
- Timeframe: 2025-10-09 onward
- Latest archive folder currently checked in: 2026-05-22
- Latest non-empty combined snapshot currently checked in: 2026-04-24
- Latest actual product price date currently available: 2026-03-25

Some recent scrape folders are present but contain header-only CSVs because the scraper stopped returning product rows. The Streamlit app now behaves as a historical price viewer: it finds non-empty combined snapshots, lets you choose an "as of" date, and shows product history through that selected snapshot instead of assuming today's scrape exists.

## App

Run the historical viewer with:

```bash
streamlit run "Dashboard Code/all_dashboard.py"
```

Use the sidebar's "As of date" selector to choose the historical snapshot to browse. Search for a product to open its price chart.

Feel free to use the data to your liking.

