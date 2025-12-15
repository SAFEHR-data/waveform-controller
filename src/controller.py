"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import functools
import threading
import logging
import pika
import db as db  # type:ignore
import settings as settings  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)

emap_db = db.starDB()
emap_db.init_query()
emap_db.create_connection_pool()


def on_message(ch, method_frame, _header_frame, body, args):
    thrds = args
    delivery_tag = method_frame.delivery_tag
    t = threading.Thread(
        target=emap_db.waveform_callback, args=(ch, delivery_tag, body)
    )
    try:
        t.start()
    except RuntimeError as e:
        db.nack_message(ch, delivery_tag)
        logger.error(
            f"Failed to start thread, got {e}. nb. There are {len(thrds)} active threads."
        )
        return

    thrds.append(t)


def receiver():
    # set up database connection
    rabbitmq_credentials = pika.PlainCredentials(
        username=settings.RABBITMQ_USERNAME, password=settings.RABBITMQ_PASSWORD
    )
    connection_parameters = pika.ConnectionParameters(
        credentials=rabbitmq_credentials,
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
    )
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    threads = []
    on_message_callback = functools.partial(on_message, args=(threads))
    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        auto_ack=False,
        on_message_callback=on_message_callback,
    )
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    connection.close()
