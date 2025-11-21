# headless.py
from playwright.async_api import async_playwright

async def create_undetected_headless_driver():
    """
    Start Playwright async, launch headless Chromium,
    and return (playwright, browser, context, page).
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    return pw, browser, context, page
