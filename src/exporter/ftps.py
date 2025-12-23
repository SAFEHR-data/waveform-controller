import argparse
import logging
import os
from pathlib import Path

import settings
from core.uploader._ftps import _connect_to_ftp, _create_and_set_as_cwd

from locations import WAVEFORM_PSEUDONYMISED_PARQUET

logging.basicConfig(format="%(levelname)s:%(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def do_upload_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file_to_upload",
        type=Path,
        help="file to upload relative to pseudonymised folder",
    )
    args = parser.parse_args()
    do_upload(args.file_to_upload)


def do_upload(rel_file_to_upload: Path):
    # Absolute paths override the base path, so disallow that (abspath1 / abspath2 == abspath2)
    if rel_file_to_upload.is_absolute():
        raise ValueError("File must be relative to pseudonymised folder")
    WAVEFORM_PSEUDONYMISED_PARQUET.mkdir(parents=False, exist_ok=True)
    file_to_upload = (WAVEFORM_PSEUDONYMISED_PARQUET / rel_file_to_upload).resolve(
        strict=True
    )
    # Check that even after evaluating ".." and symlinks, the file is still under the "safe" directory
    # for upload.
    if not file_to_upload.is_relative_to(WAVEFORM_PSEUDONYMISED_PARQUET):
        raise ValueError(
            f"File {file_to_upload} must be under {WAVEFORM_PSEUDONYMISED_PARQUET}. "
            f"If this is unexpected, maybe you are using symlinks or '..' in the path?"
        )
    if not file_to_upload.exists():
        raise ValueError(f"File {file_to_upload} does not exist")
    logger.info(
        "Connecting to FTPS server %s:%s, with username %s",
        settings.FTPS_HOST,
        settings.FTPS_PORT,
        settings.FTPS_USERNAME,
    )
    ftp = _connect_to_ftp(
        settings.FTPS_HOST,
        settings.FTPS_PORT,
        settings.FTPS_USERNAME,
        settings.FTPS_PASSWORD,
    )
    remote_project_dir = "waveform-export"
    _create_and_set_as_cwd(ftp, remote_project_dir)
    remote_filename = os.path.basename(file_to_upload)
    command = f"STOR {remote_filename}"
    logger.info("Uploading file %s", file_to_upload)
    with open(file_to_upload, "rb") as file_to_upload_fh:
        ftp.storbinary(command, file_to_upload_fh)
    print("Directory listing: ")
    ftp.dir()
    ftp.quit()
