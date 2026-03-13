import json
from pathlib import Path
import time
import random
from typing import Dict, Any, Optional

import requests
from bs4 import BeautifulSoup


URL = "https://abw.by/cars/detail/tesla/model-y/25832105"
LOCAL_FILE = "25832105.html"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36",
]


from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://abw.by/cars/detail/tesla/model-y/25832105"

# -------------------------------
# Fetch page with headers/session
# -------------------------------
def fetch_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL)
        page.wait_for_load_state("networkidle")

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    return soup


def load_local_html(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_price(soup: BeautifulSoup) -> Optional[int]:
    price = soup.select_one("[class*=price]").get_text(strip=True)
    return str(price.replace("\xa0", "")) if price else None


def parse_characteristics(soup: BeautifulSoup) -> Dict[str, Any]:
    characteristics = {}

    params = soup.select(".param")

    for idx, p in enumerate(params):
        value = p.get_text(strip=True)
        if value:
            characteristics[f"param_{idx}"] = value

    return characteristics


def parse_car(soup: BeautifulSoup) -> Dict[str, Any]:
    price = parse_price(soup)
    characteristics = parse_characteristics(soup)

    return {
        "price": price,
        "characteristics": characteristics,
    }

def main():
    soup = fetch_html(URL)
    result = parse_car(soup)
    print("PRICE:", result["price"])
    print("\nCHARACTERISTICS:")
    for k, v in result["characteristics"].items():
        print(k, ":", v)


if __name__ == "__main__":
    main()