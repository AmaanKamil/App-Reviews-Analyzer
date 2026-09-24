import os
import re
import sys

from playwright.sync_api import sync_playwright

url = os.getenv("DASHBOARD_URL")
if not url or "localhost" in url:
    sys.exit("Set the DASHBOARD_URL repo secret to your *.streamlit.app URL.")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(10_000)

    wake = page.get_by_role("button", name=re.compile("get this app back up", re.I))
    if wake.count():
        print("App was asleep - waking it up.")
        wake.first.click()
        page.wait_for_timeout(60_000)
    else:
        print("App is awake.")
    browser.close()
