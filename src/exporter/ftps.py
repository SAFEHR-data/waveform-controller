import argparse
import json
import logging
import tarfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
from typing import Any

from core.uploader._ftps import _connect_to_ftp, _create_and_set_as_cwd_multi_path

import settings
import telemetry
from locations import WAVEFORM_PSEUDONYMISED_PARQUET

logger = logging.getLogger(__name__)


def do_upload_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file_to_upload",
        type=Path,
        help="file to upload relative to pseudonymised folder",
    )
    args = parser.parse_args()
    do_upload_multiple(args.file_to_upload)


def do_upload_multiple_with_telemetry(
    file_list: list[Path], remote_tar_filename: str, wc_date: str
):
    start_perf = perf_counter()
    logger.info(
        "Calling do_upload_multiple to create temp tar file %s", remote_tar_filename
    )
    attrs = {
        "obs_date": wc_date,
    }
    try:
        do_upload_multiple(file_list, remote_tar_filename)
    except Exception as e:
        attrs["error.type"] = str(type(e))
        logger.exception(
            "FTPS upload failed for remote filename %s", remote_tar_filename, exc_info=e
        )
        raise
    finally:
        perf_time = perf_counter() - start_perf
        telemetry.ftps_uploaded.add(1, attributes=attrs)
        telemetry.ftps_time_taken.record(perf_time)
    return perf_time


def do_upload_multiple(
    abs_files_to_upload: list[Path], remote_tar_filename: str
) -> None:
    """We need to ensure that a user cannot accidentally ask for a file to be uploaded
    unless it's under the correct directory that we know contains pseudonymised data."""
    # Keep things simple, paths must be absolute
    rel_norm_files_to_upload = []
    for abs_file in abs_files_to_upload:
        if not abs_file.is_absolute():
            raise ValueError("File must be relative to pseudonymised folder")
        # Even an absolute path may contain a ".." or a symlink. Fully resolve so we
        # know what we are dealing with.
        norm_file = abs_file.resolve()
        # Check the file is still under the "safe" directory for upload.
        try:
            rel_norm_file = norm_file.relative_to(WAVEFORM_PSEUDONYMISED_PARQUET)
        except ValueError as e:
            raise ValueError(
                f"File {norm_file} must be under {WAVEFORM_PSEUDONYMISED_PARQUET}. "
                f"If this is unexpected, maybe you are using symlinks or '..' in the path?"
            ) from e
        if not norm_file.exists():
            raise ValueError(f"File {norm_file} does not exist")
        rel_norm_files_to_upload.append(rel_norm_file)
    # We get one notification email per file uploaded, so tar it up to reduce this.
    # Use a directory under WAVEFORM_PSEUDONYMISED_PARQUET so we keep all the pseudon data
    # in one place.
    tmp_tar_dir = WAVEFORM_PSEUDONYMISED_PARQUET / "tmp_tar"
    tmp_tar_dir.mkdir(exist_ok=True)
    remote_project_dir = (
        Path("waveform-export") / settings.INSTANCE_NAME / "pseudonymised"
    )
    logger.info(
        "tmp_tar_dir: %s,\nremote_project_dir = %s", tmp_tar_dir, remote_project_dir
    )
    with NamedTemporaryFile(
        dir=tmp_tar_dir, delete_on_close=False, delete=False
    ) as temp_tar_file_path:
        logger.info("Making temp tarfile: %s", temp_tar_file_path.name)
        with tarfile.TarFile(fileobj=temp_tar_file_path, mode="w") as tar_file:
            for file_to_upload in rel_norm_files_to_upload:
                tar_file.add(
                    WAVEFORM_PSEUDONYMISED_PARQUET / file_to_upload,
                    arcname=file_to_upload,
                )
        # tar writer has finished writing, but flush to disk and seek to beginning of file
        temp_tar_file_path.flush()
        temp_tar_file_path.seek(0)
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
        _create_and_set_as_cwd_multi_path(ftp, remote_project_dir)
        command = f"STOR {remote_tar_filename}"
        tar_file_size = Path(temp_tar_file_path.name).stat().st_size
        logger.info(
            "Uploading temp tarfile as %s in remote dir %s (%s bytes)",
            remote_tar_filename,
            remote_project_dir,
            tar_file_size,
        )
        resp_code = ftp.storbinary(command, temp_tar_file_path)
        logger.info("FTP response code: %s", resp_code)
        # I wanted to upload with a ".part" suffix, then rename to remove the
        # suffix, to make it very clear to the DSH end that the file transfer completed.
        # However, renaming results in error_perm (550 Permission denied), presumably because
        # of the write-only policy.
        print("Directory listing: ")
        ftp.dir()
        ftp.quit()


def write_ftps_sentinel(
    overall_stats_dict: dict[str, Any],
    sentinel_file: Path,
    uploaded_files: list[Path],
):
    sentinel_data = {
        "overall": overall_stats_dict,
        "uploaded_files": uploaded_files,
    }
    with open(sentinel_file, "w") as fh:
        json.dump(
            sentinel_data,
            fh,
            indent=0,
        )
