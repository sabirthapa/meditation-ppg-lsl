import threading
import time

from src.band.ppg_session import PpgSession
from src.band.single_band_connector import connect_single_band
from src.lsl.ppg_outlet import PpgLslOutlet


# All scan/connect operations share one physical Bluetooth adapter. Serialize
# them so a mid-session reconnect never collides with another connect/scan.
_ble_lock = threading.Lock()


class BandRunner:
    """
    Owns the full lifecycle of one wristband for a recording session:
    connect -> set up -> stream to LSL, and recover from drops.

    Connection uses the band's STABLE BLE address (see scripts/enroll_bands.py).
    The LSL outlet and PpgSession are created ONCE and reused across reconnects,
    so cumulative counts and LSL consumers survive a band dropping out.
    """

    def __init__(
        self,
        participant_id: str,
        device_identifier: str,
        stream_name: str,
        scan_seconds: int = 15,
        connect_attempts: int = 3,
    ):
        self.participant_id = participant_id
        self.device_identifier = device_identifier
        self.stream_name = stream_name
        self.scan_seconds = scan_seconds
        self.connect_attempts = connect_attempts

        self.outlet = PpgLslOutlet(
            participant_id=participant_id,
            stream_name=stream_name,
            source_id=f"{participant_id}_{device_identifier}",
            channel_count=6,
        )
        self.session = PpgSession(participant_id=participant_id, outlet=self.outlet)

        self.band = None
        self.connected = False
        self.reconnect_count = 0
        self.ever_connected = False

        # health bookkeeping (driven by the recorder loop)
        self.last_sample_count = 0
        self.stalled_seconds = 0
        self._last_reconnect_monotonic = 0.0

    # ── connection lifecycle ────────────────────────────────────────────────

    def _attach(self, band):
        self.band = band
        self.session.attach_devices(band.watch, band.nrf, band.nim, band.optical)

        band.watch.EnableNotifications(True)
        self.session.init_registers()
        band.watch.NotificationAvailable += self.session.on_notification
        band.watch.Disconnected += self._on_disconnected
        band.watch.Error += self._on_error

    def _on_disconnected(self, _sender, _event):
        self.connected = False

    def _on_error(self, _sender, _event):
        # Packet-loss/errors are surfaced via counts elsewhere; don't spam here.
        pass

    def _try_connect_once(self, verbose: bool) -> bool:
        try:
            with _ble_lock:
                band = connect_single_band(
                    target_identifier=self.device_identifier,
                    scan_seconds=self.scan_seconds,
                    verbose=verbose,
                )
            self._attach(band)
            self.connected = True
            self.ever_connected = True
            self.stalled_seconds = 0
            return True
        except Exception as exc:
            if verbose:
                print(f"  [{self.participant_id}] connect failed: {exc}")
            return False

    def connect(self, verbose: bool = True) -> bool:
        """Initial connect with bounded retries."""
        for attempt in range(1, self.connect_attempts + 1):
            if verbose:
                print(f"  [{self.participant_id}] connect attempt "
                      f"{attempt}/{self.connect_attempts} ...")
            if self._try_connect_once(verbose=verbose):
                return True
            time.sleep(1)
        return False

    def start_sensors(self):
        if self.band is not None:
            self.band.nrf.EnableSensors(True)

    def try_reconnect(self, backoff_seconds: float = 5.0, verbose: bool = True) -> bool:
        """One reconnect attempt, rate-limited by backoff. Returns True on success."""
        now = time.monotonic()
        if now - self._last_reconnect_monotonic < backoff_seconds:
            return False
        self._last_reconnect_monotonic = now
        self.reconnect_count += 1

        if verbose:
            print(f"  [{self.participant_id}] reconnecting "
                  f"(attempt #{self.reconnect_count}) ...")

        if self._try_connect_once(verbose=verbose):
            self.start_sensors()
            if verbose:
                print(f"  [{self.participant_id}] reconnected.")
            return True
        return False

    def stop(self):
        if self.band is None:
            return
        try:
            self.band.nrf.EnableSensors(False)
        except Exception as exc:
            print(f"  [{self.participant_id}] disable sensors failed: {exc}")
        try:
            self.band.watch.NotificationAvailable -= self.session.on_notification
        except Exception:
            pass
        try:
            self.band.watch.EnableNotifications(False)
        except Exception:
            pass

    # ── health ──────────────────────────────────────────────────────────────

    def health_tick(self):
        """Call once per second. Returns (state, total_samples, delta)."""
        s = self.session.summary()
        total = s["sample_count"]
        delta = total - self.last_sample_count
        self.last_sample_count = total

        if self.connected and delta == 0:
            self.stalled_seconds += 1
        else:
            self.stalled_seconds = 0

        return total, delta
