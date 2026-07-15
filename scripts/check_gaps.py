"""
Throwaway: detect recording gaps per stream in an XDF.

For each stream: coverage (start/end relative to the earliest stream), effective
rate, and any gaps between consecutive samples longer than --gap seconds. If a
laptop stopped, ALL of that laptop's bands will show a gap at the SAME time (or
all end early / start late together).
"""

import argparse
import numpy as np
import pyxdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path")
    ap.add_argument("--gap", type=float, default=1.0, help="Report gaps longer than this many seconds.")
    args = ap.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path, synchronize_clocks=True, dejitter_timestamps=False)
    ppg = [s for s in streams if s["info"]["type"][0] == "PPG" and len(s["time_stamps"]) > 1]

    t0 = min(np.asarray(s["time_stamps"])[0] for s in ppg)
    tend = max(np.asarray(s["time_stamps"])[-1] for s in ppg)
    print(f"Overall span: {tend - t0:.1f} s across {len(ppg)} PPG streams\n")

    print(f"{'STREAM':12} {'start':>7} {'end':>8} {'dur':>7} {'rate':>6} {'#gaps':>6} {'biggest gap':>26}")
    print("-" * 78)
    all_gaps = []
    for s in ppg:
        name = s["info"]["name"][0]
        ts = np.asarray(s["time_stamps"], dtype=np.float64)
        start, end = ts[0] - t0, ts[-1] - t0
        dur = ts[-1] - ts[0]
        rate = (len(ts) - 1) / dur if dur > 0 else 0
        dif = np.diff(ts)
        gap_idx = np.where(dif > args.gap)[0]
        gaps = [(ts[i] - t0, dif[i]) for i in gap_idx]  # (when relative to t0, how long)
        for when, length in gaps:
            all_gaps.append((name, when, length))
        if gaps:
            biggest = max(gaps, key=lambda g: g[1])
            bg = f"{biggest[1]:.1f}s @ t={biggest[0]:.0f}s"
        else:
            bg = "-"
        # flag short coverage (ended early or started late)
        flag = ""
        if start > 3:
            flag += f" START+{start:.0f}s"
        if (tend - t0) - end > 3:
            flag += f" ENDS-{(tend - t0) - end:.0f}s early"
        print(f"{name:12} {start:6.0f}s {end:7.0f}s {dur:6.0f}s {rate:5.1f} {len(gaps):6d} {bg:>26}{flag}")

    if all_gaps:
        print("\nAll gaps > {:.0f}s (chronological) — look for several streams gapping at the SAME time:".format(args.gap))
        for name, when, length in sorted(all_gaps, key=lambda g: g[1]):
            print(f"  t={when:7.0f}s  {name:12} gap {length:6.1f}s")
    else:
        print(f"\nNo gaps longer than {args.gap:.0f}s in any stream. Recording was continuous.")


if __name__ == "__main__":
    main()
