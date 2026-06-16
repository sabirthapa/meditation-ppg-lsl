import time

from src.blewristband import BleDongle, BleScanInfo, WristbandFactory


TARGET_IDENTIFIER = "C141D912-00EE-A9F7-C821-C977EDF150AC"
SCAN_SECONDS = 10


def main():
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
        raise RuntimeError(
            "Target wristband was not found. "
            "Confirm that it is powered on and advertising."
        )

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

    print()
    print("Available wristband components:")
    print(f"  Wristband system: {watch is not None}")
    print(f"  NRF controller:   {nrf is not None}")
    print(f"  NIM controller:   {nim is not None}")
    print(f"  Optical sensor:   {optical is not None}")

    if not all((watch, nrf, nim, optical)):
        raise RuntimeError("One or more wristband components could not be created.")

    print()
    print("One-band connection test passed.")
    print("PPG sensors were not enabled in this test.")


if __name__ == "__main__":
    main()
