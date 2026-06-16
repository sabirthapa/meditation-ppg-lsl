import time

from src.band.ppg_session import PpgSession
from src.band.single_band_connector import connect_single_band
from src.lsl.ppg_outlet import PpgLslOutlet


TARGET_IDENTIFIER = "C141D912-00EE-A9F7-C821-C977EDF150AC"
PARTICIPANT_ID = "P_TEST"
STREAM_NAME = "PPG_P_TEST"
SCAN_SECONDS = 10
STREAM_SECONDS = 20


def main():
    band = connect_single_band(
        target_identifier=TARGET_IDENTIFIER,
        scan_seconds=SCAN_SECONDS,
        verbose=True,
    )

    print("Creating LSL outlet...")
    ppg_outlet = PpgLslOutlet(
        participant_id=PARTICIPANT_ID,
        stream_name=STREAM_NAME,
        source_id=f"{PARTICIPANT_ID}_{TARGET_IDENTIFIER}",
        channel_count=6,
    )

    session = PpgSession(
        participant_id=PARTICIPANT_ID,
        outlet=ppg_outlet,
    )
    session.attach_devices(
        band.watch,
        band.nrf,
        band.nim,
        band.optical,
    )

    band.watch.Error += lambda _sender, event: print(f"Watch error: {event}")
    band.watch.Disconnected += lambda _sender, event: print("Watch disconnected.")

    print("Enabling BLE notifications...")
    band.watch.EnableNotifications(True)

    print("Initializing optical registers...")
    session.init_registers()

    print()
    print("LSL stream should now be available:")
    print(f"  name: {STREAM_NAME}")
    print("Open LabRecorder and check that this stream appears.")
    print()

    print(f"Starting sensors for {STREAM_SECONDS} seconds...")
    band.watch.NotificationAvailable += session.on_notification

    try:
        band.nrf.EnableSensors(True)

        for remaining in range(STREAM_SECONDS, 0, -1):
            result = session.summary()
            print(
                f"Streaming to LSL... {remaining}s remaining | "
                f"samples={result['sample_count']} | "
                f"notifications={result['notification_count']}"
            )
            time.sleep(1)

    finally:
        print("Stopping sensors...")

        try:
            band.nrf.EnableSensors(False)
        except Exception as exc:
            print(f"Warning: failed to disable sensors: {exc}")

        try:
            band.watch.NotificationAvailable -= session.on_notification
        except Exception as exc:
            print(f"Warning: failed to remove notification callback: {exc}")

        try:
            band.watch.EnableNotifications(False)
        except Exception as exc:
            print(f"Warning: failed to disable BLE notifications: {exc}")

    result = session.summary()

    print()
    print("One-band LSL summary")
    print("--------------------")
    print(f"Participant ID: {result['participant_id']}")
    print(f"Notifications received: {result['notification_count']}")
    print(f"Ignored notifications: {result['ignored_notification_count']}")
    print(f"Parsed/streamed samples: {result['sample_count']}")

    print()
    print("First parsed samples:")
    for i, sample in enumerate(result["first_samples"], start=1):
        print(f"{i}. {sample}")

    if result["sample_count"] == 0:
        raise RuntimeError("No PPG samples were parsed or streamed.")

    print()
    print("One-band LSL streaming test passed.")


if __name__ == "__main__":
    main()
