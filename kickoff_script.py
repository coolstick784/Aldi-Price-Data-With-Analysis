# scrape.py
import asyncio
from aldi import scrape_aldi_data
from concat_data import concat_data, get_anomalies

def main():
    base_dir = r"C:\Users\cools\grocery\aldi\data"
    print("Started Aldi…")
    asyncio.run(scrape_aldi_data(base_dir))

    concat_data()
    get_anomalies()

if __name__ == "__main__":
    main()
