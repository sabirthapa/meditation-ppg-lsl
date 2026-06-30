"""
Fault-tolerant PPG recording session.

Reads a laptop config (from scripts/enroll_bands.py), connects each band by its
stable BLE address, streams to LSL, and is built to survive a real, long session:

  - per-band failure isolation: one band failing to connect does NOT abort the
    others; the session records the rest and reports which are missing
  - auto-reconnect: bands that drop mid-session are reconnected (rate-limited)
    and resume streaming on the SAME LSL stream
  - stall detection: a band that is "connected" but stops producing samples for
    --stall-seconds is treated as dropped and reconnected
  - live per-band health so you can see what's flowing

Usage:
  .\\run.ps1 scripts\\run_session.py --config configs\\laptop_01.json --duration 120
"""

import argparse
import time

from src.band.band_runner import BandRunner
from src.utils.config_loader import load_config


def main():
    parser = argparse.ArgumentParser(description="Fault-tolerant PPG recording session.")
    parser.add_argument("--config", required=True, help="Path to laptop config JSON.")
    parser.add_argument("--duration", type=int, default=120, help="Recording duration in seconds.")
    parser.add_argument("--scan-seconds", type=int, default=15, help="BLE scan timeout per connect.")
    parser.add_argument("--connect-attempts", type=int, default=3, help="Initial connect attempts per band.")
    parser.add_argument("--reconnect-backoff", type=float, default=5.0, help="Min seconds between reconnect attempts per band.")
    parser.add_argument("--stall-seconds", type=int, default=8, help="Treat a connected band with no new samples for this long as dropped.")
    parser.add_argument("--no-reconnect", action="store_true", help="Disable mid-session auto-reconnect.")
    parser.add_argument("--battery-interval", type=int, default=60, help="Seconds between battery re-reads per band (0 disables periodic reads).")
    args = parser.parse_args()

    config = load_config(args.config)

    print("Recording session")
    print("=================")
    print(f"Laptop ID: {config['laptop_id']}")
    print(f"Configured bands: {len(config['bands'])}")
    print(f"Duration: {args.duration}s | reconnect: {not args.no_reconnect}")
    print()

    runners = [
        BandRunner(
            participant_id=b["participant_id"],
            device_identifier=b["device_identifier"],
            stream_name=b["stream_name"],
            scan_seconds=args.scan_seconds,
            connect_attempts=args.connect_attempts,
        )
        for b in config["bands"]
    ]

    # ── connect phase (isolated per band) ───────────────────────────────────
    print("Connecting bands (one failure will not stop the others)...")
    connected = []
    failed = []
    for r in runners:
        print(f"\n[{r.participant_id}] target {r.device_identifier}")
        if r.connect(verbose=True):
            print(f"[{r.participant_id}] connected. LSL stream '{r.stream_name}' is live.")
            connected.append(r)
        else:
            print(f"[{r.participant_id}] FAILED to connect — skipping (session continues).")
            failed.append(r)

    if not connected:
        raise RuntimeError("No bands connected. Nothing to record.")

    print()
    print(f"Connected {len(connected)}/{len(runners)} bands.")
    if failed:
        print("Missing: " + ", ".join(f"{r.participant_id}({r.device_identifier})" for r in failed))
    print()
    print("Active LSL streams:")
    for r in connected:
        print(f"  {r.stream_name}")
    print()
    print("In LabRecorder: click Update, select these PPG streams (+ MeditationMarkers), then Start.")
    print()

    print("Starting sensors...")
    for r in connected:
        try:
            r.start_sensors()
        except Exception as exc:
            print(f"  [{r.participant_id}] start sensors failed: {exc}")

    # ── recording loop ──────────────────────────────────────────────────────
    print("\nRecording...\n")
    last_battery_poll = time.monotonic()
    try:
        for remaining in range(args.duration, 0, -1):
            for r in connected:
                total, delta = r.health_tick()

                needs_reconnect = (not r.connected) or (r.stalled_seconds >= args.stall_seconds)
                if needs_reconnect and not args.no_reconnect:
                    if r.stalled_seconds >= args.stall_seconds and r.connected:
                        print(f"  [{r.participant_id}] no data for {r.stalled_seconds}s — treating as dropped.")
                        r.connected = False
                    r.try_reconnect(backoff_seconds=args.reconnect_backoff, verbose=True)

            # Periodically re-read battery (kept infrequent so it doesn't steal BLE airtime).
            if args.battery_interval > 0 and (time.monotonic() - last_battery_poll) >= args.battery_interval:
                for r in connected:
                    r.read_battery()
                last_battery_poll = time.monotonic()

            parts = []
            for r in connected:
                s = r.session.summary()
                state = "OK " if r.connected else "DOWN"
                parts.append(
                    f"{r.participant_id}[{state}] samp={s['sample_count']}"
                    + (f" bat={r.battery}" if r.battery is not None else "")
                    + (f" rc={r.reconnect_count}" if r.reconnect_count else "")
                )
            print(f"{remaining:4d}s | " + " | ".join(parts))
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        print("\nStopping bands...")
        for r in connected:
            r.stop()

    # ── summary ─────────────────────────────────────────────────────────────
    print("\nSession summary")
    print("---------------")
    any_samples = False
    for r in runners:
        s = r.session.summary()
        status = "connected" if r in connected else "NEVER CONNECTED"
        print(f"\n{r.participant_id} ({r.stream_name}) [{status}]")
        print(f"  Device: {r.device_identifier}")
        print(f"  Battery:       {r.battery}")
        print(f"  Notifications: {s['notification_count']}")
        print(f"  Ignored:       {s['ignored_notification_count']}")
        print(f"  Samples:       {s['sample_count']}")
        print(f"  Reconnects:    {r.reconnect_count}")
        if s["sample_count"] > 0:
            any_samples = True

    if failed:
        print("\nWARNING: these bands never connected: "
              + ", ".join(r.participant_id for r in failed))

    if not any_samples:
        raise RuntimeError("No PPG samples were streamed from any band.")

    print("\nSession finished.")


if __name__ == "__main__":
    main()
