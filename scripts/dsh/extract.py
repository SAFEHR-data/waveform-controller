# Script to run on DSH (Windows) to move data from incoming to shared drive.
# To avoid having to deal with Python envs on the DSH, target Python 3.8
# and don't introduce non-core dependencies.
import argparse
import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path

# base paths
WAVEFORM_INCOMING = Path("Q:/emap-waveform-uploader-prod/waveform-export")
# It is very important that we don't write to any share except this one
WAVEFORM_SHARED = Path("S:/WAVEFORM")
PSEUDONYMISED = "pseudonymised"


def setup_logger():
    """Log to both screen and a log file."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    datetime_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    log_dir = Path(__file__).parent / "extract_logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / f"extract{datetime_str}.log")
    file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger = setup_logger()


def main(args):
    incoming_full_path = WAVEFORM_INCOMING / args.instance_name / PSEUDONYMISED
    extraction_output_full_path = WAVEFORM_SHARED / args.instance_name / PSEUDONYMISED
    extraction_output_full_path.parent.mkdir(parents=True, exist_ok=True)
    # Tar file names contain ISO datetime strings so will sort in the order they were uploaded.
    # By design, extracted files that appear in later uploads can overwrite those from earlier uploads if the paths match.
    ordered_tar_files = sorted(incoming_full_path.glob("*.tar"))
    logger.info(f"Found {len(ordered_tar_files)} tar files in {incoming_full_path}")
    dry_run_marker = "[DRY RUN] " if args.dry_run else ""
    for tar_to_extract in ordered_tar_files:
        logger.info(
            f"{dry_run_marker}Extracting tar file ({tar_to_extract.stat().st_size:,} bytes) {tar_to_extract}"
        )
        if not args.interactive or "y" == input("Extract? "):
            with tarfile.TarFile(tar_to_extract, mode="r") as tar_obj:
                all_members = sorted(
                    tar_obj.getmembers(), key=lambda member: member.name
                )
                for tar_member in all_members:
                    logger.info(
                        "    file [%s bytes]: %s",
                        "{: 12,}".format(tar_member.size),
                        tar_member.name,
                    )
                if not args.dry_run:
                    tar_obj.extractall(path=extraction_output_full_path)
            if not args.no_delete:
                if not args.dry_run:
                    tar_to_extract.unlink()
                logger.info(f"{dry_run_marker}Deleted {tar_to_extract}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Only print what would be done."
    )
    parser.add_argument(
        "--instance-name",
        default="production",
        help="From which named uploader instance to take data from.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively prompt before extracting/deleting each tar file.",
    )
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Do not delete the source TAR file after a successful extraction.",
    )
    args = parser.parse_args()
    main(args)
