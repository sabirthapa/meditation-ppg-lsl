from src.lsl.marker_outlet import MarkerLslOutlet


VALID_MARKERS = [
    "recording_start",
    "baseline_start",
    "baseline_end",
    "meditation_start",
    "meditation_end",
    "recording_stop",
]


def print_menu():
    print()
    print("Available markers:")
    for i, marker in enumerate(VALID_MARKERS, start=1):
        print(f"  {i}. {marker}")
    print()
    print("Type a number, marker name, or 'q' to quit.")
    print()


def main():
    print("Creating persistent LSL marker stream...")
    outlet = MarkerLslOutlet(
        stream_name="MeditationMarkers",
        source_id="meditation_marker_stream",
    )

    print()
    print("Marker stream is active:")
    print("  name: MeditationMarkers")
    print()
    print("Open LabRecorder and click Update.")
    print("Select both PPG streams and MeditationMarkers before recording.")
    print()

    while True:
        print_menu()
        user_input = input("Marker > ").strip()

        if user_input.lower() in {"q", "quit", "exit"}:
            print("Exiting marker controller.")
            break

        marker = None

        if user_input.isdigit():
            index = int(user_input)
            if 1 <= index <= len(VALID_MARKERS):
                marker = VALID_MARKERS[index - 1]
        else:
            marker = user_input

        if not marker:
            print("Invalid marker.")
            continue

        timestamp = outlet.push_marker(marker)
        print(f"Sent marker: {marker}")
        print(f"LSL timestamp: {timestamp}")


if __name__ == "__main__":
    main()
