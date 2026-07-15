"""
Quick PPG viewer: plot the pulse waveform from one band in an XDF and estimate HR.

Handles the OS61 quirk automatically: the stream interleaves two frame types and
each row repeats a channel; this script de-interleaves, picks the channel with the
strongest heartbeat, band-pass-cleans it for viewing, marks detected beats, and
prints/plots the heart rate. Saves a PNG.

Usage:
  .\\run.ps1 scripts\\plot_ppg.py "C:\\path\\recording.xdf"
  .\\run.ps1 scripts\\plot_ppg.py "C:\\path\\recording.xdf" --stream P01 --seconds 15 --start 30
"""

import argparse
import os

import numpy as np
import pyxdf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HR_LO, HR_HI = 0.7, 3.0


def hr_prominence(sig, fs):
    sig = sig - sig.mean()
    if len(sig) < 32:
        return 0.0, 0.0
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / fs)
    power = np.abs(np.fft.rfft(sig)) ** 2
    band = (freqs >= HR_LO) & (freqs <= HR_HI)
    if not band.any():
        return 0.0, 0.0
    bp, bf = power[band], freqs[band]
    i = np.argmax(bp)
    return bf[i] * 60.0, bp[i] / (np.median(bp) or 1.0)


def rolling_mean(x, w):
    if w < 2:
        return x
    k = np.ones(w) / w
    return np.convolve(x, k, mode="same")


def find_beats(sig, fs):
    """Simple peak picker with a refractory period (~0.4 s)."""
    thr = 0.4 * np.std(sig)
    refractory = int(0.4 * fs)
    peaks = []
    last = -refractory
    for i in range(1, len(sig) - 1):
        if sig[i] > thr and sig[i] >= sig[i - 1] and sig[i] > sig[i + 1] and (i - last) >= refractory:
            peaks.append(i)
            last = i
    return np.array(peaks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xdf_path")
    ap.add_argument("--stream", default=None, help="Stream name to plot (default: strongest-pulse PPG stream).")
    ap.add_argument("--seconds", type=float, default=15.0, help="Window length to plot.")
    ap.add_argument("--start", type=float, default=20.0, help="Seconds into the recording to start (skip settling).")
    ap.add_argument("--out", default=None, help="Output PNG path.")
    args = ap.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path)
    ppg = [s for s in streams if s["info"]["type"][0] == "PPG" and len(s["time_series"]) > 0]
    if args.stream:
        ppg = [s for s in ppg if s["info"]["name"][0] == args.stream] or ppg

    # pick stream + (frame group, column) with the strongest heartbeat
    best = None  # (prom, bpm, name, signal, fs)
    for s in ppg:
        name = s["info"]["name"][0]
        data = np.asarray(s["time_series"], dtype=np.float64)
        ts = np.asarray(s["time_stamps"], dtype=np.float64)
        fs = (len(ts) - 1) / (ts[-1] - ts[0]) / 2.0  # per frame-group rate
        for grp_idx in (0, 1):
            grp = data[grp_idx::2]
            for c in range(grp.shape[1]):
                bpm, prom = hr_prominence(grp[:, c], fs)
                if best is None or prom > best[0]:
                    best = (prom, bpm, name, grp[:, c].copy(), fs)

    prom, bpm_fft, name, sig, fs = best
    print(f"Chosen stream: {name}  (~{fs:.1f} Hz per channel, pulse strength {prom:.0f}x)")

    # clean for viewing: remove baseline wander (rolling mean over ~1.5 s)
    ac = sig - rolling_mean(sig, max(2, int(1.5 * fs)))

    # window
    start_i = int(args.start * fs)
    end_i = start_i + int(args.seconds * fs)
    start_i = max(0, min(start_i, len(ac) - 2))
    end_i = max(start_i + 2, min(end_i, len(ac)))
    seg = ac[start_i:end_i]
    t = np.arange(len(seg)) / fs

    beats = find_beats(seg, fs)
    if len(beats) >= 2:
        ibis = np.diff(beats) / fs
        hr = 60.0 / np.median(ibis)
    else:
        hr = bpm_fft

    print(f"Heart rate: ~{hr:.1f} bpm  ({len(beats)} beats in {args.seconds:.0f}s window)")

    plt.figure(figsize=(12, 4))
    plt.plot(t, seg, lw=1.0, color="#1f77b4")
    if len(beats):
        plt.plot(beats / fs, seg[beats], "o", color="#d62728", ms=5, label="beats")
    plt.title(f"PPG pulse — {name} — HR ~ {hr:.0f} bpm")
    plt.xlabel("seconds")
    plt.ylabel("pulsatile signal (baseline removed)")
    plt.grid(alpha=0.3)
    if len(beats):
        plt.legend()
    plt.tight_layout()

    out = args.out or os.path.splitext(args.xdf_path)[0] + f"_{name}_ppg.png"
    plt.savefig(out, dpi=110)
    print(f"Saved plot: {out}")


if __name__ == "__main__":
    main()
