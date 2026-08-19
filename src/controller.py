"""
A script to receive messages in the waveform queue and write them to stdout,
based on https://www.rabbitmq.com/tutorials/tutorial-one-python
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Literal, Any, Optional

import pika
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

import db as db  # type:ignore
import settings as settings  # type:ignore
import csv_writer as writer  # type:ignore
import telemetry as telemetry  # type:ignore
from emap_interchange.messages import (
    WaveformBaseMessage,
    WaveformHighFreqMessage,
    WaveformLowFreqMessage,
)

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)
# logger.addFilter(DedupeFilter(window_seconds=60))


class waveform_message:
    def __init__(self, ch, delivery_tag, body):
        self.ch = ch
        self.delivery_tag = delivery_tag
        self.body = body


def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which the message being
    ACKed was retrieved (AMQP protocol constraint)."""
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        logger.warning("Attempting to acknowledge a message on a closed channel.")


def reject_message(ch, delivery_tag, requeue):
    if ch.is_open:
        ch.basic_reject(delivery_tag, requeue)
    else:
        logger.warning("Attempting to not acknowledge a message on a closed channel.")


ActionType = Literal["ack", "reject"]
RejectReasonType = Literal[
    "wrong_type",
    "missing_key",
    "numeric_string_confusion",
    "db_conn_err",
    "opt_out",
    "no_ehr_lookup",
]


@dataclass(frozen=True)
class MessageOutcome:
    ch: BlockingChannel
    delivery_tag: Any
    action: ActionType
    requeue: bool = False
    reason: str | None = None
    # success-only:
    success_attrs: dict | None = None
    num_data_points: int = 0


def finalise_message(outcome: MessageOutcome):
    """Send the ack/reject to rabbitmq, and send the appropriate telemetry to Otel.

    We have a counter for ALL messages and their outcomes, and then more detailed
    counters for successful messages.
    """
    handled_attrs: dict[str, Any] = {}
    if outcome.action == "ack":
        ack_message(outcome.ch, outcome.delivery_tag)
        telemetry.messages_processed.add(1, outcome.success_attrs)
        telemetry.data_points_processed.add(
            outcome.num_data_points, outcome.success_attrs
        )
        handled_attrs["waveform.disposition"] = "success"
    elif outcome.action == "reject":
        reject_message(outcome.ch, outcome.delivery_tag, requeue=outcome.requeue)
        handled_attrs["waveform.disposition"] = (
            "requeue" if outcome.requeue else "reject"
        )
        handled_attrs["waveform.reject.reason"] = outcome.reason

        # opt-out is NOT an error, but does lead to rejection
        non_error_reasons: list[RejectReasonType] = ["opt_out"]
        if outcome.reason not in non_error_reasons:
            # Specifically use this attr name because it's an OTel convention
            # for error types https://opentelemetry.io/docs/specs/semconv/registry/attributes/error/
            handled_attrs["error.type"] = outcome.reason
    telemetry.messages_handled.add(1, handled_attrs)


class WaveformController:
    def __init__(self):
        self.emap_db = db.starDB()
        self.emap_db.init_query()
        self.emap_db.connect()

    def waveform_callback(
        self,
        ch: BlockingChannel,
        method_frame: spec.Basic.Deliver,
        _header_frame: spec.BasicProperties,
        body: bytes,
    ):
        outcome = self._process_message(ch, method_frame, _header_frame, body)
        finalise_message(outcome)

    def _process_message(
        self,
        ch: BlockingChannel,
        method_frame: spec.Basic.Deliver,
        _header_frame: spec.BasicProperties,
        body: bytes,
    ) -> MessageOutcome:
        def outcome(
            action: ActionType,
            *,
            reason: Optional[RejectReasonType] = None,
            requeue: bool = False,
            success_attrs=None,
            num_data_points=0,
        ) -> MessageOutcome:
            return MessageOutcome(
                ch,
                method_frame.delivery_tag,
                action,
                reason=reason,
                requeue=requeue,
                success_attrs=success_attrs,
                num_data_points=num_data_points,
            )

        logger.debug("Message received of length %s", len(body))
        try:
            message = WaveformBaseMessage.from_json(body)
        except TypeError as e:
            logger.error("Skipping, could not understand message type %s", e)
            return outcome("reject", reason="wrong_type", requeue=False)

        try:
            location_string = message.get_mapped_location_string()
            observation_timestamp = message.get_observation_time()
            source_variable_id = message.get_source_variable_id()
            units = message.get_unit()
            mapped_location_string = message.get_mapped_location_string()
            source_channel_id = None
            sampling_rate = None
            numeric_values = None
            string_values = None
            if isinstance(message, WaveformHighFreqMessage):
                sampling_rate = message.get_sampling_rate()
                source_channel_id = message.get_source_channel_id()
                numeric_values = message.get_numeric_values()
                logger.debug(
                    "WaveformHighFreqMessage is for loc %s, var %s, ch %s",
                    location_string,
                    source_variable_id,
                    source_channel_id,
                )
            elif isinstance(message, WaveformLowFreqMessage):
                # Wrap single values in arrays so they can go in the same
                # CSV (and parquet...) columns as for HF
                string_value = message.get_string_value()
                if string_value is not None:
                    string_values = [string_value]

                numeric_value = message.get_numeric_value()
                if numeric_value is not None:
                    numeric_values = [numeric_value]

                logger.debug(
                    "WaveformLowFreqMessage is for loc %s, var %s",
                    location_string,
                    source_variable_id,
                )
            else:
                raise RuntimeError(
                    "Unrecognized message type but should have dealt with this by now?"
                )
        except KeyError as e:
            logger.error(
                f"Waveform message {method_frame.delivery_tag} is missing required data {e}."
            )
            return outcome("reject", reason="missing_key", requeue=False)

        if (numeric_values is None) == (string_values is None):
            logger.error(
                f"Waveform message {method_frame.delivery_tag} has either both numeric and string values, or neither."
            )
            return outcome("reject", reason="numeric_string_confusion", requeue=False)

        observation_time = datetime.fromtimestamp(
            observation_timestamp, tz=timezone.utc
        )
        lookup_success = True
        try:
            matched_mrn = self.emap_db.get_row(location_string, observation_time)
        except ValueError:
            lookup_success = False
            logger.error(
                "Ambiguous or non existent match for location %s, obs time %s",
                location_string,
                observation_time,
                exc_info=True,
            )
            matched_mrn = ("unmatched_mrn", "unmatched_nhs", "unmatched_csn", False)
        except ConnectionError:
            logger.error("Database error, will try again", exc_info=True)
            return outcome("reject", reason="db_conn_err", requeue=True)

        (mrn, nhs_no, csn, opt_out) = matched_mrn
        if opt_out:
            logger.info("Research opt-out is set for mrn %s, not writing.", mrn)
            return outcome("reject", reason="opt_out", requeue=False)

        writer.write_frame(
            source_variable_id=source_variable_id,
            source_channel_id=source_channel_id,
            sampling_rate=sampling_rate,
            observation_timestamp=observation_timestamp,
            units=units,
            mapped_location_string=mapped_location_string,
            csn=csn,
            mrn=mrn,
            numeric_values=numeric_values,
            string_values=string_values,
        )
        if lookup_success:
            success_attrs = {
                # don't include CSNs until we're sure that would be acceptable
                "mapped_location_string": mapped_location_string,
                "source_variable_id": source_variable_id,
                "source_channel_id": source_channel_id,
                "message_type": str(type(message)),  # HF vs LF
            }
            if numeric_values is not None:
                num_data_points = len(numeric_values)
            else:
                assert string_values is not None
                num_data_points = len(string_values)
            return outcome(
                "ack", success_attrs=success_attrs, num_data_points=num_data_points
            )
        return outcome("reject", reason="no_ehr_lookup", requeue=False)


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
    logger.info("Connecting to RabbitMQ %s", connection_parameters)
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)

    controller = WaveformController()
    channel.basic_consume(
        queue=settings.RABBITMQ_QUEUE,
        auto_ack=False,
        on_message_callback=controller.waveform_callback,
    )
    logger.info("Connected to RabbitMQ, callback configured")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.warning("Received keyboard interrupt, exiting.")
        channel.stop_consuming()
    except Exception as e:
        logger.error("Received other exception")
        logger.error(e)
        raise e

    logger.info("Closing connection to RabbitMQ")
    connection.close()
