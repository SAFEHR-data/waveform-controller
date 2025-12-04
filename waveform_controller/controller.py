"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

import pika
import waveform_controller.db as db
import waveform_controller.settings as settings
import logging

logger = logging.getLogger(__name__)


class waveform_receiver:
    channel = None

    # set up database connection
    emap_db = db.starDB()
    emap_db.init_query()

    def on_connected(self, connection):
        """Called when we are fully connected to RabbitMQ."""
        # Open a channel
        connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, new_channel):
        """Called when our channel has opened."""
        self.channel = new_channel
        self.channel.basic_consume(
            queue=settings.RABBITMQ_QUEUE,
            on_message_callback=self.emap_db.waveform_callback,
            auto_ack=False,
        )

    def on_close(self, connection, exception):
        # Invoked when the connection is closed
        connection.ioloop.stop()

    def run(self):
        rabbitmq_credentials = pika.PlainCredentials(
            username=settings.RABBITMQ_USERNAME, password=settings.RABBITMQ_PASSWORD
        )
        connection_parameters = pika.ConnectionParameters(
            credentials=rabbitmq_credentials,
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            heartbeat=300,
        )

        connection = pika.SelectConnection(
            on_open_callback=self.on_connected,
            on_close_callback=self.on_close,
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
