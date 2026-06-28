"""
Diagnostic: connect to ONE OS61 band and dump its full GATT, reading every
readable characteristic. We're hunting for a STABLE, UNIQUE per-band value
(serial number, system id, etc.) that survives the rotating BLE address.

Standard Device Information Service candidates we especially care about:
  0x2A23 System ID          (often a unique 64-bit id)
  0x2A25 Serial Number
  0x2A27 Hardware Revision
  0x2A26 Firmware Revision
  0x2A29 Manufacturer Name

Run this against each band (power only the one you're probing, or just rerun and
it grabs whichever it finds first) and compare the readable values across bands.
"""

import time

import simplepyble


SCAN_SECONDS = 10
NAME_FILTER = "OS61"


def hexd(data: bytes) -> str:
    return data.hex(":") if data else "(empty)"


def asciid(data: bytes) -> str:
    try:
        return data.decode("ascii", errors="replace")
    except Exception:
        return "(non-ascii)"


def main():
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapter found.")
        return

    adapter = adapters[0]
    found = {}

    def on_found(p):
        name = p.identifier() or ""
        if NAME_FILTER.upper() in name.upper():
            found[p.address()] = p

    print(f"Scanning {SCAN_SECONDS}s for an OS61 band...")
    adapter.set_callback_on_scan_found(on_found)
    adapter.scan_start()
    time.sleep(SCAN_SECONDS)
    adapter.scan_stop()

    if not found:
        print("No OS61 band found. Make sure it is powered on and advertising.")
        return

    target = next(iter(found.values()))
    print(f"Connecting to {target.identifier()} | {target.address()} ...")
    target.connect()
    print("Connected. Enumerating GATT...\n")

    try:
        for service in target.services():
            print(f"SERVICE {service.uuid()}")
            for ch in service.characteristics():
                caps = []
                try:
                    caps = list(ch.capabilities())
                except Exception:
                    pass
                cap_str = ",".join(caps) if caps else "?"
                line = f"  CHAR {ch.uuid()} [{cap_str}]"

                can_read = ("read" in caps) or (not caps)
                if can_read:
                    try:
                        val = target.read(service.uuid(), ch.uuid())
                        line += f"\n        hex   : {hexd(val)}"
                        line += f"\n        ascii : {asciid(val)}"
                    except Exception as exc:
                        line += f"  (read failed: {exc})"
                print(line)
            print()
    finally:
        try:
            target.disconnect()
            print("Disconnected.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
