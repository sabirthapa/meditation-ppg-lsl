"""
Network diagnostic: list every LSL stream visible to THIS laptop.

Run this on the central laptop while satellite laptops are running run_session.py.
If their PPG_* streams show up here, LabRecorder on this laptop will see them too.
If they DON'T show up, it's a network problem (see notes below), not a band
problem.

Usage:
  .\\run.ps1 scripts\\list_lsl_streams.py             # one snapshot
  .\\run.ps1 scripts\\list_lsl_streams.py --watch     # refresh every few seconds
"""

import argparse
import time

from pylsl import resolve_streams


def show_once(wait_seconds: float):
    streams = resolve_streams(wait_time=wait_seconds)
    if not streams:
        print("No LSL streams found on the network.")
        return

    print(f"Found {len(streams)} stream(s):\n")
    print(f"{'name':24} {'type':8} {'ch':>3} {'srate':>7}  {'source_id':24} host")
    print("-" * 90)
    for info in streams:
        print(
            f"{info.name():24} {info.type():8} {info.channel_count():>3} "
            f"{info.nominal_srate():>7.1f}  {info.source_id():24} {info.hostname()}"
        )


def main():
    parser = argparse.ArgumentParser(description="List visible LSL streams.")
    parser.add_argument("--watch", action="store_true", help="Keep refreshing.")
    parser.add_argument("--wait", type=float, default=3.0, help="Resolve wait seconds.")
    parser.add_argument("--interval", type=float, default=4.0, help="Refresh interval in --watch mode.")
    args = parser.parse_args()

    if not args.watch:
        show_once(args.wait)
        return

    print("Watching for LSL streams (Ctrl+C to stop)...\n")
    try:
        while True:
            print("=" * 90)
            show_once(args.wait)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
