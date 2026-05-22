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
- Historical viewer snapshots: 2025-11-13 through 2026-03-24

Some recent scrape folders are present but contain header-only CSVs because the scraper stopped returning product rows. The Streamlit app now behaves as a historical price viewer: it lets users choose an available "as of" date, loads that date's 30-day combined sliding-window CSV for the product catalog, and reconstructs full product chart history through the selected date from cached combined windows.

## App

Run the historical viewer with:

```bash
streamlit run "Dashboard Code/all_dashboard.py"
```

Use the sidebar's "As of date" selector to browse a historical snapshot. Search for a product to open its full price history chart through that selected date.

Feel free to use the data to your liking.

