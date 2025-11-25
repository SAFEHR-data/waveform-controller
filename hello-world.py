import pika
import json

"""
A script to receive messages in the waveform queue and write them to stdout, 
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

def match_waveform_to_mrn(body : dict):
    """
    Queries a star schema to find a medical record number (MRN)
    and NHS number that is likely to correspond to the 
    waveform message
    """
    return "mrn"


def waveform_callback(ch, method, properties, body):
    
    data = json.loads(body)
    #print(f"Received a waveform message {data.get('observationTime', 'NAT')}")
    print(f"Received a waveform message {data}")

def receiver():
    rabbitmq_credentials = pika.PlainCredentials(username = "my_name", password = "my_pw")
    connection_parameters = pika.ConnectionParameters(credentials = rabbitmq_credentials, host='localhost', port = 5672)
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    channel.basic_consume(queue='waveform', auto_ack = False, on_message_callback = waveform_callback)
    channel.start_consuming()


if __name__ == "__main__":
    receiver()
