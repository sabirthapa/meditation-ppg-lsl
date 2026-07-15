"""
Analyze a worn-vs-desk 2-band recording to figure out the real PPG structure.

The stream interleaves two firmware frame types (they alternate sample-to-sample
and have very different magnitudes), and each stored 6-col row looks like 2
values x 3 sub-samples. This script:
  - shows the raw structure,
  - de-interleaves the two frame types (even/odd samples),
  - for each frame type + column, looks for a heartbeat (dominant frequency in
    the 0.7-3.0 Hz / 42-180 bpm band) and how strong it is,
  - compares the worn band vs the desk band.

A real pulse => the WORN band shows a strong, narrow peak ~1 Hz that the DESK
band does not.
"""

import argparse
import numpy as np
import pyxdf

HR_LO, HR_HI = 0.7, 3.0  # Hz  (42-180 bpm)


def hr_peak(sig, fs):
    """Return (bpm, prominence) of the strongest spectral peak in the HR band."""
    sig = np.asarray(sig, dtype=np.float64)
    if len(sig) < 32 or fs <= 0:
        return None, 0.0
    sig = sig - sig.mean()
    # light detrend
    sig = sig - np.linspace(sig[0], sig[-1], len(sig))
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / fs)
    power = np.abs(np.fft.rfft(sig)) ** 2
    band = (freqs >= HR_LO) & (freqs <= HR_HI)
    if not band.any():
        return None, 0.0
    band_power = power[band]
    band_freqs = freqs[band]
    peak_i = np.argmax(band_power)
    peak_freq = band_freqs[peak_i]
    # prominence = peak power / median power in band
    med = np.median(band_power) or 1.0
    prominence = band_power[peak_i] / med
    return peak_freq * 60.0, prominence


def analyze_stream(name, data, ts):
    dur = ts[-1] - ts[0]
    n = data.shape[0]
    fs_all = (n - 1) / dur
    print(f"\n===== {name} =====")
    print(f"samples={n}  duration={dur:.1f}s  overall rate={fs_all:.1f} Hz  cols={data.shape[1]}")

    print("First 6 rows (raw 6 columns):")
    for i in range(6):
        print("   " + "  ".join(f"{v:11.0f}" for v in data[i]))

    even = data[0::2]
    odd = data[1::2]
    fs_grp = fs_all / 2.0
    print(f"\nInterleaved frame magnitudes (mean of col0):"
          f"  even={even[:, 0].mean():,.0f}   odd={odd[:, 0].mean():,.0f}")
    print(f"Per-frame-type rate ~{fs_grp:.1f} Hz\n")

    print(f"Heartbeat search (band {HR_LO}-{HR_HI} Hz), per frame-type x column:")
    best = (None, 0.0, None, None)
    for label, grp in (("even", even), ("odd", odd)):
        for c in range(grp.shape[1]):
            bpm, prom = hr_peak(grp[:, c], fs_grp)
            if bpm is not None:
                tag = ""
                if prom > best[1]:
                    best = (bpm, prom, label, c)
                    tag = "  <-- strongest so far"
                print(f"   {label} col{c}: peak={bpm:6.1f} bpm   strength={prom:7.1f}x{tag}")
    bpm, prom, label, c = best
    verdict = ("STRONG pulse" if prom >= 20 else
               "weak/possible pulse" if prom >= 6 else
               "NO clear pulse")
    print(f"\n  >> {name}: best = {bpm:.1f} bpm at strength {prom:.1f}x ({label} col{c})  =>  {verdict}")
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xdf_path")
    args = parser.parse_args()

    streams, _ = pyxdf.load_xdf(args.xdf_path)
    ppg = [s for s in streams if s["info"]["type"][0] == "PPG" and len(s["time_series"]) > 0]

    for s in ppg:
        name = s["info"]["name"][0]
        data = np.asarray(s["time_series"], dtype=np.float64)
        ts = np.asarray(s["time_stamps"], dtype=np.float64)
        analyze_stream(name, data, ts)


if __name__ == "__main__":
    main()
