import copy
import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from controller import WaveformController


class FakeData:
    """Fake data to be used for building an Emap-Interchange JSON string for testing
    purposes."""

    def __init__(self, missing_key, value_type):
        self.missing_key = missing_key
        self.fake_data = FakeData._base_fake_data()
        self.value_type = value_type

    @staticmethod
    def _base_fake_data() -> dict:
        return {
            "sourceSystem": None,
            "sourceMessageId": "UCHT03ICURM09_t20240912080130_00003_1_10",
            "sourceLocationString": "foo",
            "sourceObservationType": "waveform",
            "mappedVariableDescription": "P0.1 Occlusion Pressure",
            "mappedLocationString": "loc",
            "observationTime": datetime.now().timestamp(),
            "sourceVariableId": "27",
            "unit": "uV",
        }


class FakeHFData(FakeData):
    def get_fake_data(self) -> dict:
        self.fake_data["@class"] = (
            "uk.ac.ucl.rits.inform.interchange.visit_observations.WaveformHighFreqMessage"
        )
        # simulate a missing key
        if not self.missing_key:
            self.fake_data["sourceChannelId"] = "1"
        self.fake_data["samplingRate"] = 50
        self.fake_data["numericValues"] = {
            "@class": "uk.ac.ucl.rits.inform.interchange.InterchangeValue",
            "value": [956.793, 945.615],
            "status": "SAVE",
        }
        return self.fake_data

    def get_expected_write_frame_kwargs(self) -> dict:
        """If not bad data, what should write_frame be called with?"""
        fd = self.fake_data
        return {
            "numeric_values": fd["numericValues"]["value"],
            "string_values": None,  # HF is always numeric
            "source_variable_id": fd["sourceVariableId"],
            "source_channel_id": fd["sourceChannelId"],
            "observation_timestamp": fd["observationTime"],
            "units": fd["unit"],
            "sampling_rate": fd["samplingRate"],
            "mapped_location_string": fd["mappedLocationString"],
            "csn": "csn",
            "mrn": "mrn",
        }


class FakeLFData(FakeData):
    def get_fake_data(self) -> dict:
        self.fake_data["@class"] = (
            "uk.ac.ucl.rits.inform.interchange.visit_observations.WaveformLowFreqMessage"
        )

        ignore_val = {
            "@class": "uk.ac.ucl.rits.inform.interchange.InterchangeValue",
            "value": None,
            "status": "IGNORE",
        }
        if self.value_type == "numeric":
            source_val = "0.8"
            self.fake_data["numericValue"] = {
                "@class": "uk.ac.ucl.rits.inform.interchange.InterchangeValue",
                "value": 0.8,
                "status": "SAVE",
            }
            self.fake_data["stringValue"] = copy.copy(ignore_val)
        elif self.value_type == "string":
            source_val = "some categorical"
            self.fake_data["stringValue"] = {
                "@class": "uk.ac.ucl.rits.inform.interchange.InterchangeValue",
                "value": source_val,
                "status": "SAVE",
            }
            self.fake_data["numericValue"] = copy.copy(ignore_val)
        else:
            raise ValueError("must be numeric or string")
        self.fake_data["sourceValue"] = {
            "@class": "uk.ac.ucl.rits.inform.interchange.InterchangeValue",
            "value": source_val,
            "status": "SAVE",
        }
        if self.missing_key:
            # simulate a missing key
            del self.fake_data["sourceVariableId"]
        return self.fake_data

    def get_expected_write_frame_kwargs(self) -> dict:
        """If not bad data, what should write_frame be called with?

        Keys: CSV file column names
        Values: using interchange field names
        """
        fd = self.fake_data
        expected = {
            "source_variable_id": fd["sourceVariableId"],
            "source_channel_id": None,
            "observation_timestamp": fd["observationTime"],
            "units": fd["unit"],
            "sampling_rate": None,
            "mapped_location_string": fd["mappedLocationString"],
            "csn": "csn",
            "mrn": "mrn",
        }

        # LF may be string or numeric
        expected["numeric_values"] = (
            [fd["numericValue"]["value"]] if self.value_type == "numeric" else None
        )
        expected["string_values"] = (
            [fd["stringValue"]["value"]] if self.value_type == "string" else None
        )
        return expected


@pytest.mark.parametrize(
    # only affect LF tests so is redundant for HF
    "lf_value_type",
    ["string", "numeric"],
)
@pytest.mark.parametrize(
    "fake_data_class",
    [FakeHFData, FakeLFData],
)
@pytest.mark.parametrize(
    "opt_out",
    [True, False],
)
@pytest.mark.parametrize(
    "db_connect_failure",
    [True, False],
)
@pytest.mark.parametrize(
    "bad_data_type",
    # 0 is not bad data, 1,2,3 are various different kinds of bad data
    range(4),
)
def test_controller_callback(
    monkeypatch,
    lf_value_type,
    fake_data_class,
    opt_out,
    db_connect_failure,
    bad_data_type,
):
    emap_db_mock = Mock()
    if db_connect_failure:
        emap_db_mock.get_row.side_effect = ConnectionError("mock database error")
    else:
        emap_db_mock.get_row.return_value = ("mrn", "nhsno", "csn", opt_out)
    monkeypatch.setattr("controller.db.starDB", Mock(return_value=emap_db_mock))

    write_frame_mock = Mock(return_value=True)
    monkeypatch.setattr("controller.writer.write_frame", write_frame_mock)

    # Simulate various kinds of bad data. Make sure to keep the range parameter
    # bad_data_type up to date with the number of possible failures
    fake_data_obj = fake_data_class(
        missing_key=(bad_data_type == 1), value_type=lf_value_type
    )
    fake_data = fake_data_obj.get_fake_data()
    match bad_data_type:
        case 2:
            # message type field missing
            del fake_data["@class"]
        case 3:
            # message type field present but unrecognised
            fake_data["@class"] = fake_data["@class"].replace("e", "x")
    fake_data_str = json.dumps(fake_data)
    controller = WaveformController()

    method_frame_mock = Mock()
    delivery_tag = 12345
    method_frame_mock.delivery_tag = delivery_tag
    channel_mock = Mock()
    channel_mock.is_open = True

    controller.waveform_callback(channel_mock, method_frame_mock, None, fake_data_str)

    if not bad_data_type:
        # we at least tried to query the DB
        emap_db_mock.get_row.assert_called_once()

    if bad_data_type:
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
        expected_write_frame_kwargs = fake_data_obj.get_expected_write_frame_kwargs()
        write_frame_mock.assert_called_once_with(**expected_write_frame_kwargs)
        channel_mock.basic_reject.assert_not_called()
        channel_mock.basic_ack.assert_called_once_with(delivery_tag)
