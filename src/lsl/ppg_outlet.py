from pylsl import StreamInfo, StreamOutlet


class PpgLslOutlet:
    """
    Creates one LSL outlet for one wristband/participant.
    """

    def __init__(
        self,
        participant_id: str,
        stream_name: str,
        source_id: str,
        channel_count: int = 6,
        nominal_srate: float = 0.0,
    ):
        self.participant_id = participant_id
        self.stream_name = stream_name
        self.source_id = source_id
        self.channel_count = channel_count

        info = StreamInfo(
            name=stream_name,
            type="PPG",
            channel_count=channel_count,
            nominal_srate=nominal_srate,
            channel_format="float32",
            source_id=source_id,
        )

        desc = info.desc()
        desc.append_child_value("participant_id", participant_id)
        desc.append_child_value("device_type", "MAXREFDES280_OS61")
        desc.append_child_value("sensor", "wrist_ppg")
        desc.append_child_value("timestamp_clock", "pylsl.local_clock")

        channels = desc.append_child("channels")
        for i in range(channel_count):
            channel = channels.append_child("channel")
            channel.append_child_value("label", f"ppg_{i}")
            channel.append_child_value("unit", "raw")
            channel.append_child_value("type", "optical")

        self.outlet = StreamOutlet(info)

    def push_sample(self, values, timestamp):
        self.outlet.push_sample([float(v) for v in values], timestamp)
