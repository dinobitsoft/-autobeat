import json
import time
import pika

from config import RABBITMQ_HOST
from logging import getLogger

logger = getLogger("message_queue")


def connect():

    while True:

        try:

            logger.info("connecting to rabbitmq")

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )

            logger.info("rabbitmq connected")

            return connection

        except Exception as e:

            logger.error(f"rabbitmq connection failed: {e}")

            time.sleep(5)


connection = connect()

channel = connection.channel()

channel.queue_declare(queue="car_pages", durable=False)
channel.queue_declare(queue="car_images", durable=False)

logger.info("queues declared")


def publish(queue, data):

    try:

        message = json.dumps(data)

        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

        logger.info(f"message sent → {queue}")

    except Exception as e:

        logger.exception(f"publish failed: {e}")


def consume(queue, callback):

    logger.info(f"consumer started for queue {queue}")

    def wrapper(ch, method, properties, body):

        data = json.loads(body)

        logger.info(f"message received from {queue}")

        try:

            callback(data)

        except Exception as e:

            logger.exception(f"worker failed: {e}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=queue, on_message_callback=wrapper)

    channel.start_consuming()