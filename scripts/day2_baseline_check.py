"""
Throwaway analysis: for a recording with a MISSING recording_start marker,
find (a) when each participant's PPG pulse stabilizes (worn + settled) in the
pre-meditation window, and (b) which bands show NO pulse (on a table / absent).

Helps pick a defensible baseline window = [recording_start + trim, meditation_start].
"""

import argparse
import numpy as np
import pyxdf

HR_LO, HR_HI = 0.7, 3.0
CLEAN = 18.0        # HR-band prominence above this = clean pulse
WIN = 20.0          # sliding window seconds
STEP = 5.0          # step seconds


def prominence(sig, fs):
    sig = np.asarray(sig, float)
    if len(sig) < 32:
        return 0.0
    sig = sig - sig.mean()
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / fs)
    p = np.abs(np.fft.rfft(sig)) ** 2
    band = (freqs >= HR_LO) & (freqs <= HR_HI)
    if not band.any():
        return 0.0
    return p[band].max() / (np.median(p[band]) or 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path")
    args = ap.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path)
    ppg = [s for s in streams if s["info"]["type"][0] == "PPG" and len(s["time_series"]) > 0]
    marks = [s for s in streams if s["info"]["type"][0] == "Markers"]

    med_start = None
    for m in marks:
        for val, t in zip(m["time_series"], m["time_stamps"]):
            v = val[0] if isinstance(val, (list, tuple)) else val
            if v == "meditation_start":
                med_start = t
    if med_start is None:
        print("No meditation_start marker found; cannot define baseline.")
        return

    rec_start = min(np.asarray(s["time_stamps"])[0] for s in ppg)
    pre_len = med_start - rec_start
    print(f"Recording start (first sample): t={rec_start:.1f}")
    print(f"meditation_start:               t={med_start:.1f}")
    print(f"Pre-meditation window:          {pre_len:.0f} s ({pre_len/60:.1f} min)\n")

    print(f"{'PARTICIPANT':12} {'verdict':16} {'settle@(s)':>10} {'settled-strength':>16}")
    print("-" * 60)

    settle_times = []
    for s in ppg:
        name = s["info"]["name"][0]
        data = np.asarray(s["time_series"], float)
        ts = np.asarray(s["time_stamps"], float)

        # choose best (group, col) using the settled reference window (last 40s before meditation)
        ref_a, ref_b = med_start - 40, med_start
        best = (0.0, 0, 0)
        for g in (0, 1):
            tg = ts[g::2]
            dg = data[g::2]
            fs = 1.0 / np.median(np.diff(tg))
            m = (tg >= ref_a) & (tg < ref_b)
            for c in range(dg.shape[1]):
                pr = prominence(dg[m, c], fs)
                if pr > best[0]:
                    best = (pr, g, c)
        settled_strength, g, c = best
        tg = ts[g::2]
        dg = data[g::2, c]
        fs = 1.0 / np.median(np.diff(tg))

        # slide across the pre-meditation window, find first clean window
        settle = None
        t = rec_start
        while t + WIN <= med_start:
            m = (tg >= t) & (tg < t + WIN)
            if m.sum() > 32 and prominence(dg[m], fs) >= CLEAN:
                settle = t - rec_start
                break
            t += STEP

        if settled_strength < CLEAN:
            verdict = "NO PULSE (table)"
            settle_str = "-"
        else:
            verdict = "worn"
            settle_str = f"{settle:.0f}" if settle is not None else ">pre-window"
            if settle is not None:
                settle_times.append(settle)
        print(f"{name:12} {verdict:16} {settle_str:>10} {settled_strength:>16.0f}")

    print()
    if settle_times:
        rec_trim = max(settle_times)
        base_start = rec_start + rec_trim
        base_len = med_start - base_start
        print(f"Latest settle among worn bands: {rec_trim:.0f} s after recording start.")
        print(f"=> Common baseline = [rec_start + {rec_trim:.0f}s, meditation_start] "
              f"= {base_len:.0f} s ({base_len/60:.1f} min) of clean baseline.")
        print(f"   (Your +120s guess would give {med_start - (rec_start+120):.0f} s of baseline.)")


if __name__ == "__main__":
    main()
