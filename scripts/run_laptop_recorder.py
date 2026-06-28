import argparse
import time

from src.band.ppg_session import PpgSession
from src.band.single_band_connector import connect_single_band
from src.lsl.ppg_outlet import PpgLslOutlet
from src.utils.config_loader import load_config


def start_band_recorder(
    band_config: dict,
    scan_seconds: int,
    match_by_name: bool = False,
    name_filter: str = "OS61",
    exclude_addresses: set = None,
):
    participant_id = band_config["participant_id"]
    device_identifier = band_config["device_identifier"]
    stream_name = band_config["stream_name"]

    print()
    print("Starting band recorder")
    print("----------------------")
    print(f"Participant ID: {participant_id}")
    if match_by_name:
        print(f"Matching by name: {name_filter} (config address ignored)")
    else:
        print(f"Device identifier: {device_identifier}")
    print(f"LSL stream name: {stream_name}")
    print()

    band = connect_single_band(
        target_identifier=device_identifier,
        scan_seconds=scan_seconds,
        verbose=True,
        match_by_name=match_by_name,
        name_filter=name_filter,
        exclude_addresses=exclude_addresses,
    )

    if match_by_name:
        print(f"[{participant_id}] Connected to band at address {band.identifier}")

    ppg_outlet = PpgLslOutlet(
        participant_id=participant_id,
        stream_name=stream_name,
        source_id=f"{participant_id}_{device_identifier}",
        channel_count=6,
    )

    session = PpgSession(
        participant_id=participant_id,
        outlet=ppg_outlet,
    )

    session.attach_devices(
        band.watch,
        band.nrf,
        band.nim,
        band.optical,
    )

    band.watch.Error += lambda _sender, event: print(f"Watch error [{participant_id}]: {event}")
    band.watch.Disconnected += lambda _sender, event: print(f"Watch disconnected [{participant_id}]")

    print(f"[{participant_id}] Enabling BLE notifications...")
    band.watch.EnableNotifications(True)

    print(f"[{participant_id}] Initializing optical registers...")
    session.init_registers()

    print(f"[{participant_id}] Attaching notification callback...")
    band.watch.NotificationAvailable += session.on_notification

    return {
        "participant_id": participant_id,
        "device_identifier": device_identifier,
        "stream_name": stream_name,
        "band": band,
        "session": session,
    }


def stop_band_recorder(recorder):
    participant_id = recorder["participant_id"]
    band = recorder["band"]
    session = recorder["session"]

    print()
    print(f"Stopping band recorder for {participant_id}...")

    try:
        band.nrf.EnableSensors(False)
    except Exception as exc:
        print(f"Warning: failed to disable sensors for {participant_id}: {exc}")

    try:
        band.watch.NotificationAvailable -= session.on_notification
    except Exception as exc:
        print(f"Warning: failed to remove notification callback for {participant_id}: {exc}")

    try:
        band.watch.EnableNotifications(False)
    except Exception as exc:
        print(f"Warning: failed to disable BLE notifications for {participant_id}: {exc}")


def print_live_summary(recorders, remaining):
    parts = []

    for recorder in recorders:
        session = recorder["session"]
        result = session.summary()
        parts.append(
            f"{result['participant_id']}: "
            f"samples={result['sample_count']}, "
            f"notifications={result['notification_count']}"
        )

    print(f"Recording... {remaining}s remaining | " + " | ".join(parts))


def main():
    parser = argparse.ArgumentParser(description="Run laptop PPG recorder from config.")
    parser.add_argument("--config", required=True, help="Path to laptop config JSON.")
    parser.add_argument("--scan-seconds", type=int, default=10, help="BLE scan timeout per band.")
    parser.add_argument("--duration", type=int, default=60, help="Recording duration in seconds.")
    parser.add_argument(
        "--match-by-name",
        action="store_true",
        help=(
            "Connect to bands by advertised name instead of the config address. "
            "Each band is claimed in discovery order and mapped to participants "
            "in config order. Use this on Windows, where OS61 BLE addresses rotate."
        ),
    )
    parser.add_argument(
        "--device-name",
        default="OS61",
        help="Substring of the advertised name to match when using --match-by-name.",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    print("Laptop recorder")
    print("===============")
    print(f"Laptop ID: {config['laptop_id']}")
    print(f"Configured bands: {len(config['bands'])}")

    recorders = []
    connected_addresses = set()

    try:
        print()
        print("Connecting configured bands one by one...")
        for band_config in config["bands"]:
            recorder = start_band_recorder(
                band_config=band_config,
                scan_seconds=args.scan_seconds,
                match_by_name=args.match_by_name,
                name_filter=args.device_name,
                exclude_addresses=connected_addresses,
            )
            connected_addresses.add(recorder["band"].identifier)
            recorders.append(recorder)

        print()
        print("All configured bands are connected.")
        print("LSL streams are active:")
        for recorder in recorders:
            print(f"  {recorder['stream_name']}")

        print()
        print("Open LabRecorder, click Update, select all PPG streams, then Start.")
        print()

        print("Starting sensors for all connected bands...")
        for recorder in recorders:
            recorder["band"].nrf.EnableSensors(True)

        for remaining in range(args.duration, 0, -1):
            print_live_summary(recorders, remaining)
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("Recording interrupted by user.")

    finally:
        print()
        print("Stopping all band recorders...")
        for recorder in reversed(recorders):
            stop_band_recorder(recorder)

    print()
    print("Recorder summary")
    print("----------------")

    any_samples = False

    for recorder in recorders:
        result = recorder["session"].summary()
        print()
        print(f"Participant ID: {result['participant_id']}")
        print(f"Stream name: {recorder['stream_name']}")
        print(f"Notifications received: {result['notification_count']}")
        print(f"Ignored notifications: {result['ignored_notification_count']}")
        print(f"Parsed/streamed samples: {result['sample_count']}")

        if result["sample_count"] > 0:
            any_samples = True

    if not any_samples:
        raise RuntimeError("No PPG samples were parsed or streamed from any band.")

    print()
    print("Laptop recorder finished successfully.")


if __name__ == "__main__":
    main()
