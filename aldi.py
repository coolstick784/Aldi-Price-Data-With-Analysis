# aldi.py
import os
import datetime
import re
import pandas as pd
from headless import create_undetected_headless_driver


from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import asyncio
import itertools






def cleanAvg(weight_str: str) -> str:
    """
    Extracts the part after "avg. " and before the first "/".
    If no "/" is found, returns everything after "avg. ".
    
    Examples:
      cleanAvg("avg. 3 lb/piece")  -> "3 lb"
      cleanAvg("avg. 5kg")         -> "5kg"
      cleanAvg("total 4 lb")       -> "total 4 lb"  # unchanged
    """
    match = re.search(r"avg\.\s*([^/]+)", weight_str, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return weight_str


async def scrape_aldi_data(directory: str):
    """
    Scrape Aldi categories, enrich with nutrition, and save CSVs.
    """
    categories = [
        'fresh-produce/k/13','healthy-living/k/208','fresh-meat-seafood/k/12','snacks/k/20',
        'bbq-picnic/k/234','frozen-foods/k/14','dairy-eggs/k/10','beverages/k/7',
        'pantry-essentials/k/16','deli/k/11','bakery-bread/k/6','breakfast-cereals/k/9'
    ]

    stamp = datetime.datetime.now().strftime("%Y%m%d")
    out_dir = os.path.join(directory, stamp)
    os.makedirs(out_dir, exist_ok=True)

    pw, browser, context, page = await create_undetected_headless_driver()

    for cat in categories:
        print("Scraping", cat)
        brands, names, weights, prices = [], [], [], []


        for p in itertools.count(1):
            url = f"https://aldi.us/products/{cat}?page={p}"
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("domcontentloaded")

            # try to see product tiles; if they don't show, retry once, then quit this category
            try:
                await page.wait_for_selector('.product-teaser-item.product-grid__item', timeout=15000)
            except PlaywrightTimeoutError:
                await asyncio.sleep(2)
                await page.reload()
                await page.wait_for_load_state("domcontentloaded")
                try:
                    await page.wait_for_selector('.product-teaser-item.product-grid__item', timeout=15000)
                except PlaywrightTimeoutError:
                    # no products for this page => end the loop for this category
                    break

            items = await page.query_selector_all('.product-teaser-item.product-grid__item')
            if not items:
                # empty page => done with this category
                break

            for itm in items:
                b = await itm.query_selector('.product-tile__brandname p')
                n = await itm.query_selector('.product-tile__name p')
                w = await itm.query_selector('[data-test="product-tile__unit-of-measurement"] p')
                pr = await itm.query_selector('span.product-tile__price')

                brands.append((await b.inner_text()).strip().upper() if b else "")
                names.append((await n.inner_text()).strip() if n else "")
                cur_weight = cleanAvg((await w.inner_text()).strip() if w else "")
                weights.append(cur_weight)
                prices.append((await pr.inner_text()).strip() if pr else "")


        df = pd.DataFrame({
            "brand": brands,
            "name": names,
            "weight": weights,
            "price": prices
        })

        # df = await addNutrition_async(df)    # <-- await here
        path = os.path.join(out_dir, f"{cat.split('/')[0]}.csv")

        df.to_csv(path, index=False)
        print(f" → saved {len(df)} rows to {path}")

    await browser.close()
    await pw.stop()
    print("All done.")
