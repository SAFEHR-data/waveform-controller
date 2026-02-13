import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from controller import WaveformController


@pytest.mark.parametrize(
    "opt_out, expected_accept",
    [
        [True, False],
        [False, True],
    ],
)
def test_controller_callback(monkeypatch, opt_out, expected_accept):
    emap_db_mock = Mock()
    emap_db_mock.get_row.return_value = ("mrn", "nhsno", "csn", opt_out)
    monkeypatch.setattr("controller.db.starDB", Mock(return_value=emap_db_mock))

    write_frame_mock = Mock(return_value=True)
    monkeypatch.setattr("controller.writer.write_frame", write_frame_mock)

    fake_data = {
        "sourceLocationString": "foo",
        "mappedLocationString": "loc",
        "observationTime": datetime.now().timestamp(),
        "sourceVariableId": "27",
        "sourceChannelId": "1",
        "samplingRate": 50,
        "unit": "uV",
        "numericValues": "[1,2,3]",
    }
    fake_data_str = json.dumps(fake_data)
    controller = WaveformController()

    method_frame_mock = Mock()
    delivery_tag = 12345
    method_frame_mock.delivery_tag = delivery_tag
    channel_mock = Mock()
    channel_mock.is_open = True

    controller.waveform_callback(channel_mock, method_frame_mock, None, fake_data_str)

    emap_db_mock.get_row.assert_called_once()
    if expected_accept:
        write_frame_mock.assert_called()
        channel_mock.basic_ack.assert_called_once_with(delivery_tag)
    else:
        write_frame_mock.assert_not_called()
        channel_mock.basic_reject.assert_called_once_with(delivery_tag, False)
