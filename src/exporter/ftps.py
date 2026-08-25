import argparse
import logging
import os
from pathlib import Path

import settings
from core.uploader._ftps import _connect_to_ftp, _create_and_set_as_cwd

from locations import WAVEFORM_PSEUDONYMISED_PARQUET


def do_upload_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file_to_upload",
        type=Path,
        help="file to upload relative to pseudonymised folder",
    )
    args = parser.parse_args()
    do_upload_multiple(args.file_to_upload)


def do_upload_multiple(abs_files_to_upload: list[Path]):
    """We need to ensure that a user cannot accidentally ask for a file to be uploaded
    unless it's under the correct directory that we know contains pseudonymised data."""
    logger = logging.getLogger(__name__)
    # Keep things simple, paths must be absolute
    norm_files_to_upload = []
    for abs_file in abs_files_to_upload:
        if not abs_file.is_absolute():
            raise ValueError("File must be relative to pseudonymised folder")
        # Even an absolute path may contain a ".." or a symlink. Fully resolve so we
        # know what we are dealing with.
        norm_file = abs_file.resolve()
        # Check the file is still under the "safe" directory for upload.
        if not norm_file.is_relative_to(WAVEFORM_PSEUDONYMISED_PARQUET):
            raise ValueError(
                f"File {norm_file} must be under {WAVEFORM_PSEUDONYMISED_PARQUET}. "
                f"If this is unexpected, maybe you are using symlinks or '..' in the path?"
            )
        if not norm_file.exists():
            raise ValueError(f"File {norm_file} does not exist")
        norm_files_to_upload.append(norm_file)
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
    remote_project_dir = str(Path("waveform-export") / settings.INSTANCE_NAME)
    for file_to_upload in norm_files_to_upload:
        # do we need to cd back again?
        _create_and_set_as_cwd(ftp, remote_project_dir)
        remote_filename = os.path.basename(file_to_upload)
        command = f"STOR {remote_filename}"
        logger.info("Uploading file %s", file_to_upload)
        with open(file_to_upload, "rb") as file_to_upload_fh:
            resp_code = ftp.storbinary(command, file_to_upload_fh)
            logger.info("Response code: %s", resp_code)
        print("Directory listing: ")
        ftp.dir()
    ftp.quit()
