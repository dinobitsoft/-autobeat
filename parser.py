import re
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

from worker_logging import get_logger

logger = get_logger("crawler_worker")


def parse_price(soup: BeautifulSoup) -> Optional[int]:
    price = soup.select_one("[class*=price]").get_text(strip=True)
    logger.info(f"parsed price={price} ")
    return normalize_price(price) if price else None



def parse_characteristics(soup: BeautifulSoup) -> Dict[str, Any]:
    characteristics = {}

    params = soup.select(".param")

    for idx, p in enumerate(params):
        value = p.get_text(strip=True)
        if value:
            characteristics[f"param_{idx}"] = value

    return characteristics


def normalize_price(text: str) -> int | None:
    if not text:
        return None
    if "$" in text and "≈" in text:
        text = text.split("≈")[-1]
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse(html):

    soup = BeautifulSoup(html, "html.parser")

    price = parse_price(soup)

    characteristics = parse_characteristics(soup)

    images = []

    imgs = soup.select("img")

    for img in imgs:

        src = img.get("src")

        if src and "cars" in src:
            images.append(src)

    return price, characteristics, images