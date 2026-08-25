from pathlib import Path
from unittest.mock import Mock

import pytest

from src.exporter import ftps


@pytest.mark.parametrize(
    ["rel_path_to_try", "should_pass"],
    [
        # These will all be turned into abs paths in the test (test params are evaluated before fixtures
        # so we can't know the tmp_path at this point)
        ["sensitive/foobar.txt", False],
        ["../sensitive/foobar.txt", False],
        ["pseudonymised/../sensitive/foobar.txt", False],
        ["pseudonymised/../../sensitive/foobar.txt", False],
        ["pseudonymised/blah/../blah/foobar.txt", True],
        ["pseudonymised/foobar.txt", True],
        ["pseudonymised/../foobar.txt", False],
        # weird cases
        ["..", False],
        ["", False],
        ["/", False],
    ],
)
def test_do_upload_input_paths(
    monkeypatch, tmp_path: Path, rel_path_to_try: str, should_pass: bool
):
    fake_abs_root = tmp_path.absolute()
    fake_waveform_pseudonymised_parquet = fake_abs_root / "pseudonymised"
    monkeypatch.setattr(
        ftps, "WAVEFORM_PSEUDONYMISED_PARQUET", fake_waveform_pseudonymised_parquet
    )

    ftp_mock = Mock()
    connect_mock = Mock(return_value=ftp_mock)
    monkeypatch.setattr(ftps, "_connect_to_ftp", connect_mock)

    # do_upload expects file to already exist, but we are setting up a test, so we must create the dir here
    # (and the file later)
    fake_waveform_pseudonymised_parquet.mkdir()
    path_to_try = fake_abs_root / rel_path_to_try
    if should_pass:
        # file needs to exist
        path_to_try.parent.mkdir(parents=True, exist_ok=True)
        path_to_try.write_text("blah")
        ftps.do_upload_multiple([path_to_try])
        assert connect_mock.called
        ftp_mock.storbinary.assert_called_once()
    else:
        # Don't create upload file as it may be outside the pytest tmp_path. We expect things to fail before that point anyway
        with pytest.raises(ValueError, match="must be under"):
            ftps.do_upload_multiple([path_to_try])
        connect_mock.assert_not_called()
