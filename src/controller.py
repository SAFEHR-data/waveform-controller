"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import functools
import json
from datetime import datetime
import threading
import queue
import logging
import pika
import db as db  # type:ignore
import settings as settings  # type:ignore
import csv_writer as writer  # type:ignore

max_threads = 1
logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


worker_queue: queue.Queue = queue.Queue(maxsize=max_threads)


class waveform_message:
    def __init__(self, ch, delivery_tag, body):
        self.ch = ch
        self.delivery_tag = delivery_tag
        self.body = body


def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which the
    message being ACKed was retrieved (AMQP protocol constraint)."""
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        logger.warning("Attempting to acknowledge a message on a closed channel.")


def nack_message(ch, delivery_tag, requeue):
    if ch.is_open:
        ch.basic_nack(delivery_tag, requeue)
    else:
        logger.warning("Attempting to not acknowledge a message on a closed channel.")


def waveform_callback():
    emap_db = db.starDB()
    emap_db.init_query()
    emap_db.connect()
    while True:
        message = worker_queue.get()
        if message is not None:
            data = json.loads(message.body)
            try:
                location_string = data["mappedLocationString"]
                observation_time = data["observationTime"]
            except IndexError as e:
                cb = functools.partial(
                    nack_message, message.ch, message.delivery_tag, True
                )
                message.ch.connection.add_callback_threadsafe(cb)
                logger.error(f"Waveform message is missing required data {e}")
                worker_queue.task_done()
                continue

            observation_time = datetime.fromtimestamp(observation_time)
            try:
                matched_mrn = emap_db.get_row(location_string, observation_time)
            except ValueError as e:
                cb = functools.partial(
                    nack_message, message.ch, message.delivery_tag, False
                )
                message.ch.connection.add_callback_threadsafe(cb)
                logger.error(f"Ambiguous or non existent match: {e}")
                matched_mrn = ("unmatched_mrn", "unmatched_nhs", "unmatched_csn")

            if writer.write_frame(data, matched_mrn[2], matched_mrn[0]):
                cb = functools.partial(ack_message, message.ch, message.delivery_tag)
                message.ch.connection.add_callback_threadsafe(cb)

            worker_queue.task_done()
        else:
            logger.warning("No message in queue.")


def on_message(ch, method_frame, _header_frame, body):
    wf_message = waveform_message(ch, method_frame.delivery_tag, body)
    if not worker_queue.full():
        worker_queue.put(wf_message)
    else:
        logger.warning("Working queue is full.")


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
    # I just want on thread, but in theory this should work for more
    worker_thread = threading.Thread(target=waveform_callback)
    worker_thread.start()
    threads.append(worker_thread)

    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        auto_ack=False,
        on_message_callback=on_message,
    )
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    connection.close()
