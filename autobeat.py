import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from bs4 import BeautifulSoup

from models import Car, CarBrand, CarPriceHistory, CarSnapshot, Marketplace, MarketplaceBrand, utcnow
from db import get_session, init_db

_UPSERT_FIELDS = [
    "year", "body_type", "transmission", "engine", "drivetrain",
    "condition", "color", "availability", "mileage", "brand", "model",
    "generation", "modification", "description",
]


def persist_cars(scraped: List[Car]) -> tuple[int, int]:
    """Upsert scraped cars. Returns (inserted, updated) counts."""
    session = get_session()
    inserted = updated = 0
    try:
        for scraped_car in scraped:
            db_car = session.query(Car).filter_by(url=scraped_car.url).first()
            if not db_car:
                db_car = Car(url=scraped_car.url)
                session.add(db_car)
                session.flush()
                logging.info("New car: %s", scraped_car.url)
                inserted += 1
            else:
                updated += 1

            for field in _UPSERT_FIELDS:
                setattr(db_car, field, getattr(scraped_car, field))
            db_car.last_seen = utcnow()
            db_car.sold_at = None

            last_price = (
                session.query(CarPriceHistory)
                .filter_by(car_id=db_car.id)
                .order_by(CarPriceHistory.fetched_at.desc())
                .first()
            )
            price_changed = (
                not last_price
                or last_price.price != scraped_car.price
                or last_price.price_local_currency != scraped_car.price_local_currency
            )
            if price_changed:
                if last_price:
                    logging.info(
                        "Price change for %s: $%s → $%s",
                        scraped_car.url, last_price.price, scraped_car.price,
                    )
                session.add(CarPriceHistory(
                    car_id=db_car.id,
                    price=scraped_car.price,
                    price_local_currency=scraped_car.price_local_currency,
                ))

        session.commit()
    finally:
        session.close()
    return inserted, updated


def mark_sold_cars(active_urls: set) -> int:
    """Mark DB cars absent from the current scrape as sold. Returns sold count."""
    session = get_session()
    try:
        now = utcnow()
        unsold = session.query(Car).filter(Car.sold_at.is_(None)).all()
        sold_count = 0
        for car in unsold:
            if car.url not in active_urls:
                car.sold_at = now
                sold_count += 1
                logging.info("Marked as sold: %s", car.url)
        if sold_count:
            session.commit()
        return sold_count
    finally:
        session.close()


def daily_check(resume_brand: Optional[str] = None, resume_page: int = 1) -> None:
    brands = parse_brand_list(fetch_html(f"{BASE_URL}/"))
    logging.info("Found %d brands, %d cars total", len(brands), sum(b.count for b in brands))

    # skip brands before the resume point
    if resume_brand:
        brand_titles = [b.title for b in brands]
        if resume_brand in brand_titles:
            brands = brands[brand_titles.index(resume_brand):]
            logging.info("Resuming from brand '%s', page %d", resume_brand, resume_page)
        else:
            logging.warning("Resume brand '%s' not found, starting from scratch", resume_brand)
            resume_page = 1

    total_inserted = total_updated = 0
    all_urls: set = set()
    for brand in brands:
        pages = brand_page_count(brand)
        start_page = resume_page if brand.title == (resume_brand or brand.title) else 1
        logging.info("Parsing brand '%s' — %d cars, %d page(s), starting page %d", brand.title, brand.count, pages, start_page)

        cars = []
        for page in range(start_page, pages + 1):
            cars.extend(fetch_brand_page(brand, page))

        logging.info("Brand '%s' done — fetched %d cars, persisting...", brand.title, len(cars))
        inserted, updated = persist_cars(cars)
        total_inserted += inserted
        total_updated += updated
        all_urls.update(car.url for car in cars)
        resume_page = 1  # only the first brand may have a partial page offset

    total_sold = mark_sold_cars(all_urls)
    logging.info("Daily summary — inserted: %d, updated: %d, sold: %d", total_inserted, total_updated, total_sold)


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

        page.goto(url)
        page.wait_for_load_state("networkidle")

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    return soup


def load_local_html(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_price(soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
    el = soup.select_one("[class*=price]")
    if not el:
        return None, None
    raw = el.get_text(strip=True).replace("\xa0", "").replace(" ", "")
    # e.g. "69771р.≈23900$"
    parts = re.split(r"[^\d]+", raw)
    parts = [int(p) for p in parts if p.isdigit()]
    local = parts[0] if len(parts) > 0 else None
    usd   = parts[1] if len(parts) > 1 else None
    return local, usd


def parse_characteristics(soup: BeautifulSoup) -> Dict[str, Any]:
    characteristics = {}

    params = soup.select(".param")

    for idx, p in enumerate(params):
        value = p.get_text(strip=True)
        if value:
            characteristics[f"param_{idx}"] = value

    return characteristics


def parse_description(soup: BeautifulSoup) -> Dict[str, Any]:
    description = soup.select_one(".description__text")
    return description.get_text(strip=True) if description else {}


BASE_URL = "https://abw.by"



def parse_brand_list(soup: BeautifulSoup) -> List[CarBrand]:
    brands = []
    for item in soup.select("ul.cars-list li.cars-list__item"):
        link = item.select_one("a.cars-list__item__link")
        count_el = item.select_one(".cars-list__item__count")
        if not link or not count_el:
            continue
        href = link.get("href", "")
        title = href.split("brand_", 1)[-1] if "brand_" in href else None
        count = _parse_int(count_el.get_text())
        if title and count is not None:
            brands.append(CarBrand(title=title, count=count))
    return brands


def _parse_int(text: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_car_list(soup: BeautifulSoup) -> List[Car]:
    cars = []
    for article in soup.select("article.card"):
        link_el = article.select_one("a.card__link")
        if not link_el:
            continue
        href = link_el["href"]

        # extract brand/model word count from url: /cars/detail/{brand}/{model-slug}/{id}
        url_parts = href.strip("/").split("/")
        # url_parts: ["cars", "detail", "tesla", "model-y", "18612334"]
        model_slug = url_parts[3] if len(url_parts) >= 5 else ""
        model_word_count = len(model_slug.split("-"))

        # title: "Tesla Model Y I, 2025"
        title_el = article.select_one(".top__title")
        title = title_el.get_text(strip=True) if title_el else ""
        name_part, _, year = title.rpartition(", ")
        tokens = name_part.split()
        brand = tokens[0] if tokens else None
        model = " ".join(tokens[1: 1 + model_word_count]) if len(tokens) > 1 else None
        generation = " ".join(tokens[1 + model_word_count:]) or None

        # params: [mileage, "transmission, drivetrain", "engine, power", body_type]
        params = [li.get_text(strip=True) for li in article.select(".top__params li")]
        mileage     = params[0] if len(params) > 0 else None
        trans_drive = params[1].split(", ") if len(params) > 1 else []
        transmission = trans_drive[0] if trans_drive else None
        drivetrain   = trans_drive[1] if len(trans_drive) > 1 else None
        engine_raw  = params[2].split(", ") if len(params) > 2 else []
        engine      = engine_raw[0] if engine_raw else None
        body_type   = params[3] if len(params) > 3 else None

        byn_el = article.select_one(".price-byn")
        usd_el = article.select_one(".price-usd")
        price_local_currency = _parse_int(byn_el.get_text()) if byn_el else None
        price                = _parse_int(usd_el.get_text()) if usd_el else None

        cars.append(Car(
            url=BASE_URL + href,
            year=year or None,
            brand=brand,
            model=model,
            generation=generation,
            mileage=mileage,
            transmission=transmission,
            drivetrain=drivetrain,
            engine=engine,
            body_type=body_type,
            price_local_currency=price_local_currency,
            price=price,
        ))
    return cars


PARAM_TO_FIELD = {
    0: "year",
    1: "body_type",
    2: "transmission",
    3: "engine",
    4: "drivetrain",
    5: "condition",
    6: "color",
    7: "availability",
    8: "mileage",
    9: "brand",
    10: "model",
    11: "generation",
    12: "modification",
}


def parse_car(soup: BeautifulSoup, url: Optional[str] = None) -> Car:
    price_local_currency, price = parse_price(soup)
    description = parse_description(soup)
    characteristics = parse_characteristics(soup)

    car_fields = {"url": url, "price": price, "price_local_currency": price_local_currency, "description": description}
    for idx, field in PARAM_TO_FIELD.items():
        car_fields[field] = characteristics.get(f"param_{idx}")

    return Car(**car_fields)


CARS_PER_PAGE = 20


def brand_page_url(brand_title: str, page: int = 1) -> str:
    url = f"{BASE_URL}/cars/brand_{brand_title}"
    if page > 1:
        url += f"?page={page}"
    return url


def brand_page_count(brand: CarBrand) -> int:
    import math
    return math.ceil(brand.count / CARS_PER_PAGE)


def fetch_brand_page(brand: CarBrand, page: int = 1) -> List[Car]:
    url = brand_page_url(brand.title, page)
    soup = fetch_html(url)
    return parse_car_list(soup)


def fetch_all_brand_cars(brand: CarBrand) -> List[Car]:
    cars = []
    for page in range(1, brand_page_count(brand) + 1):
        cars.extend(fetch_brand_page(brand, page))
    return cars


def main() -> None:
    init_db()
    daily_check(resume_brand="peugeot", resume_page=55)


if __name__ == "__main__":
    main()