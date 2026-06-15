import argparse
import time

from src.band.ppg_session import PpgSession
from src.band.single_band_connector import connect_single_band
from src.lsl.ppg_outlet import PpgLslOutlet
from src.utils.config_loader import load_config


def run_one_band(band_config: dict, scan_seconds: int):
    participant_id = band_config["participant_id"]
    device_identifier = band_config["device_identifier"]
    stream_name = band_config["stream_name"]

    print()
    print("Starting band recorder")
    print("----------------------")
    print(f"Participant ID: {participant_id}")
    print(f"Device identifier: {device_identifier}")
    print(f"LSL stream name: {stream_name}")
    print()

    band = connect_single_band(
        target_identifier=device_identifier,
        scan_seconds=scan_seconds,
        verbose=True,
    )

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

    print("Enabling BLE notifications...")
    band.watch.EnableNotifications(True)

    print("Initializing optical registers...")
    session.init_registers()

    print("Attaching notification callback...")
    band.watch.NotificationAvailable += session.on_notification

    return band, session


def stop_one_band(band, session):
    participant_id = session.participant_id

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


def main():
    parser = argparse.ArgumentParser(description="Run laptop PPG recorder from config.")
    parser.add_argument("--config", required=True, help="Path to laptop config JSON.")
    parser.add_argument("--scan-seconds", type=int, default=10, help="BLE scan timeout.")
    parser.add_argument("--duration", type=int, default=60, help="Recording duration in seconds.")
    args = parser.parse_args()

    config = load_config(args.config)

    print("Laptop recorder")
    print("===============")
    print(f"Laptop ID: {config['laptop_id']}")
    print(f"Configured bands: {len(config['bands'])}")

    if len(config["bands"]) != 1:
        raise RuntimeError(
            "This first recorder version supports exactly one band. "
            "Multi-band support will be added next."
        )

    band, session = run_one_band(
        band_config=config["bands"][0],
        scan_seconds=args.scan_seconds,
    )

    print()
    print("LSL stream is active.")
    print("Open LabRecorder, click Update, select the PPG stream, then Start.")
    print()

    try:
        print("Starting sensors...")
        band.nrf.EnableSensors(True)

        for remaining in range(args.duration, 0, -1):
            result = session.summary()
            print(
                f"Recording... {remaining}s remaining | "
                f"participant={result['participant_id']} | "
                f"samples={result['sample_count']} | "
                f"notifications={result['notification_count']}"
            )
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("Recording interrupted by user.")

    finally:
        stop_one_band(band, session)

    result = session.summary()

    print()
    print("Recorder summary")
    print("----------------")
    print(f"Participant ID: {result['participant_id']}")
    print(f"Notifications received: {result['notification_count']}")
    print(f"Ignored notifications: {result['ignored_notification_count']}")
    print(f"Parsed/streamed samples: {result['sample_count']}")

    if result["sample_count"] == 0:
        raise RuntimeError("No PPG samples were parsed or streamed.")

    print()
    print("Laptop recorder finished successfully.")


if __name__ == "__main__":
    main()
