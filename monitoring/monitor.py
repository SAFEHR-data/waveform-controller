#!/usr/bin/env python3
"""Scan saved HL7 messages and emit OpenTelemetry metrics.

Run in this command in dev to update the lockfile: `uv lock --script monitoring/monitor.py`
"""

import logging
import os
import sys
import time
from pathlib import Path

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "opentelemetry-exporter-otlp-proto-http==1.42.0",
# ]
# ///

INSTRUMENTATION_SCOPE = "waveform-monitoring.meter"
SAVED_MESSAGES_DIR = Path("/waveform-saved-messages")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        if default is not None:
            return default
        else:
            raise RuntimeError(f"Environment variable {name} not set")
    return value


def _scan_directory(path: Path) -> tuple[int, float | None, float | None]:
    """Return file count, newest age (seconds), oldest age (seconds)."""
    now = time.time()
    mtimes: list[float] = []

    for entry in path.rglob("*.hl7archive.bz2"):
        if entry.is_file():
            mtimes.append(entry.stat().st_mtime)

    if not mtimes:
        return 0, None, None

    newest_mtime = max(mtimes)
    oldest_mtime = min(mtimes)
    return len(mtimes), now - newest_mtime, now - oldest_mtime


def _setup_metrics(service_name: str, otlp_endpoint: str | None) -> None:
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


def main() -> int:
    service_name = _env("OTEL_SERVICE_NAME")
    otlp_endpoint = _env("OTEL_EXPORTER_OTLP_ENDPOINT")

    _setup_metrics(service_name, otlp_endpoint)

    meter = metrics.get_meter(INSTRUMENTATION_SCOPE)
    file_count = meter.create_up_down_counter(
        "waveform.monitoring.hl7bz2_files.count",
        unit="{file}",
        description="Total HL7 files in saved-messages directory",
    )
    newest_age = meter.create_gauge(
        "waveform.monitoring.hl7bz2_files.newest_age_seconds",
        unit="s",
        description="Age of the most recently modified HL7 file",
    )
    oldest_age = meter.create_gauge(
        "waveform.monitoring.hl7bz2_files.oldest_age_seconds",
        unit="s",
        description="Age of the oldest HL7 file",
    )

    if not SAVED_MESSAGES_DIR.is_dir():
        logger.warning("Saved messages directory not found: %s", SAVED_MESSAGES_DIR)
        file_count.add(0)
    else:
        count, newest_age_seconds, oldest_age_seconds = _scan_directory(
            SAVED_MESSAGES_DIR
        )
        file_count.add(count)
        if newest_age_seconds is not None:
            newest_age.set(newest_age_seconds)
        if oldest_age_seconds is not None:
            oldest_age.set(oldest_age_seconds)
        logger.info(
            "Scanned %s: count=%d newest_age=%s oldest_age=%s",
            SAVED_MESSAGES_DIR,
            count,
            f"{newest_age_seconds:.0f}s" if newest_age_seconds is not None else "n/a",
            f"{oldest_age_seconds:.0f}s" if oldest_age_seconds is not None else "n/a",
        )

    provider = metrics.get_meter_provider()
    if isinstance(provider, MeterProvider):
        provider.force_flush(timeout_millis=5000)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
