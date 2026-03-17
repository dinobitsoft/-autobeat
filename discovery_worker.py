import sys
import requests
from bs4 import BeautifulSoup
from message_queue import publish
from worker_logging import get_logger

logger = get_logger("discovery_worker")

BASE = "https://abw.by/cars?page="


def discover():
    logger.info("starting discovery")
    total = 0

    for page in range(1, 100):
        logger.info(f"fetching listing page {page}")

        try:
            r = requests.get(BASE + str(page), timeout=15)
            r.raise_for_status()
        except Exception as e:
            logger.error(f"failed to fetch page {page}: {e!r}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a[href*='/cars/detail/']")
        logger.info(f"page {page}: found {len(links)} car links")

        if not links:
            logger.warning(f"page {page}: no links — stopping (last page or selector mismatch)")
            break

        for l in links:
            url = "https://abw.by" + l["href"]
            publish("car_pages", {"url": url})
            total += 1

    logger.info(f"discovery done — queued {total} URLs total")
    if total == 0:
        logger.error("nothing was queued — check selector or site availability")
        sys.exit(1)


if __name__ == "__main__":
    discover()