from pylsl import StreamInfo, StreamOutlet, local_clock


class MarkerLslOutlet:
    """
    Creates an LSL marker outlet for session events.

    Example markers:
    - recording_start
    - baseline_start
    - meditation_start
    - meditation_end
    - recording_stop
    """

    def __init__(
        self,
        stream_name: str = "MeditationMarkers",
        source_id: str = "meditation_marker_stream",
    ):
        info = StreamInfo(
            name=stream_name,
            type="Markers",
            channel_count=1,
            nominal_srate=0,
            channel_format="string",
            source_id=source_id,
        )

        desc = info.desc()
        desc.append_child_value("purpose", "meditation_session_events")
        desc.append_child_value("timestamp_clock", "pylsl.local_clock")

        self.outlet = StreamOutlet(info)
        self.stream_name = stream_name

    def push_marker(self, marker: str):
        timestamp = local_clock()
        self.outlet.push_sample([marker], timestamp)
        return timestamp
