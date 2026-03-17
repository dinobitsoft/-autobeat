import requests
from message_queue import consume
from storage import upload_image
from db import Session
from models import CarImage
from worker_logging import get_logger

logger = get_logger("image_worker")


def worker(data):

    url = data["url"]

    car_id = data["car_id"]

    logger.info(f"image job received {url}")

    try:

        logger.info("downloading image")

        r = requests.get(url, timeout=30)

        sha, key = upload_image(r.content)

        logger.info(f"uploaded image sha={sha}")

        db = Session()

        exists = db.query(CarImage).filter_by(sha256=sha).first()

        if exists:

            logger.info("image already stored")

        else:

            logger.info("storing new image metadata")

            db.add(
                CarImage(
                    car_id=car_id,
                    sha256=sha,
                    storage_key=key,
                    source_url=url
                )
            )

            db.commit()

        db.close()

    except Exception as e:

        logger.exception(f"image worker failed {url}: {e}")


consume("car_images", worker)