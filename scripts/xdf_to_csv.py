"""
Convert an XDF recording to CSV — one CSV file per stream.

Each PPG stream -> <stream_name>.csv with columns: timestamp, ch0..chN
The marker stream -> <stream_name>.csv with columns: timestamp, value

Timestamps are the LSL timestamps as stored in the XDF (already clock-aligned
across streams/laptops by LabRecorder). Optical values are the raw sensor counts.

Usage:
  .\\run.ps1 scripts\\xdf_to_csv.py "C:\\path\\to\\recording.xdf"
  .\\run.ps1 scripts\\xdf_to_csv.py "C:\\path\\to\\recording.xdf" --out-dir "C:\\somewhere"
"""

import argparse
import csv
import os

import numpy as np
import pyxdf


def channel_labels(info, n):
    """Pull channel labels from stream metadata, fall back to ch0..chN-1."""
    try:
        chans = info["desc"][0]["channels"][0]["channel"]
        labels = [c["label"][0] for c in chans]
        if len(labels) == n:
            return labels
    except Exception:
        pass
    return [f"ch{i}" for i in range(n)]


def safe_name(name):
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(name))


def main():
    ap = argparse.ArgumentParser(description="Convert an XDF file to per-stream CSV files.")
    ap.add_argument("xdf_path", help="Path to the .xdf file.")
    ap.add_argument("--out-dir", default=None,
                    help="Output folder (default: '<xdf name>_csv' next to the file).")
    args = ap.parse_args()

    print(f"Loading {args.xdf_path} ...")
    streams, _ = pyxdf.load_xdf(args.xdf_path)

    base = os.path.splitext(os.path.basename(args.xdf_path))[0]
    out_dir = args.out_dir or os.path.join(
        os.path.dirname(os.path.abspath(args.xdf_path)), f"{base}_csv"
    )
    os.makedirs(out_dir, exist_ok=True)
    print(f"Writing {len(streams)} stream(s) to: {out_dir}\n")

    for s in streams:
        info = s["info"]
        name = (info.get("name") or ["unnamed"])[0]
        stype = (info.get("type") or [""])[0]
        ts = np.asarray(s["time_stamps"], dtype=np.float64)
        series = s["time_series"]
        n = len(ts)
        out_path = os.path.join(out_dir, f"{safe_name(name)}.csv")

        is_numeric = isinstance(series, np.ndarray) and series.dtype.kind in "fiu"

        if is_numeric and n > 0:
            arr = series.reshape(n, -1).astype(np.float64)
            nch = arr.shape[1]
            labels = channel_labels(info, nch)
            matrix = np.column_stack([ts, arr])
            header = ",".join(["timestamp"] + labels)
            # timestamps: high precision; sensor counts: exact (they are integers)
            fmt = ["%.9f"] + ["%.6f"] * nch
            np.savetxt(out_path, matrix, delimiter=",", header=header,
                       comments="", fmt=fmt)
        else:
            # marker / string stream (or empty)
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "value"])
                for i in range(n):
                    val = series[i]
                    if isinstance(val, (list, tuple)):
                        val = val[0] if len(val) else ""
                    w.writerow([f"{ts[i]:.9f}", val])

        print(f"  {name:20} type={stype:8} rows={n:>8}  -> {os.path.basename(out_path)}")

    print("\nDone. One CSV per stream.")


if __name__ == "__main__":
    main()
