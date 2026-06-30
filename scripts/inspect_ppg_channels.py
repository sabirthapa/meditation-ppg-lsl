"""
Quick diagnostic: are the 6 stored PPG columns 6 independent channels, or
fewer channels repeated / interleaved? Looks at one PPG stream from an XDF:
prints a few consecutive samples and the correlation between the 6 columns.
"""

import argparse

import numpy as np
import pyxdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xdf_path")
    parser.add_argument("--rows", type=int, default=12, help="Consecutive samples to print.")
    args = parser.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path)

    # first PPG stream that actually has data
    ppg = next(
        s for s in streams
        if s["info"]["type"][0] == "PPG" and len(s["time_series"]) > 0
    )
    name = ppg["info"]["name"][0]
    data = np.asarray(ppg["time_series"], dtype=np.float64)
    ts = np.asarray(ppg["time_stamps"], dtype=np.float64)

    print(f"Stream: {name}  shape={data.shape}  (samples x channels)\n")

    print("First consecutive samples (6 columns):")
    for i in range(min(args.rows, data.shape[0])):
        cols = "  ".join(f"{v:11.0f}" for v in data[i])
        print(f"  t={ts[i]-ts[0]:7.4f}s | {cols}")

    print("\nPer-column stats over first 5000 samples:")
    win = data[:5000]
    for c in range(data.shape[1]):
        col = win[:, c]
        print(f"  ch{c}: mean={col.mean():12.1f}  std={col.std():10.1f}  "
              f"min={col.min():.0f}  max={col.max():.0f}")

    print("\nCorrelation matrix between the 6 columns (first 5000 samples):")
    corr = np.corrcoef(win.T)
    header = "      " + "".join(f"ch{c:<6}" for c in range(data.shape[1]))
    print(header)
    for c in range(corr.shape[0]):
        row = "  ".join(f"{corr[c, k]:+.2f}" for k in range(corr.shape[1]))
        print(f"  ch{c} {row}")

    print("\nUnique values in row 0:", sorted(set(data[0].tolist())))


if __name__ == "__main__":
    main()
