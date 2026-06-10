import time

from src.blewristband import BleDongle


SCAN_SECONDS = 10


def main():
    dongle = BleDongle()
    discovered = {}

    def on_device_found(_sender, event):
        name = event.Name or "Unknown"
        address = str(event.Address)

        key = address or name

        if key not in discovered:
            discovered[key] = {
                "name": name,
                "address": address,
            }

            marker = " <-- OS61 wristband" if "OS61" in name.upper() else ""

            print(
                f"Found: name={name}, "
                f"address={address}{marker}"
            )

    dongle.DeviceFound += on_device_found

    print("Initializing Bluetooth adapter...")
    dongle.Connect()

    print(f"Scanning for {SCAN_SECONDS} seconds...")
    dongle.StartScan()

    try:
        time.sleep(SCAN_SECONDS)
    finally:
        dongle.StopScan()

    os61_devices = [
        device
        for device in discovered.values()
        if "OS61" in device["name"].upper()
    ]

    print()
    print(f"Total unique BLE devices found: {len(discovered)}")
    print(f"OS61 wristbands found: {len(os61_devices)}")

    for index, device in enumerate(os61_devices, start=1):
        print(
            f"{index}. {device['name']} | "
            f"{device['address']}"
        )


if __name__ == "__main__":
    main()
