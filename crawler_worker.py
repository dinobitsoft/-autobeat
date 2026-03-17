from playwright.sync_api import sync_playwright
import hashlib
from parser import parse
from message_queue import consume, publish
from db import Session
from models import Car, CarSnapshot
from datetime import datetime
from worker_logging import get_logger

logger = get_logger("crawler_worker")


def worker(data):

    url = data["url"]

    logger.info(f"received crawl job: {url}")

    try:

        with sync_playwright() as p:

            logger.info("starting browser")

            browser = p.chromium.launch()

            page = browser.new_page()

            logger.info(f"loading page {url}")

            page.goto(url)

            page.wait_for_load_state("networkidle")

            html = page.content()

            browser.close()

        logger.info("page loaded")

        price, characteristics, images = parse(html)

        logger.info(f"parsed price={price} images={len(images)}")

        snapshot_hash = hashlib.sha256(
            (str(price) + str(characteristics)).encode()
        ).hexdigest()

        db = Session()

        car = db.query(Car).filter_by(source_url=url).first()

        if not car:

            logger.info("creating new car record")

            car = Car(source_url=url)

            db.add(car)

            db.commit()

        snapshot = db.query(CarSnapshot).filter_by(
            snapshot_hash=snapshot_hash
        ).first()

        if snapshot:

            logger.info("snapshot unchanged — updating last_seen")

            snapshot.last_seen = datetime.utcnow()

        else:

            logger.info("new snapshot detected — inserting")

            db.add(
                CarSnapshot(
                    car_id=car.id,
                    price=price,
                    characteristics=characteristics,
                    snapshot_hash=snapshot_hash
                )
            )

        db.commit()

        for img in images:

            publish("car_images", {"url": img, "car_id": car.id})

        logger.info(f"queued {len(images)} images")

        db.close()

    except Exception as e:

        logger.exception(f"worker failed for {url}: {e}")


consume("car_pages", worker)