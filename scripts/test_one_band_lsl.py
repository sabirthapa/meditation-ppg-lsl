import time

from src.blewristband import BleDongle, BleScanInfo, WristbandFactory
from src.band.ppg_session import PpgSession
from src.lsl.ppg_outlet import PpgLslOutlet


TARGET_IDENTIFIER = "C141D912-00EE-A9F7-C821-C977EDF150AC"
PARTICIPANT_ID = "P_TEST"
STREAM_NAME = "PPG_P_TEST"
SCAN_SECONDS = 10
STREAM_SECONDS = 20


def connect_target_wristband():
    dongle = BleDongle()
    selected_device = [None]

    def on_device_found(_sender, event):
        name = event.Name or "Unknown"
        identifier = str(event.Address)

        print(f"Found: {name} | {identifier}")

        if identifier == TARGET_IDENTIFIER:
            print("Target OS61 wristband found.")
            selected_device[0] = BleScanInfo(event.peripheral)
            dongle.StopScan()

    dongle.DeviceFound += on_device_found

    print("Initializing Bluetooth adapter...")
    dongle.Connect()

    print(f"Searching for target wristband for up to {SCAN_SECONDS} seconds...")
    dongle.StartScan()

    deadline = time.time() + SCAN_SECONDS

    while selected_device[0] is None and time.time() < deadline:
        time.sleep(0.1)

    if selected_device[0] is None:
        dongle.StopScan()
        raise RuntimeError("Target wristband was not found.")

    print("Connecting to wristband...")
    factory = WristbandFactory(dongle)

    if not factory.Connect(selected_device[0]):
        raise RuntimeError("Failed to connect to the wristband.")

    print("Connected successfully.")

    print("Setting up OS61 target devices...")
    factory.SetupOS61TargetDevices()

    watch = factory.WristbandSystem
    nrf = watch.GetDevice("NRF")
    nim = watch.GetDevice("NIM")
    optical = watch.GetDevice("OS61")

    if not all((watch, nrf, nim, optical)):
        raise RuntimeError("One or more wristband components could not be created.")

    return watch, nrf, nim, optical


def main():
    watch, nrf, nim, optical = connect_target_wristband()

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
    session.attach_devices(watch, nrf, nim, optical)

    watch.Error += lambda _sender, event: print(f"Watch error: {event}")
    watch.Disconnected += lambda _sender, event: print("Watch disconnected.")

    print("Enabling BLE notifications...")
    watch.EnableNotifications(True)

    print("Initializing optical registers...")
    session.init_registers()

    print()
    print("LSL stream should now be available:")
    print(f"  name: {STREAM_NAME}")
    print("Open LabRecorder and check that this stream appears.")
    print()

    print(f"Starting sensors for {STREAM_SECONDS} seconds...")
    watch.NotificationAvailable += session.on_notification

    try:
        nrf.EnableSensors(True)

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
            nrf.EnableSensors(False)
        except Exception as exc:
            print(f"Warning: failed to disable sensors: {exc}")

        try:
            watch.NotificationAvailable -= session.on_notification
        except Exception as exc:
            print(f"Warning: failed to remove notification callback: {exc}")

        try:
            watch.EnableNotifications(False)
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
