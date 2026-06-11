import time
import threading

from src.blewristband import BleDongle, BleScanInfo, WristbandFactory


TARGET_IDENTIFIER = "C141D912-00EE-A9F7-C821-C977EDF150AC"
SCAN_SECONDS = 10
STREAM_SECONDS = 10


class RawNotificationCounter:
    def __init__(self):
        self.lock = threading.Lock()
        self.total_packets = 0
        self.by_notify_type = {}
        self.first_packets = 0
        self.first_examples = []

    def on_notification(self, _sender, event):
        with self.lock:
            self.total_packets += 1

            notify_type = getattr(event, "Notify", None)
            is_first = getattr(event, "First", False)
            data = getattr(event, "Data", b"")

            self.by_notify_type[notify_type] = self.by_notify_type.get(notify_type, 0) + 1

            if is_first:
                self.first_packets += 1

            if len(self.first_examples) < 10:
                self.first_examples.append(
                    {
                        "notify": notify_type,
                        "first": is_first,
                        "length": len(data),
                        "hex": bytes(data).hex(" "),
                    }
                )

    def print_summary(self):
        with self.lock:
            print()
            print("Raw notification summary")
            print("------------------------")
            print(f"Total packets received: {self.total_packets}")
            print(f"First packets observed: {self.first_packets}")
            print(f"Packets by notify type: {self.by_notify_type}")

            print()
            print("First few packets:")
            for i, packet in enumerate(self.first_examples, start=1):
                print(
                    f"{i}. notify={packet['notify']} "
                    f"first={packet['first']} "
                    f"len={packet['length']} "
                    f"hex={packet['hex']}"
                )


def init_optical_registers(optical, nim):
    # Copied from friend's PpgSession.init_registers()
    optical.ReadModifyWrite(12, 7, 0, 2)
    optical.ReadModifyWrite(13, 7, 0, 1)
    optical.ReadModifyWrite(14, 7, 0, 0)
    optical.ReadModifyWrite(15, 7, 0, 85)
    optical.ReadModifyWrite(16, 7, 0, 0)
    optical.ReadModifyWrite(17, 7, 0, 0)
    optical.ReadModifyWrite(21, 7, 0, 0)
    optical.ReadModifyWrite(22, 7, 0, 1)
    optical.ReadModifyWrite(23, 7, 0, 64)

    for slot in (24, 32, 40, 48, 56, 64, 72, 80, 88):
        optical.ReadModifyWrite(slot + 0, 7, 0, 0)
        optical.ReadModifyWrite(slot + 1, 7, 0, 24)
        optical.ReadModifyWrite(slot + 2, 7, 0, 58)
        optical.ReadModifyWrite(slot + 3, 7, 0, 80)
        optical.ReadModifyWrite(slot + 4, 7, 0, 10)
        optical.ReadModifyWrite(slot + 5, 7, 0, 0)
        optical.ReadModifyWrite(slot + 6, 7, 0, 0)

    optical.ReadModifyWrite(112, 7, 0, 0)
    nim.EnableFclk(False)


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

    counter = RawNotificationCounter()

    watch.Error += lambda _sender, event: print(f"Watch error: {event}")
    watch.Disconnected += lambda _sender, event: print("Watch disconnected.")

    print("Enabling BLE notifications...")
    watch.EnableNotifications(True)

    print("Initializing optical registers...")
    init_optical_registers(optical, nim)

    print(f"Starting sensors for {STREAM_SECONDS} seconds...")
    watch.NotificationAvailable += counter.on_notification

    try:
        nrf.EnableSensors(True)

        for remaining in range(STREAM_SECONDS, 0, -1):
            print(f"Recording raw notifications... {remaining}s remaining")
            time.sleep(1)

    finally:
        print("Stopping sensors...")
        try:
            nrf.EnableSensors(False)
        except Exception as exc:
            print(f"Warning: failed to disable sensors: {exc}")

        try:
            watch.NotificationAvailable -= counter.on_notification
        except Exception as exc:
            print(f"Warning: failed to remove notification callback: {exc}")

        try:
            watch.EnableNotifications(False)
        except Exception as exc:
            print(f"Warning: failed to disable BLE notifications: {exc}")

    counter.print_summary()

    if counter.total_packets == 0:
        raise RuntimeError("No raw BLE notifications were received.")

    print()
    print("Raw notification test passed.")


if __name__ == "__main__":
    main()
