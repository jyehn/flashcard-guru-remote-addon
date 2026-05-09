"""Persistent add-on configuration: port, network binding, paired devices.

Persistence goes through Anki's `addonManager` when running inside Anki,
and is a no-op fallback in tests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

DEFAULT_PORT = 39847
ADDON_PACKAGE = "flashcard_guru_remote"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PairedDevice:
    token: str
    device_name: str
    paired_at: str
    last_seen_at: str | None = None

    def touch(self) -> None:
        self.last_seen_at = _utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PairedDevice":
        return cls(
            token=str(data.get("token", "")),
            device_name=str(data.get("device_name", "Unknown device")),
            paired_at=str(data.get("paired_at", _utc_now_iso())),
            last_seen_at=data.get("last_seen_at"),
        )


@dataclass
class RemoteConfig:
    port: int = DEFAULT_PORT
    bound_interface: str | None = None
    paired_devices: list[PairedDevice] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> "RemoteConfig":
        raw = _read_anki_config()
        if not raw:
            return cls()
        return cls(
            port=int(raw.get("port", DEFAULT_PORT)),
            bound_interface=raw.get("bound_interface"),
            paired_devices=[
                PairedDevice.from_dict(d) for d in raw.get("paired_devices", [])
            ],
        )

    def save(self) -> None:
        _write_anki_config(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "bound_interface": self.bound_interface,
            "paired_devices": [d.to_dict() for d in self.paired_devices],
        }

    # ------------------------------------------------------------------
    # Paired device CRUD
    # ------------------------------------------------------------------

    def find_device(self, token: str) -> PairedDevice | None:
        for device in self.paired_devices:
            if device.token == token:
                return device
        return None

    def add_device(self, token: str, device_name: str) -> PairedDevice:
        device = PairedDevice(
            token=token,
            device_name=device_name,
            paired_at=_utc_now_iso(),
        )
        self.paired_devices.append(device)
        self.save()
        return device

    def remove_device(self, token: str) -> bool:
        for i, device in enumerate(self.paired_devices):
            if device.token == token:
                del self.paired_devices[i]
                self.save()
                return True
        return False


# ---------------------------------------------------------------------------
# Anki addonManager bridge (no-op outside Anki, e.g. in tests)
# ---------------------------------------------------------------------------


def _read_anki_config() -> dict[str, Any] | None:
    try:
        from aqt import mw  # type: ignore
    except ImportError:
        return None
    if mw is None or mw.addonManager is None:
        return None
    try:
        return mw.addonManager.getConfig(ADDON_PACKAGE)
    except Exception:
        return None


def _write_anki_config(data: dict[str, Any]) -> None:
    try:
        from aqt import mw  # type: ignore
    except ImportError:
        return
    if mw is None or mw.addonManager is None:
        return
    try:
        mw.addonManager.writeConfig(ADDON_PACKAGE, data)
    except Exception:
        pass
