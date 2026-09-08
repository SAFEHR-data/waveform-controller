#!/usr/bin/env python3
"""Scan saved HL7 messages and emit OpenTelemetry metrics.

Run in this command in dev to update the lockfile: `uv lock --script monitoring/monitor.py`
"""

import logging
import shutil
import sys
import time
from pathlib import Path
from time import perf_counter

from opentelemetry import metrics
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider

import utils

# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "opentelemetry-exporter-otlp-proto-http==1.42.0",
# ]
# ///

INSTRUMENTATION_SCOPE = "waveform-monitoring.meter"
SAVED_MESSAGES_DIR = Path("/waveform-saved-messages")
WAVEFORM_EXPORT_DIR = Path("/waveform-export")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _scan_directory_ages(path: Path) -> tuple[int, float | None, float | None]:
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


def scan_hl7_bz2(meter: Meter):
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
    total_bytes = meter.create_gauge(
        "waveform.monitoring.hl7bz2_files.total_bytes",
        unit="By",
        description="Total byte count of hl7 bz2 files",
    )

    scan_time_hist = meter.create_histogram(
        "waveform.monitoring.hl7bz2_files.meta.disk_scan_time",
        unit="s",
        description="Duration of disk scan for metrics generation",
    )

    start_time = perf_counter()
    byte_count = _bytes_in_regular_files(SAVED_MESSAGES_DIR)
    total_bytes.set(byte_count)
    count, newest_age_seconds, oldest_age_seconds = _scan_directory_ages(
        SAVED_MESSAGES_DIR
    )
    time_taken = perf_counter() - start_time
    scan_time_hist.record(time_taken)
    file_count.add(count)
    if newest_age_seconds is not None:
        newest_age.set(newest_age_seconds)
    if oldest_age_seconds is not None:
        oldest_age.set(oldest_age_seconds)
    logger.info(
        "Scanned %s in %ss: count=%d newest_age=%s oldest_age=%s, bytes=%s",
        SAVED_MESSAGES_DIR,
        time_taken,
        count,
        f"{newest_age_seconds:.0f}s" if newest_age_seconds is not None else "n/a",
        f"{oldest_age_seconds:.0f}s" if oldest_age_seconds is not None else "n/a",
        byte_count,
    )


def scan_waveform_exporter_files(meter):
    scan_time_hist = meter.create_histogram(
        "waveform.monitoring.exporter.meta.disk_scan_time",
        unit="s",
        description="Duration of disk scan for metrics generation",
    )
    start_time = perf_counter()
    # dirs that contain large files where we need to track disk usage
    big_top_level_dirs = ["original-csv", "original-parquet", "pseudonymised"]
    for tld_name in big_top_level_dirs:
        tld = WAVEFORM_EXPORT_DIR / tld_name
        tld_meter_name = tld_name.replace("-", "_")
        gauge = meter.create_gauge(
            f"waveform.monitoring.{tld_meter_name}_bytes",
            unit="By",
            description=f"Bytes in the {tld_name} directory",
        )
        byte_count = _bytes_in_regular_files(tld)
        gauge.set(byte_count)
    time_taken = perf_counter() - start_time
    scan_time_hist.record(time_taken)
    logger.info("Scanned %s in %ss", WAVEFORM_EXPORT_DIR, time_taken)


def _bytes_in_regular_files(tld: Path):
    """Get sum of bytes in all regular files under the given directory."""
    byte_count = 0
    for dn, _, files in tld.walk():
        for f in files:
            f_path = dn / f
            if f_path.is_file():
                byte_count += f_path.stat().st_size
    return byte_count


def report_disk_free_space(meter: Meter):
    disk_free = meter.create_gauge(
        "waveform.monitoring.gae_disk_free",
        unit="By",
        description="Disk free on the /gae partition",
    )
    # We assume here that we are mounted onto the partition we
    # care about measuring (on the GAE this would be /gae)
    gae_free_bytes = shutil.disk_usage(SAVED_MESSAGES_DIR)
    disk_free.set(gae_free_bytes.free)


def main() -> int:
    service_name = utils.get_env("OTEL_SERVICE_NAME")
    otlp_endpoint = utils.get_env("OTEL_EXPORTER_OTLP_ENDPOINT")

    # setup
    utils.setup_metrics(service_name, otlp_endpoint)
    meter = metrics.get_meter(INSTRUMENTATION_SCOPE)

    # things to measure
    scan_hl7_bz2(meter)
    scan_waveform_exporter_files(meter)
    report_disk_free_space(meter)

    # shutdown, flush data
    provider = metrics.get_meter_provider()
    if isinstance(provider, MeterProvider):
        provider.force_flush(timeout_millis=15000)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
