"""Minimal OpenTelemetry metrics: in-process counters, periodic OTLP export."""

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

import settings as settings  # type: ignore

# Instrumentation scope: to distinguish instruments
# as ours, as opposed to a library
# (pika, psycopg2, ...).
#
# Distinct from OTEL_SERVICE_NAME, which is the
# process/deployment identity.
INSTRUMENTATION_SCOPE = "waveform-controller.meter"

if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
    metrics.set_meter_provider(
        MeterProvider(
            resource=Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME}),
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(), export_interval_millis=15000
                )
            ],
        )
    )

messages_processed = metrics.get_meter(INSTRUMENTATION_SCOPE).create_counter(
    "waveform.messages.processed",
    unit="{message}",
    description="Waveform queue messages successfully written",
)

messages_handled = metrics.get_meter(INSTRUMENTATION_SCOPE).create_counter(
    "waveform.messages.handled",
    unit="{message}",
    description="Waveform queue messages handled (ack or reject)",
)

data_points_processed = metrics.get_meter(INSTRUMENTATION_SCOPE).create_counter(
    "waveform.data_points.processed",
    unit="{data_point}",
    description="Waveform data points processed successfully",
)

ftps_uploaded = metrics.get_meter(INSTRUMENTATION_SCOPE).create_counter(
    "waveform.ftps.uploaded.count",
    unit="{file}",
    description="Waveform ftps parquet file upload status",
)

ftps_time_taken = metrics.get_meter(INSTRUMENTATION_SCOPE).create_histogram(
    "waveform.ftps.uploaded.time_taken",
    unit="s",
    description="Time taken to upload a days' messages",
)
