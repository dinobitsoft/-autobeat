from db import init_db
from message_queue import publish

init_db()

publish(
    "car_pages",
    {"url": "https://abw.by/cars/detail/tesla/model-y/25832105"}
)