import re
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

from worker_logging import get_logger

logger = get_logger("crawler_worker")

CAR_CHARACTERISTIC_FIELDS = (
    "year",
    "body_type",
    "transmission",
    "engine",
    "drivetrain",
    "condition",
    "color",
    "availability",
    "mileage",
    "brand",
    "model",
    "generation",
    "modification",
)

FIELD_ALIASES = {
    "year": "year",
    "год": "year",
    "body type": "body_type",
    "кузов": "body_type",
    "transmission": "transmission",
    "коробка передач": "transmission",
    "кпп": "transmission",
    "engine": "engine",
    "двигатель": "engine",
    "drivetrain": "drivetrain",
    "привод": "drivetrain",
    "condition": "condition",
    "состояние": "condition",
    "color": "color",
    "цвет": "color",
    "availability": "availability",
    "наличие": "availability",
    "mileage": "mileage",
    "пробег": "mileage",
    "brand": "brand",
    "марка": "brand",
    "model": "model",
    "модель": "model",
    "generation": "generation",
    "поколение": "generation",
    "modification": "modification",
    "модификация": "modification",
}


def parse_price(soup: BeautifulSoup) -> Optional[int]:
    price = soup.select_one("[class*=price]").get_text(strip=True)
    logger.info(f"parsed price={price} ")
    return normalize_price(price) if price else None



def parse_characteristics(soup: BeautifulSoup) -> Dict[str, Any]:
    characteristics = {field: None for field in CAR_CHARACTERISTIC_FIELDS}

    params = soup.select(".param")

    for idx, param in enumerate(params):
        label, value = _extract_label_and_value(param)

        if not value:
            continue

        canonical_field = FIELD_ALIASES.get((label or "").strip().lower())

        if canonical_field:
            characteristics[canonical_field] = value
        else:
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


def _extract_label_and_value(param) -> tuple[str | None, str | None]:
    label_node = param.select_one(".label, .name, .title, dt, strong")
    value_node = param.select_one(".value, .text, .content, dd")

    label = label_node.get_text(" ", strip=True) if label_node else None
    value = value_node.get_text(" ", strip=True) if value_node else None

    if label and value:
        return label, value

    raw_text = param.get_text(" ", strip=True)
    if ":" in raw_text:
        left, right = raw_text.split(":", 1)
        return left.strip() or None, right.strip() or None

    return label, raw_text or None