"""
One-at-a-time band enrollment.

Builds a laptop config (the same JSON the recorder reads) by having you power on
your bands ONE AT A TIME. Because the OS61 BLE addresses are stable while powered
but there is no readable unique id and the lab has other stray "OS61 Demo" bands,
the reliable way to know which physical band is which participant is to bring them
online one by one and pin each new address as it appears.

Procedure:
  1. Start with ALL of your study bands OFF.
  2. Run this script. When prompted, power ON the next band only.
  3. The script detects the newly-appeared OS61 address and asks for the
     participant id. It records address -> participant id / stream name.
  4. Repeat for each band, then type 'done'.

Output: configs/<laptop_id>.json  (use it with scripts/run_session.py)

Run it in your own terminal (it is interactive):
  .\\run.ps1 scripts\\enroll_bands.py --laptop-id laptop_01
"""

import argparse
import json
import os
import time

import simplepyble


NAME_FILTER = "OS61"
SCAN_SECONDS = 5
WEAK_RSSI_DBM = -75  # warn if a "new" band is far away (maybe a stray lab band)


def scan_os61(adapter, scan_seconds):
    """Return {address: rssi} for OS61 bands seen in one short scan."""
    seen = {}

    def on_found(p):
        name = p.identifier() or ""
        if NAME_FILTER.upper() in name.upper():
            seen[p.address()] = p.rssi()

    adapter.set_callback_on_scan_found(on_found)
    adapter.scan_start()
    time.sleep(scan_seconds)
    adapter.scan_stop()
    return seen


def detect_new_address(adapter, known: set, scan_seconds):
    """Scan and return the strongest OS61 address not in `known`, or None."""
    seen = scan_os61(adapter, scan_seconds)
    candidates = {a: r for a, r in seen.items() if a not in known}
    if not candidates:
        return None, seen
    best = max(candidates.items(), key=lambda kv: kv[1])  # strongest RSSI
    return best, seen


def main():
    parser = argparse.ArgumentParser(description="One-at-a-time band enrollment.")
    parser.add_argument("--laptop-id", required=True, help="Identifier for this laptop, e.g. laptop_01.")
    parser.add_argument("--out-dir", default="configs", help="Where to write the config JSON.")
    parser.add_argument("--scan-seconds", type=int, default=SCAN_SECONDS)
    args = parser.parse_args()

    scan_seconds = args.scan_seconds

    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapter found.")
        return
    adapter = adapters[0]
    print(f"Using adapter: {adapter.identifier()} [{adapter.address()}]")

    print()
    print("Enrollment — one band at a time")
    print("===============================")
    print("Make sure ALL of your study bands are currently OFF.")
    print("You will power them on one at a time.")
    print()

    # Baseline: any OS61 addresses already on the air are NOT ours (stray lab
    # bands). Record them so we ignore them.
    print("Taking a baseline scan of stray OS61 bands already on the air...")
    baseline = scan_os61(adapter, scan_seconds)
    if baseline:
        print(f"  Ignoring {len(baseline)} stray OS61 band(s) already advertising:")
        for a, r in sorted(baseline.items(), key=lambda kv: kv[1], reverse=True):
            print(f"    {a} ({r} dBm)")
    else:
        print("  None seen. Good.")
    print()

    known = set(baseline.keys())
    bands = []

    while True:
        prompt = (
            f"Power ON the next band, then press ENTER to detect it "
            f"(or type 'done' to finish): "
        )
        user = input(prompt).strip().lower()
        if user in {"done", "d", "q", "quit"}:
            break

        print("  Scanning for the newly powered-on band...")
        result, seen = detect_new_address(adapter, known, scan_seconds)

        if result is None:
            print("  No NEW OS61 band detected. Wait a few seconds after powering")
            print("  on, make sure it's close to the laptop, and try again.")
            continue

        address, rssi = result
        if rssi < WEAK_RSSI_DBM:
            print(f"  WARNING: detected {address} but it's weak ({rssi} dBm) — this")
            print("  might be a stray band, not the one you just turned on.")
        confirm = input(f"  Detected {address} ({rssi} dBm). Use this band? [Y/n]: ").strip().lower()
        if confirm in {"n", "no"}:
            print("  Skipped. (Address not recorded; rescan to try again.)")
            continue

        participant_id = input("  Participant id (e.g. P01): ").strip()
        if not participant_id:
            print("  Empty participant id — skipping.")
            continue
        default_stream = f"PPG_{participant_id}"
        stream_name = input(f"  Stream name [{default_stream}]: ").strip() or default_stream

        bands.append({
            "participant_id": participant_id,
            "device_identifier": address,
            "stream_name": stream_name,
        })
        known.add(address)
        print(f"  Enrolled {participant_id} -> {address} ({stream_name}). "
              f"Total enrolled: {len(bands)}")
        print()

    if not bands:
        print("No bands enrolled. Nothing written.")
        return

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, f"{args.laptop_id}.json")
    config = {"laptop_id": args.laptop_id, "bands": bands}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print()
    print(f"Wrote {len(bands)} band(s) to {out_path}")
    print("Enrolled bands:")
    for b in bands:
        print(f"  {b['participant_id']:8} {b['device_identifier']}  -> {b['stream_name']}")
    print()
    print("Run the session with:")
    print(f"  .\\run.ps1 scripts\\run_session.py --config {out_path} --duration 120")


if __name__ == "__main__":
    main()
