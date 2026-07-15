"""
Identify which student a physical band belongs to, so you can label it.

Uses the student->address map recovered from a recording (XDF source_ids), then
scans. Power on ONE band, hold it CLOSE to the laptop, and run this: the
strongest matching band is the one in your hand -> write that student's name on it.

Usage:
  .\\run.ps1 scripts\\identify_band.py "C:\\path\\today_recording.xdf"
  (repeat for each band, powering on one at a time)
"""

import argparse
import time

import pyxdf
import simplepyble


def build_map(xdf_path):
    streams, _ = pyxdf.load_xdf(xdf_path, synchronize_clocks=False, dejitter_timestamps=False)
    mapping = {}
    for s in streams:
        info = s["info"]
        if (info.get("type") or [""])[0] != "PPG":
            continue
        name = (info.get("name") or [""])[0]
        sid = (info.get("source_id") or [""])[0]
        addr = sid.split("_", 1)[1] if "_" in sid else sid
        mapping[addr.lower()] = name
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path", help="A recording that contains the student streams (for the name<->address map).")
    ap.add_argument("--scan-seconds", type=int, default=6)
    args = ap.parse_args()

    mapping = build_map(args.xdf_path)
    print(f"Loaded {len(mapping)} known bands from the recording.\n")

    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapter found.")
        return
    adapter = adapters[0]

    seen = {}

    def on_found(p):
        name = p.identifier() or ""
        if "OS61" in name.upper():
            seen[p.address().lower()] = p.rssi()

    print(f"Scanning {args.scan_seconds}s... (power on ONE band, hold it near the laptop)\n")
    adapter.set_callback_on_scan_found(on_found)
    adapter.scan_start()
    time.sleep(args.scan_seconds)
    adapter.scan_stop()

    if not seen:
        print("No OS61 band detected. Make sure it's on and close, then retry.")
        return

    print(f"{'STUDENT':16} {'ADDRESS':22} RSSI")
    print("-" * 48)
    for addr, rssi in sorted(seen.items(), key=lambda kv: kv[1], reverse=True):
        who = mapping.get(addr, "UNKNOWN (not in recording)")
        print(f"{who:16} {addr:22} {rssi} dBm")

    strongest_addr, strongest_rssi = max(seen.items(), key=lambda kv: kv[1])
    who = mapping.get(strongest_addr, "UNKNOWN")
    print(f"\n>> Closest/strongest band = '{who}'  ({strongest_addr}, {strongest_rssi} dBm)")
    print("   If you powered on just one band, THIS is it. Label it and move on.")


if __name__ == "__main__":
    main()
