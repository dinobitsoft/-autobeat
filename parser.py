import re
from bs4 import BeautifulSoup


def normalize_price(text):

    text = text.replace("\xa0", "")

    digits = re.findall(r"\d+", text)

    return int("".join(digits))


def parse(html):

    soup = BeautifulSoup(html, "html.parser")

    price_el = soup.select_one(".card-price")

    price = normalize_price(price_el.text)

    characteristics = {}

    rows = soup.select(".card-specifications__item")

    for r in rows:

        key = r.select_one(".card-specifications__name")

        val = r.select_one(".card-specifications__value")

        characteristics[key.text.strip()] = val.text.strip()

    images = []

    imgs = soup.select("img")

    for img in imgs:

        src = img.get("src")

        if src and "cars" in src:
            images.append(src)

    return price, characteristics, images