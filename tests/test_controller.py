import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from controller import WaveformController


@pytest.mark.parametrize(
    "opt_out",
    [True, False],
)
@pytest.mark.parametrize(
    "db_connect_failure",
    [True, False],
)
@pytest.mark.parametrize(
    "bad_data",
    [True, False],
)
def test_controller_callback(monkeypatch, opt_out, db_connect_failure, bad_data):
    emap_db_mock = Mock()
    if db_connect_failure:
        emap_db_mock.get_row.side_effect = ConnectionError("mock database error")
    else:
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
    if bad_data:
        # simulate a missing key
        del fake_data["sourceChannelId"]
    fake_data_str = json.dumps(fake_data)
    controller = WaveformController()

    method_frame_mock = Mock()
    delivery_tag = 12345
    method_frame_mock.delivery_tag = delivery_tag
    channel_mock = Mock()
    channel_mock.is_open = True

    controller.waveform_callback(channel_mock, method_frame_mock, None, fake_data_str)

    if not bad_data:
        # we at least tried to query the DB
        emap_db_mock.get_row.assert_called_once()

    if bad_data:
        write_frame_mock.assert_not_called()
        # db should not even have been queried if data was bad
        emap_db_mock.get_row.assert_not_called()
        channel_mock.basic_reject.assert_called_once_with(delivery_tag, False)
        channel_mock.basic_ack.assert_not_called()
    elif db_connect_failure:
        # if the DB lookup failed, we should not write anything and requeue the message
        write_frame_mock.assert_not_called()
        channel_mock.basic_reject.assert_called_once_with(delivery_tag, True)
        channel_mock.basic_ack.assert_not_called()
    elif opt_out:
        # patient has opted out, dump the message
        write_frame_mock.assert_not_called()
        channel_mock.basic_reject.assert_called_once_with(delivery_tag, False)
        channel_mock.basic_ack.assert_not_called()
    else:
        # happy path
        write_frame_mock.assert_called_once()
        channel_mock.basic_reject.assert_not_called()
        channel_mock.basic_ack.assert_called_once_with(delivery_tag)
