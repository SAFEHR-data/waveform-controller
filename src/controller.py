"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import functools
import json
from datetime import datetime, timedelta
import threading
import queue
import logging
import pika
import db as db  # type:ignore
import settings as settings  # type:ignore

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)

emap_db = db.starDB()
emap_db.init_query()
emap_db.create_connection_pool()

worker_queue = queue.Queue(maxsize = 1)

class waveform_message ():
    def __init__(self, ch, delivery_tag, body):
        self.ch = ch
        self.delivery_tag = delivery_tag
        self.body = body

def waveform_callback():
    message = worker_queue.get()
    logger.warn(f"Got a message {message.delivery_tag}")
    if message is not None:
        data = json.loads(message.body)
        location_string = data.get("mappedLocationString", "unknown")
        observation_time = data.get("observationTime", "NaT")
        observation_time = datetime.fromtimestamp(observation_time)
        # I found in testing that to find the first patient I had to go back 7 months. I'm not sure this
        # is expected, but I suppose an ICU patient could occupy a bed for a long time. Let's use
        # 52 weeks for now.
        start_time = observation_time - timedelta(weeks=52)
        obs_time_str = observation_time.strftime("%Y-%m-%d:%H:%M:%S")
        start_time_str = start_time.strftime("%Y-%m-%d:%H:%M:%S")
        try:
            logger.warn(f"Looking for mrn")
            matched_mrn = emap_db.get_row(location_string, start_time_str, obs_time_str)
        except ConnectionError:
            cb = functools.partial(nack_message, message.ch, message.delivery_tag)
            ch.connection.add_callback_threadsafe(cb)
            return

            if writer.write_frame(data, matched_mrn[2], matched_mrn[0]):
                cb = functools.partial(ack_message, ch, delivery_tag)
                ch.connection.add_callback_threadsafe(cb)

            worker_queue.task_done()
    else:
        logger.warning("empty message")


def on_message(ch, method_frame, _header_frame, body, args):
    worker_queue = args

    logger.warn("Got a message")
    wf_message = waveform_message(ch, method_frame.delivery_tag, body)
    if not worker_queue.full():
        worker_queue.put(wf_message)
    else:
        logger.warning("Working is queue is full.")


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

    on_message_callback = functools.partial(on_message, args=(worker_queue))
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
