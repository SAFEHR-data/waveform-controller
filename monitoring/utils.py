import logging
import os
from typing import Optional, Any

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)

logger = logging.getLogger(__name__)


def get_env(
    name: str, default: str | None = None, as_type: Optional[type] = None
) -> Any:
    value = os.environ.get(name)
    if value is None or value == "":
        if default is not None:
            return default
        else:
            raise RuntimeError(f"Environment variable {name} not set")
    if as_type:
        return as_type(value)
    else:
        return value


def setup_metrics(service_name: str, otlp_endpoint: str | None) -> None:
    if not otlp_endpoint:
        logger.error(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set; metrics will not be exported"
        )
        return

    metrics.set_meter_provider(
        MeterProvider(
            resource=Resource.create({SERVICE_NAME: service_name}),
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(), export_interval_millis=15000
                )
            ],
        )
    )
