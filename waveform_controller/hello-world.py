import pika
import waveform_controller.db as db
import waveform_controller.settings as settings

"""
A script to receive messages in the waveform queue and write them to stdout, 
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""


def match_waveform_to_mrn(body: dict):
    """
    Queries a star schema to find a medical record number (MRN)
    and NHS number that is likely to correspond to the
    waveform message
    """
    return "mrn"


def receiver():
    # set up database connection
    emap_db = db.starDB()
    emap_db.init_query()
    emap_db.connect()

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
    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        auto_ack=False,
        on_message_callback=emap_db.waveform_callback,
    )
    channel.start_consuming()


if __name__ == "__main__":
    receiver()
