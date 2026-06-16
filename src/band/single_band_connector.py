import time
from dataclasses import dataclass

from src.blewristband import BleDongle, BleScanInfo, WristbandFactory


@dataclass
class ConnectedBand:
    identifier: str
    name: str
    dongle: object
    factory: object
    watch: object
    nrf: object
    nim: object
    optical: object


def connect_single_band(
    target_identifier: str,
    scan_seconds: int = 10,
    verbose: bool = True,
) -> ConnectedBand:
    """
    Scan for one specific OS61 wristband and connect to it.

    On macOS, target_identifier is usually the CoreBluetooth UUID shown during scan,
    not the physical BLE MAC address.

    Returns a ConnectedBand object containing:
    - watch
    - nrf
    - nim
    - optical
    - dongle/factory references, so the connection stays alive
    """

    dongle = BleDongle()
    selected_device = [None]
    selected_name = ["Unknown"]

    def on_device_found(_sender, event):
        name = event.Name or "Unknown"
        identifier = str(event.Address)

        if verbose:
            print(f"Found: {name} | {identifier}")

        if identifier == target_identifier:
            if verbose:
                print("Target OS61 wristband found.")

            selected_device[0] = BleScanInfo(event.peripheral)
            selected_name[0] = name
            dongle.StopScan()

    dongle.DeviceFound += on_device_found

    if verbose:
        print("Initializing Bluetooth adapter...")

    dongle.Connect()

    if verbose:
        print(f"Searching for target wristband for up to {scan_seconds} seconds...")

    dongle.StartScan()

    deadline = time.time() + scan_seconds

    while selected_device[0] is None and time.time() < deadline:
        time.sleep(0.1)

    if selected_device[0] is None:
        dongle.StopScan()
        raise RuntimeError(
            f"Target wristband was not found: {target_identifier}. "
            "Confirm that it is powered on and advertising."
        )

    if verbose:
        print("Connecting to wristband...")

    factory = WristbandFactory(dongle)

    if not factory.Connect(selected_device[0]):
        raise RuntimeError("Failed to connect to the wristband.")

    if verbose:
        print("Connected successfully.")
        print("Setting up OS61 target devices...")

    factory.SetupOS61TargetDevices()

    watch = factory.WristbandSystem
    nrf = watch.GetDevice("NRF")
    nim = watch.GetDevice("NIM")
    optical = watch.GetDevice("OS61")

    if not all((watch, nrf, nim, optical)):
        raise RuntimeError("One or more wristband components could not be created.")

    return ConnectedBand(
        identifier=target_identifier,
        name=selected_name[0],
        dongle=dongle,
        factory=factory,
        watch=watch,
        nrf=nrf,
        nim=nim,
        optical=optical,
    )
