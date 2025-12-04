"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import pika
import waveform_controller.db as db
import waveform_controller.settings as settings
import logging

channel = None
logger = logging.getLogger(__name__)
logging.basicConfig(filename="/dev/stdout", level=logging.ERROR)

# set up database connection
emap_db = db.starDB()
emap_db.init_query()


def on_connected(connection):
    """Called when we are fully connected to RabbitMQ."""
    # Open a channel
    connection.channel(on_open_callback=on_channel_open)


def on_channel_open(new_channel):
    """Called when our channel has opened."""
    global channel
    channel = new_channel
    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        on_message_callback=emap_db.waveform_callback,
        auto_ack=False,
    )


def on_close(connection, exception):
    # Invoked when the connection is closed
    connection.ioloop.stop()


def receiver():
    rabbitmq_credentials = pika.PlainCredentials(
        username=settings.RABBITMQ_USERNAME, password=settings.RABBITMQ_PASSWORD
    )
    connection_parameters = pika.ConnectionParameters(
        credentials=rabbitmq_credentials,
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
    )

    connection = pika.SelectConnection(
        on_open_callback=on_connected,
        on_close_callback=on_close,
        parameters=connection_parameters,
    )
    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        # Gracefully close the connection
        connection.close()
        # Loop until we're fully closed.
        # The on_close callback is required to stop the io loop
        connection.ioloop.start()
