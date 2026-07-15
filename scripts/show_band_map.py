"""
Recover the student -> band(device address) mapping from a recorded XDF.

Each PPG stream stores its device address in source_id (format:
"<participant>_<device_address>"), so we can rebuild who wore which band and
label the bands physically.

Usage:
  .\\run.ps1 scripts\\show_band_map.py "C:\\path\\recording.xdf"
"""

import argparse
import pyxdf


def first(info, key, default=""):
    v = info.get(key, [default])
    return v[0] if isinstance(v, list) and v else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path")
    args = ap.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path, synchronize_clocks=False, dejitter_timestamps=False)

    rows = []
    for s in streams:
        info = s["info"]
        if first(info, "type") != "PPG":
            continue
        name = first(info, "name")
        source_id = first(info, "source_id")
        # source_id = "<participant>_<address>"; address is after the first "_"
        addr = source_id.split("_", 1)[1] if "_" in source_id else source_id
        rows.append((name, addr, source_id))

    print(f"\n{'STUDENT / STREAM':20} {'BAND DEVICE ADDRESS':22} source_id")
    print("-" * 70)
    for name, addr, sid in sorted(rows):
        print(f"{name:20} {addr:22} {sid}")
    print(f"\n{len(rows)} bands. Label each physical band with the student name next to its address.")


if __name__ == "__main__":
    main()
