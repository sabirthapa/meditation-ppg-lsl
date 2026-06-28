"""
Diagnostic: look for a STABLE per-band identifier on the OS61 wristbands.

The BLE MAC address rotates and every band advertises the same name
("OS61 Demo"), so neither is usable for reliable participant mapping on Windows.
This script scans (no connection) and, for each OS61 band, prints everything that
might be stable and unique:

  - address + address_type  (random => rotates; public => stable)
  - manufacturer advertising data (often contains a serial/unique id)
  - service-data / advertised service UUIDs

Run it twice a minute apart. Anything that stays the SAME for a given physical
band across both runs is a candidate stable identifier we can map to a person.
"""

import time

import simplepyble


SCAN_SECONDS = 10
NAME_FILTER = "OS61"


def hexd(data: bytes) -> str:
    return data.hex(":") if data else "(none)"


def main():
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapter found.")
        return

    adapter = adapters[0]
    print(f"Using adapter: {adapter.identifier()} [{adapter.address()}]")
    print(f"Scanning for {SCAN_SECONDS}s...\n")

    found = {}

    def on_found(p):
        name = p.identifier() or ""
        if NAME_FILTER.upper() in name.upper():
            # keep the latest peripheral object seen for this address
            found[p.address()] = p

    adapter.set_callback_on_scan_found(on_found)
    adapter.scan_start()
    time.sleep(SCAN_SECONDS)
    adapter.scan_stop()

    os61 = list(found.values())

    print(f"OS61 bands seen this scan: {len(os61)}\n")

    for i, p in enumerate(os61, start=1):
        print(f"--- OS61 band #{i} ---")
        print(f"  name           : {p.identifier()}")
        print(f"  address        : {p.address()}")
        try:
            print(f"  address_type   : {p.address_type()}")
        except Exception as exc:
            print(f"  address_type   : (error: {exc})")
        print(f"  rssi           : {p.rssi()} dBm")
        try:
            print(f"  connectable    : {p.is_connectable()}")
        except Exception:
            pass

        try:
            md = p.manufacturer_data()  # dict {company_id: bytes}
            if md:
                for company_id, payload in md.items():
                    print(f"  mfg_data[{company_id}] : {hexd(payload)}")
            else:
                print("  mfg_data       : (none)")
        except Exception as exc:
            print(f"  mfg_data       : (error: {exc})")

        try:
            services = p.services()
            if services:
                for s in services:
                    data = b""
                    try:
                        data = s.data()
                    except Exception:
                        pass
                    suffix = f" data={hexd(data)}" if data else ""
                    print(f"  service        : {s.uuid()}{suffix}")
            else:
                print("  services       : (none advertised)")
        except Exception as exc:
            print(f"  services       : (error: {exc})")

        print()


if __name__ == "__main__":
    main()
