# Meditation Group-Synchrony PPG Study — Data & Collection Brief (for analysis)

This document explains how the PPG data was collected and what is inside the
recordings, so the analysis phase can start with full context.

## 1. Goal
We study **physiological synchrony during group meditation**. We record
**PPG (photoplethysmography)** from wrist wristbands worn by a group of participants,
derive **heart rate (HR)** and **heart-rate variability (HRV)** per person, then
analyze **inter-subject synchrony** — comparing a **baseline** period vs. a
**meditation** period.

## 2. Hardware
- Wristbands: **MAXREFDES280 / "OS61"** (Maxim optical PPG sensor, MAX86171-class),
  streaming raw optical data over **Bluetooth Low Energy (BLE)**.
- Each band is a separate BLE device; on Windows it advertises the name "OS61 Demo"
  and a (stable) BLE MAC address.

## 3. How data was collected
- **Multiple Windows laptops**, each connected to a **subset of bands** (~6–8 bands
  per laptop — a single Bluetooth adapter can only stream ~8 at full rate).
- Each laptop runs a recorder that connects its bands and publishes **one LSL
  (Lab Streaming Layer) stream per band**.
- All laptops are on the **same local network**. One **central laptop** runs
  **LabRecorder**, which discovers **all bands from all laptops** and records them
  into a **single .xdf file** per session.
- LabRecorder **time-synchronizes the streams across laptops** (it stores clock-offset
  measurements; pyxdf applies them on load), so all streams share one timeline.
- A separate **marker stream** (see §6) is recorded alongside for event timing.
- One file per day/session: **day1.xdf, day2.xdf, …**

## 4. File format
Each `.xdf` contains, per session:
- **N PPG streams** — one per participant. Stream `name` = the participant's
  name/ID (e.g. "P01"). `type` = "PPG".
- **1 marker stream** — `name` = "MeditationMarkers", `type` = "Markers".

Load with Python `pyxdf.load_xdf(path)` → returns a list of streams; each has
`stream["time_series"]` (samples) and `stream["time_stamps"]` (LSL clock, seconds).
A converter to per-stream CSV exists (`scripts/xdf_to_csv.py`) → columns
`timestamp, ppg_0..ppg_5` for PPG, `timestamp, value` for markers.

## 5. PPG data columns — IMPORTANT, read before analyzing
Each PPG stream stores **6 columns per sample** and a nominal rate of **~67 Hz**,
but the "6 channels" label is misleading. Verified structure:
- The **6 columns are really 2 optical channels, each repeated 3×** per BLE packet
  (cols 0/2/4 ≈ one channel, cols 1/3/5 ≈ the other). The 3 repeats are likely
  **3 consecutive sub-samples** (so the true per-channel rate may be ~100 Hz —
  confirm against the MAX86171 / OS61 datasheet).
- Consecutive samples **interleave two firmware "frame types"** (they alternate
  sample-to-sample), distinguishable by magnitude:
  - one frame ≈ **1,000,000** counts → this is the **clean, usable PPG**;
  - the other ≈ **15,000,000** counts → **saturates on skin, not usable**.
- Values are **raw 24-bit optical ADC counts** (range 0–16,777,215), **unfiltered**.
  The large DC baseline is ambient/reflectance; the heartbeat is the small pulsatile
  variation on top.

**Required first step:** de-interleave the two frame types (by magnitude, ~1e6 vs
~1.5e7), keep the **non-saturating (~1e6) channel**, and treat that as the PPG.
Do NOT feed the raw 6 columns into a peak detector — it alternates between the two
modes and produces garbage.

## 6. Markers (event timeline)
The "MeditationMarkers" stream holds text events with LSL timestamps on the same
clock as the PPG. Intended events:
`recording_start, baseline_start, baseline_end, meditation_start, meditation_end,
recording_stop`.
In practice we mostly used **recording_start → meditation_start → meditation_end →
recording_stop**. Use these to segment **baseline** (recording_start → meditation_start)
and **meditation** (meditation_start → meditation_end).

## 7. Per-session data-quality notes (must handle)
- **Bands on a table / absent participants:** an unworn band still records, but shows
  **no heartbeat** (flat/noisy). QC every participant and exclude no-pulse streams.
- **Missing markers on some days:** e.g., one day the `recording_start` marker was
  not pushed. Reconstruct "recording start" from the **first sample timestamp**, and
  **trim the first ~1–2 min** (participants were still putting bands on = motion / no
  contact). Keep the **baseline definition consistent across all days** (e.g., a fixed
  window ending at `meditation_start`).
- **Short baselines:** some days have a short pre-meditation period (~1–4 min).
- **Slightly variable rates:** most bands ~67 Hz; occasionally a band ~64–65 Hz. Fine.
- **Same participant = same physical band across days** (bands are labeled), so
  within-subject comparisons across days are valid.

## 8. Analysis objectives
Per participant, per session:
1. De-interleave → isolate clean PPG channel (§5).
2. Band-pass (~0.5–4 Hz), detect systolic peaks (use interpolation for sub-sample
   peak timing → better HRV precision given the modest sample rate).
3. Compute **HR** and **HRV** (time-domain: SDNN, RMSSD, pNN50; frequency-domain
   LF/HF with caveats about sample rate & short baselines).
4. Signal-quality index per participant; drop bad segments / participants.

Group level:
5. Segment into **baseline** vs **meditation** using markers.
6. Resample HR/IBI to a **common grid** (e.g., 4 Hz) across participants.
7. Quantify **inter-subject synchrony** (e.g., pairwise windowed correlation,
   phase-locking, or coherence of HR/IBI), and **compare meditation vs baseline**
   (is synchrony higher during meditation?).
8. Optionally compare across days.

## 9. Key caveats for the analyst
- De-interleave + pick the clean channel BEFORE anything else.
- Confirm the true per-channel sample rate (the 3× sub-sample question) against the
  sensor datasheet before finalizing HRV methods.
- Timestamps are already cross-laptop clock-aligned — use them directly.
- Verify per-participant signal quality; exclude table / absent bands.
- Baseline windows may be short and defined differently if markers were missed —
  keep the definition consistent across days.

## 10. Repo scripts useful for analysis / QC
- `scripts/xdf_to_csv.py` — export each stream to CSV.
- `scripts/check_gaps.py` — detect recording gaps / a laptop that dropped out.
- `scripts/show_band_map.py` — recover participant ↔ device-address mapping.
- `scripts/plot_ppg.py` — quick pulse-waveform plot + HR estimate (needs matplotlib).

> Note: participant configs and raw recordings are intentionally NOT stored in this
> (public) repository — they contain identifiable data. Keep them local / private.
