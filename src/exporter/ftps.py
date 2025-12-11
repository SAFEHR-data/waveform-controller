import os
from typing import BinaryIO

from core.uploader._ftps import _connect_to_ftp
import settings
import argparse


def do_upload():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_to_upload", type=str, help="file to upload")
    args = parser.parse_args()
    do_upload_inner(args.file_to_upload)


def do_upload_inner(file_to_upload):
    ftp = _connect_to_ftp(settings.FTPS_HOST, settings.FTPS_PORT, settings.FTPS_USERNAME, settings.FTPS_PASSWORD)
    project_dir = "foobar_waveform"
    # ftp.mkd(project_dir)
    ftp.cwd(project_dir)
    remote_filename = os.path.basename(file_to_upload)
    command = f"STOR {remote_filename}"
    # BinaryIO
    print("PWD: " + ftp.pwd())
    with open(file_to_upload, 'rb') as file_to_upload_fh:
        ftp.storbinary(command, file_to_upload_fh)
    ftp.dir()
    print("Done dir")
    ftp.quit()
