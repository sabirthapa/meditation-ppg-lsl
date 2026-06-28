"""
Diagnostic: are the OS61 BLE addresses STABLE or ROTATING?

This is the question the whole connection strategy hinges on:
  - STABLE (static-random) addresses never change while powered -> fixed-MAC
    enrollment is reliable.
  - ROTATING (resolvable-private) addresses change on a timer (~15 min) -> we
    need a different strategy.

It repeatedly scans for ~MONITOR_MINUTES and tracks, per OS61 address:
  - how many scans it appeared in
  - first/last time offset (seconds)
  - RSSI range (your own bands on the desk should be strong & steady, e.g.
    -45..-60 dBm; faraway/other-room bands will be weaker / intermittent)

Interpretation at the end:
  - An address seen in (almost) every scan for the whole window = STABLE.
  - Addresses that appear then vanish, replaced by new ones = ROTATING or
    other bands moving in/out of range.
"""

import time

import simplepyble


SCAN_SECONDS = 8
GAP_SECONDS = 2
MONITOR_MINUTES = 3
NAME_FILTER = "OS61"


def main():
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapter found.")
        return

    adapter = adapters[0]
    deadline = time.time() + MONITOR_MINUTES * 60
    start = time.time()

    # address -> stats
    stats = {}
    scan_index = 0

    print(f"Monitoring OS61 addresses for ~{MONITOR_MINUTES} min "
          f"({SCAN_SECONDS}s scans)...\n")

    while time.time() < deadline:
        scan_index += 1
        seen = {}

        def on_found(p, _seen=seen):
            name = p.identifier() or ""
            if NAME_FILTER.upper() in name.upper():
                _seen[p.address()] = p.rssi()

        adapter.set_callback_on_scan_found(on_found)
        adapter.scan_start()
        time.sleep(SCAN_SECONDS)
        adapter.scan_stop()

        offset = time.time() - start
        for addr, rssi in seen.items():
            s = stats.setdefault(addr, {
                "count": 0, "first": offset, "last": offset,
                "rssi_min": rssi, "rssi_max": rssi,
            })
            s["count"] += 1
            s["last"] = offset
            s["rssi_min"] = min(s["rssi_min"], rssi)
            s["rssi_max"] = max(s["rssi_max"], rssi)

        addrs = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
        summary = ", ".join(f"{a}({r})" for a, r in addrs) or "(none)"
        print(f"scan {scan_index:2d} @ {offset:5.1f}s: {len(seen)} bands | {summary}")

        time.sleep(GAP_SECONDS)

    print("\n==================== STABILITY SUMMARY ====================")
    print(f"Total scans: {scan_index}\n")
    print(f"{'address':20} {'seen':>6} {'first':>7} {'last':>7} {'rssi range':>14}")
    print("-" * 60)
    for addr, s in sorted(stats.items(), key=lambda kv: kv[1]["count"], reverse=True):
        seen_pct = 100.0 * s["count"] / scan_index
        print(f"{addr:20} {s['count']:>3}/{scan_index:<2} "
              f"{s['first']:6.1f}s {s['last']:6.1f}s "
              f"  {s['rssi_min']:>4}..{s['rssi_max']:<4} dBm "
              f"{'  <== persistent' if seen_pct >= 80 else ''}")
    print()
    print("Persistent addresses (seen in >=80% of scans) are STABLE and safe to")
    print("pin in a config. If your 4 desk bands each show one persistent address,")
    print("fixed-MAC enrollment will work.")


if __name__ == "__main__":
    main()
