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
    target_identifier: str = None,
    scan_seconds: int = 10,
    verbose: bool = True,
    match_by_name: bool = False,
    name_filter: str = "OS61",
    exclude_addresses: set = None,
) -> ConnectedBand:
    """
    Scan for one OS61 wristband and connect to it.

    Two matching modes:

    - Exact address (default): connect to the device whose BLE address equals
      ``target_identifier``. On macOS this identifier is usually the CoreBluetooth
      UUID shown during scan, not the physical BLE MAC address.

    - Name match (``match_by_name=True``): connect to the first discovered device
      whose name contains ``name_filter`` and whose address is not in
      ``exclude_addresses``. This is the reliable mode on Windows, where the OS61
      bands broadcast rotating random BLE addresses (so a fixed address goes stale
      between scans) but the advertised name stays "OS61 Demo". Pass the set of
      already-connected addresses as ``exclude_addresses`` so each call claims a
      different physical band.

    Returns a ConnectedBand object containing:
    - watch
    - nrf
    - nim
    - optical
    - dongle/factory references, so the connection stays alive
    """

    exclude_addresses = exclude_addresses or set()

    dongle = BleDongle()
    selected_device = [None]
    selected_name = ["Unknown"]
    selected_address = [None]

    def on_device_found(_sender, event):
        name = event.Name or "Unknown"
        identifier = str(event.Address)

        if verbose:
            print(f"Found: {name} | {identifier}")

        if selected_device[0] is not None:
            return

        if match_by_name:
            matches = (
                name_filter.upper() in name.upper()
                and identifier not in exclude_addresses
            )
        else:
            matches = identifier == target_identifier

        if matches:
            if verbose:
                if match_by_name:
                    print(f"Matched OS61 wristband by name at {identifier}.")
                else:
                    print("Target OS61 wristband found.")

            selected_device[0] = BleScanInfo(event.peripheral)
            selected_name[0] = name
            selected_address[0] = identifier
            dongle.StopScan()

    dongle.DeviceFound += on_device_found

    if verbose:
        print("Initializing Bluetooth adapter...")

    dongle.Connect()

    if verbose:
        if match_by_name:
            print(
                f"Searching for an unclaimed '{name_filter}' wristband "
                f"for up to {scan_seconds} seconds..."
            )
        else:
            print(f"Searching for target wristband for up to {scan_seconds} seconds...")

    dongle.StartScan()

    deadline = time.time() + scan_seconds

    while selected_device[0] is None and time.time() < deadline:
        time.sleep(0.1)

    if selected_device[0] is None:
        dongle.StopScan()
        if match_by_name:
            raise RuntimeError(
                f"No unclaimed '{name_filter}' wristband was found within "
                f"{scan_seconds}s. Confirm the bands are powered on and advertising."
            )
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
        identifier=selected_address[0] or target_identifier,
        name=selected_name[0],
        dongle=dongle,
        factory=factory,
        watch=watch,
        nrf=nrf,
        nim=nim,
        optical=optical,
    )
