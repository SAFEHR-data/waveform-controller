#!/usr/bin/env python3
"""Scan saved HL7 messages and emit OpenTelemetry metrics.

Run in this command in dev to update the lockfile: `uv lock --script monitoring/janitor.py`
"""

import logging
import sys
from datetime import timedelta, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Optional

from opentelemetry import metrics

import utils

# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "opentelemetry-exporter-otlp-proto-http==1.42.0",
# ]
# ///

INSTRUMENTATION_SCOPE = "waveform-janitoring.meter"
SAVED_MESSAGES_DIR = Path("/waveform-saved-messages")
WAVEFORM_EXPORT_DIR = Path("/waveform-export")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def scan_waveform_exporter_files(meter, dry_run):
    scan_time_hist = meter.create_histogram(
        "waveform.janitoring.exporter.disk_cleanup_time",
        unit="s",
        description="Duration of cleanup in exporter directory",
    )
    start_time = perf_counter()
    # Dirs that contain large files where we need to clean up.
    # Missing/blank env means do not clean up at all.
    big_top_level_dirs: dict[str, Optional[float]] = {
        "original-csv": utils.get_env("ORIGINAL_CSV_RETENTION_DAYS", None, float),
        "original-parquet": utils.get_env(
            "ORIGINAL_PARQUET_RETENTION_DAYS", None, float
        ),
        "pseudonymised": utils.get_env("PSEUDONYMISED_RETENTION_DAYS", None, float),
    }
    bytes_deleted_histo = meter.create_histogram(
        "waveform.janitoring.deleted_bytes",
        unit="By",
        description="Bytes deleted by the janitoring process",
    )
    for tld_name, retention_days in big_top_level_dirs.items():
        logger.info(f"Scanning {tld_name} for items older than {retention_days} days")
        if not retention_days:
            logger.info("Skipping %s due to empty/missing retention value", tld_name)
            continue
        tld = WAVEFORM_EXPORT_DIR / tld_name
        tld_meter_name = tld_name.replace("-", "_")
        byte_count = _delete_old_files(tld, retention_days, dry_run)
        bytes_deleted_histo.record(
            byte_count,
            attributes={
                "directory": tld_meter_name,
                "dry_run": bool(dry_run),
            },
        )
    time_taken = perf_counter() - start_time
    scan_time_hist.record(time_taken)
    logger.info("Scanned %s in %ss", WAVEFORM_EXPORT_DIR, time_taken)


def _delete_old_files(tld: Path, retention_days: float, dry_run) -> int:
    retention_threshold = datetime.now(timezone.utc) - timedelta(days=retention_days)
    retention_threshold_timestamp = retention_threshold.timestamp()
    deleted_byte_count = 0
    for dn, _, files in tld.walk():
        for f in files:
            f_path = dn / f
            if f_path.is_file():
                stat = f_path.stat()
                actual_mtime = stat.st_mtime
                if actual_mtime < retention_threshold_timestamp:
                    if not dry_run:
                        f_path.unlink()
                    logger.info(
                        "%sDeleting file [%s bytes] %s",
                        "[DRY RUN] " if dry_run else "",
                        stat.st_size,
                        f_path,
                    )
                    deleted_byte_count += stat.st_size
    return deleted_byte_count


def main(args) -> int:
    service_name = utils.get_env("OTEL_SERVICE_NAME")
    otlp_endpoint = utils.get_env("OTEL_EXPORTER_OTLP_ENDPOINT")

    # setup
    utils.setup_metrics(service_name, otlp_endpoint)
    meter = metrics.get_meter(INSTRUMENTATION_SCOPE)

    # things to clean up
    scan_waveform_exporter_files(meter, args.dry_run)

    # shutdown, flush data
    provider = metrics.get_meter_provider()
    provider.force_flush(timeout_millis=15000)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    raise SystemExit(main(args))
