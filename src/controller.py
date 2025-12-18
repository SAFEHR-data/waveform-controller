"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import json
from datetime import datetime, timezone
import logging
import pika
import db as db  # type:ignore
import settings as settings  # type:ignore
import csv_writer as writer  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


emap_db = db.starDB()
emap_db.init_query()
emap_db.connect()


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


def reject_message(ch, delivery_tag, requeue):
    if ch.is_open:
        ch.basic_reject(delivery_tag, requeue)
    else:
        logger.warning("Attempting to not acknowledge a message on a closed channel.")


def waveform_callback(ch, method_frame, _header_frame, body):
    data = json.loads(body)
    try:
        location_string = data["mappedLocationString"]
        observation_time = data["observationTime"]
    except IndexError as e:
        reject_message(ch, method_frame.delivery_tag, False)
        logger.error(
            f"Waveform message {method_frame.delivery_tag} is missing required data {e}."
        )
        return

    observation_time = datetime.fromtimestamp(observation_time, tz=timezone.utc)
    lookup_success = True
    try:
        matched_mrn = emap_db.get_row(location_string, observation_time)
    except ValueError as e:
        lookup_success = False
        logger.error(f"Ambiguous or non existent match: {e}")
        matched_mrn = ("unmatched_mrn", "unmatched_nhs", "unmatched_csn")
    except ConnectionError as e:
        logger.error(f"Database error, will try again: {e}")
        reject_message(ch, method_frame.delivery_tag, True)
        return

    if writer.write_frame(data, matched_mrn[2], matched_mrn[0]):
        if lookup_success:
            ack_message(ch, method_frame.delivery_tag)
        else:
            reject_message(ch, method_frame.delivery_tag, False)


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

    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        auto_ack=False,
        on_message_callback=waveform_callback,
    )
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()

    connection.close()
