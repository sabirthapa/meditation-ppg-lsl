"""
Throwaway: for each participant, scan the WHOLE recording in 30s bins and report
where a clean heartbeat is present. Prints a timeline sparkline for flagged names
so we can see if a 'no pulse in baseline' band has signal elsewhere (e.g. once
adjusted during meditation) or is bad throughout (poor fit).
"""

import argparse
import numpy as np
import pyxdf

HR_LO, HR_HI = 0.7, 3.0
CLEAN = 18.0
BIN = 30.0


def prominence(sig, fs):
    sig = np.asarray(sig, float)
    if len(sig) < 32:
        return 0.0
    sig = sig - sig.mean()
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / fs)
    p = np.abs(np.fft.rfft(sig)) ** 2
    band = (freqs >= HR_LO) & (freqs <= HR_HI)
    return (p[band].max() / (np.median(p[band]) or 1.0)) if band.any() else 0.0


def spark(v):
    blocks = " .:-=+*#%@"
    lo, hi = 0, 60
    i = int(min(max((v - lo) / (hi - lo), 0), 1) * (len(blocks) - 1))
    return blocks[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path")
    ap.add_argument("--focus", default="",
                    help="Comma-separated stream names to print detailed timelines for.")
    args = ap.parse_args()
    focus = {x.strip().lower() for x in args.focus.split(",") if x.strip()}
    streams, _ = pyxdf.load_xdf(args.xdf_path)
    ppg = [s for s in streams if s["info"]["type"][0] == "PPG" and len(s["time_series"]) > 0]

    med_start = med_end = None
    for s in streams:
        if s["info"]["type"][0] == "Markers":
            for val, t in zip(s["time_series"], s["time_stamps"]):
                v = val[0] if isinstance(val, (list, tuple)) else val
                if v == "meditation_start": med_start = t
                if v == "meditation_end": med_end = t

    rec_start = min(np.asarray(s["time_stamps"])[0] for s in ppg)
    rec_end = max(np.asarray(s["time_stamps"])[-1] for s in ppg)
    dur = rec_end - rec_start
    nbins = int(dur // BIN)
    if med_start:
        print(f"meditation_start at {med_start - rec_start:.0f}s"
              + (f", meditation_end at {med_end - rec_start:.0f}s" if med_end else ""))
    print(f"Recording length {dur:.0f}s, {nbins} bins of {BIN:.0f}s\n")

    print(f"{'PARTICIPANT':12} {'max':>4} {'%clean':>6}  clean time-range")
    print("-" * 55)
    focus_rows = []
    for s in ppg:
        name = s["info"]["name"][0]
        data = np.asarray(s["time_series"], float)
        ts = np.asarray(s["time_stamps"], float)
        # choose channel by best prominence over whole recording
        best = (0.0, 0, 0)
        for g in (0, 1):
            tg, dg = ts[g::2], data[g::2]
            fs = 1.0 / np.median(np.diff(tg))
            for c in range(dg.shape[1]):
                # sample a few windows to pick channel
                pr = prominence(dg[:min(len(dg), 4000), c], fs)
                if pr > best[0]:
                    best = (pr, g, c)
        _, g, c = best
        tg, dg = ts[g::2], data[g::2, c]
        fs = 1.0 / np.median(np.diff(tg))

        strengths = []
        for b in range(nbins):
            a = rec_start + b * BIN
            m = (tg >= a) & (tg < a + BIN)
            strengths.append(prominence(dg[m], fs) if m.sum() > 32 else 0.0)
        strengths = np.array(strengths)
        clean = strengths >= CLEAN
        pct = 100.0 * clean.mean()
        if clean.any():
            first = np.argmax(clean) * BIN
            last = (len(clean) - 1 - np.argmax(clean[::-1])) * BIN
            rng = f"{first:.0f}-{last:.0f}s"
        else:
            rng = "never"
        print(f"{name:12} {strengths.max():4.0f} {pct:5.0f}%  {rng}")
        if name.lower() in focus:
            focus_rows.append((name, strengths))

    print("\nTimelines (each char = 30s; ' .' = flat/no pulse, '#@' = strong pulse):")
    print(f"{'':12} 0s{'':>{max(0,nbins-6)}}end")
    for name, st in focus_rows:
        print(f"{name:12} " + "".join(spark(v) for v in st))
    if med_start:
        mb = int((med_start - rec_start) // BIN)
        print(f"{'meditation>':12} " + " " * mb + "^")


if __name__ == "__main__":
    main()
