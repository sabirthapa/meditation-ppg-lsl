import argparse
import threading
import time

from src.band.ppg_session import PpgSession
from src.band.single_band_connector import connect_single_band
from src.utils.config_loader import load_config


def main():
    parser = argparse.ArgumentParser(description="Debug OS61 connection lifetime.")
    parser.add_argument("--config", required=True, help="Path to config JSON.")
    parser.add_argument("--duration", type=int, default=180, help="Test duration in seconds.")
    parser.add_argument("--scan-seconds", type=int, default=10)
    parser.add_argument("--enable-notifications", action="store_true")
    parser.add_argument("--init-registers", action="store_true")
    parser.add_argument("--enable-sensors", action="store_true")
    parser.add_argument("--keep-alive-seconds", type=int, default=0)
    parser.add_argument("--connection-parameter", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)

    if len(config["bands"]) != 1:
        raise RuntimeError("Debug test expects exactly one band in config.")

    band_config = config["bands"][0]
    participant_id = band_config["participant_id"]
    device_identifier = band_config["device_identifier"]

    print("Connection lifetime debug")
    print("=========================")
    print(f"Participant ID: {participant_id}")
    print(f"Device identifier: {device_identifier}")
    print(f"Duration: {args.duration}s")
    print(f"Enable notifications: {args.enable_notifications}")
    print(f"Init registers: {args.init_registers}")
    print(f"Enable sensors: {args.enable_sensors}")
    print(f"Keep alive seconds: {args.keep_alive_seconds}")
    print(f"Connection parameter: {args.connection_parameter}")
    print()

    disconnected_event = threading.Event()

    band = connect_single_band(
        target_identifier=device_identifier,
        scan_seconds=args.scan_seconds,
        verbose=True,
    )

    session = PpgSession(participant_id=participant_id)
    session.attach_devices(
        band.watch,
        band.nrf,
        band.nim,
        band.optical,
    )

    def on_disconnected(_sender, _event):
        print()
        print(f"DISCONNECTED event received for {participant_id}")
        disconnected_event.set()

    band.watch.Disconnected += on_disconnected
    band.watch.Error += lambda _sender, event: print(f"Watch error [{participant_id}]: {event}")

    last_keep_alive = 0

    try:
        try:
            print(f"Initial battery reading: {band.nrf.ReadBattery()}")
        except Exception as exc:
            print(f"Initial battery read failed: {exc}")

        try:
            current_param = band.nrf.ReadConnectionParameters()
            print(f"Initial connection parameter: {current_param}")
        except Exception as exc:
            print(f"Read connection parameter failed: {exc}")

        if args.connection_parameter is not None:
            try:
                print(f"Setting connection parameter to: {args.connection_parameter}")
                band.nrf.ConnectionParameters(args.connection_parameter)
                time.sleep(1)

                new_param = band.nrf.ReadConnectionParameters()
                print(f"New connection parameter: {new_param}")
            except Exception as exc:
                print(f"Set connection parameter failed: {exc}")

        if args.enable_notifications:
            print("Enabling BLE notifications...")
            band.watch.EnableNotifications(True)
            band.watch.NotificationAvailable += session.on_notification

        if args.init_registers:
            print("Initializing optical registers...")
            session.init_registers()

        if args.enable_sensors:
            print("Enabling sensors...")
            band.nrf.EnableSensors(True)

        print()
        print("Starting lifetime timer...")
        start_time = time.time()

        for remaining in range(args.duration, 0, -1):
            now = time.time()
            elapsed = now - start_time
            summary = session.summary()

            if args.keep_alive_seconds > 0:
                if now - last_keep_alive >= args.keep_alive_seconds:
                    try:
                        battery = band.nrf.ReadBattery()
                        print(f"Keep-alive battery read: {battery}")
                    except Exception as exc:
                        print(f"Keep-alive failed: {exc}")
                    last_keep_alive = now

            print(
                f"Alive... elapsed={elapsed:.1f}s | "
                f"remaining={remaining}s | "
                f"samples={summary['sample_count']} | "
                f"notifications={summary['notification_count']}"
            )

            if disconnected_event.is_set():
                break

            time.sleep(1)

        elapsed = time.time() - start_time
        print()
        print(f"Finished debug test. Elapsed: {elapsed:.2f}s")
        print(f"Disconnected: {disconnected_event.is_set()}")

    finally:
        print("Cleaning up...")

        try:
            if args.enable_sensors:
                band.nrf.EnableSensors(False)
        except Exception as exc:
            print(f"Warning: failed to disable sensors: {exc}")

        try:
            if args.enable_notifications:
                band.watch.NotificationAvailable -= session.on_notification
        except Exception as exc:
            print(f"Warning: failed to remove callback: {exc}")

        try:
            if args.enable_notifications:
                band.watch.EnableNotifications(False)
        except Exception as exc:
            print(f"Warning: failed to disable notifications: {exc}")

    print("Debug connection lifetime test complete.")


if __name__ == "__main__":
    main()
