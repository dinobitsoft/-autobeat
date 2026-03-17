import requests
from bs4 import BeautifulSoup
from message_queue import publish
from worker_logging import get_logger

logger = get_logger("discovery_worker")

BASE = "https://abw.by/cars?page="


def discover():

    logger.info("starting discovery")

    for page in range(1, 100):

        logger.info(f"fetch listing page {page}")

        html = requests.get(BASE + str(page)).text

        soup = BeautifulSoup(html, "html.parser")

        links = soup.select("a[href*='/cars/detail/']")

        logger.info(f"found {len(links)} car links")

        for l in links:

            url = "https://abw.by" + l["href"]

            publish("car_pages", {"url": url})

            logger.info(f"queued {url}")


if __name__ == "__main__":

    discover()