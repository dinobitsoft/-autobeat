import json
import time
import pika

from config import RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS
from worker_logging import get_logger

logger = get_logger("message_queue")

QUEUES = ["car_pages", "car_images"]


def connect() -> pika.BlockingConnection:
    while True:
        try:
            logger.info("connecting to rabbitmq")
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            logger.info("rabbitmq connected")
            return conn
        except Exception as e:
            logger.error(f"rabbitmq connection failed: {e!r}")
            time.sleep(5)


def _make_channel(conn: pika.BlockingConnection):
    ch = conn.channel()
    for q in QUEUES:
        ch.queue_declare(queue=q, durable=True)
    logger.info("queues declared")
    return ch


_publish_conn: pika.BlockingConnection | None = None
_publish_channel = None


def _get_publish_channel():
    global _publish_conn, _publish_channel
    try:
        if _publish_conn is None or _publish_conn.is_closed:
            raise Exception("no connection")
        if _publish_channel is None or _publish_channel.is_closed:
            raise Exception("no channel")
        return _publish_channel
    except Exception:
        _publish_conn = connect()
        _publish_channel = _make_channel(_publish_conn)
        return _publish_channel


def publish(queue: str, data: dict):
    try:
        ch = _get_publish_channel()
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        _publish_conn.process_data_events()
        logger.info(f"message sent → {queue}")
    except Exception as e:
        logger.exception(f"publish failed: {e}")


def close():
    global _publish_conn, _publish_channel
    try:
        if _publish_conn and _publish_conn.is_open:
            _publish_conn.close()
    except Exception:
        pass
    _publish_conn = None
    _publish_channel = None


def consume(queue: str, callback):
    logger.info(f"consumer started for queue: {queue}")
    while True:
        try:
            conn = connect()
            ch = _make_channel(conn)
            ch.basic_qos(prefetch_count=1)

            def wrapper(ch, method, properties, body):
                data = json.loads(body)
                logger.info(f"message received from {queue}")
                try:
                    callback(data)
                except Exception as e:
                    logger.exception(f"worker failed: {e}")
                ch.basic_ack(delivery_tag=method.delivery_tag)

            ch.basic_consume(queue=queue, on_message_callback=wrapper)
            logger.info(f"waiting for messages on {queue}")
            ch.start_consuming()
        except Exception as e:
            logger.error(f"consume loop error: {e!r} — reconnecting in 5s")
            time.sleep(5)