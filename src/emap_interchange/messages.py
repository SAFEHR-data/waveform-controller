# Python version of interchange messages
# Ideally this would be generated automatically by the Java
# code as part of its build process, but for now it's just copied
# and modified
import json


class WaveformBaseMessage:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def from_json(json_data) -> "WaveformBaseMessage":
        data = json.loads(json_data)
        message_type = data.get("@class")
        message_cls: type
        if (
            message_type
            == "uk.ac.ucl.rits.inform.interchange.visit_observations.WaveformHighFreqMessage"
        ):
            message_cls = WaveformHighFreqMessage
        elif (
            message_type
            == "uk.ac.ucl.rits.inform.interchange.visit_observations.WaveformLowFreqMessage"
        ):
            message_cls = WaveformLowFreqMessage
        else:
            raise TypeError("Unknown message type {}".format(message_type))

        return message_cls(data)

    def get_observation_time(self):
        """Time of the observation."""
        return self.data["observationTime"]

    def get_source_location_string(self):
        """Location string according to the original data source."""
        return self.data["sourceLocationString"]

    def get_mapped_location_string(self):
        """Location string, mapped by the data source to the canonical Emap format,
        which matches what we get from the main HL7 ADT feed."""
        return self.data["mappedLocationString"]

    def get_source_observation_type(self):
        """Do we want to be more specific here?

        Eg. carescape, etc Eg. get from the CSV metadata and prefix with "waveform-"
        """
        return self.data["sourceObservationType"]

    def get_source_variable_id(self):
        """Variable ID according to the source system.

        Has previously been referred to as stream ID, so you may see that in some
        places.
        """
        return self.data["sourceVariableId"]

    def get_mapped_variable_description(self):
        """Variable (aka stream) description mapped by the data source."""
        return self.data["mappedVariableDescription"]

    def get_unit(self):
        """Unit of the measurement."""
        return self.data["unit"]


class WaveformHighFreqMessage(WaveformBaseMessage):
    def get_source_channel_id(self):
        """Channel ID according to the source system."""
        return self.data["sourceChannelId"]

    def get_sampling_rate(self):
        """Sampling rate in Hz."""
        return self.data["samplingRate"]

    def get_numeric_values(self):
        """Numeric array."""
        return self.data["numericValues"]["value"]


class WaveformLowFreqMessage(WaveformBaseMessage):
    def get_source_value(self):
        """Unmapped value."""
        return self.data["sourceValue"]["value"]

    def get_numeric_value(self):
        """Mapped value, if it's a numerical value."""
        return self.data["numericValue"]["value"]

    def get_string_value(self):
        """Mapped value, if it's a string.

        Also use for categorical, eg.  "Flow Trig"
        """
        return self.data["stringValue"]["value"]
