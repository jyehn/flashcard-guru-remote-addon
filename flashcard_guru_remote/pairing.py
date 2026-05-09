"""Pairing helpers — token, QR payload encoding, LAN interface detection.

Pure functions / dataclasses with no Qt dependency, so they're unit-testable
without a running Anki instance.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
from dataclasses import dataclass
from io import BytesIO

from .auth import generate_token

PAIRING_PAYLOAD_VERSION = 1


@dataclass
class PairingPayload:
    """The blob encoded into the QR code that the iOS app scans."""

    version: int
    host: str
    port: int
    token: str
    name: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "v": self.version,
                "host": self.host,
                "port": self.port,
                "token": self.token,
                "name": self.name,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str) -> "PairingPayload":
        data = json.loads(raw)
        return cls(
            version=int(data["v"]),
            host=str(data["host"]),
            port=int(data["port"]),
            token=str(data["token"]),
            name=str(data.get("name", "")),
        )


def make_pairing_payload(port: int, host_ip: str, host_name: str) -> tuple[str, PairingPayload]:
    """Generate a fresh `(token, payload)` for one pairing attempt."""
    token = generate_token()
    payload = PairingPayload(
        version=PAIRING_PAYLOAD_VERSION,
        host=host_ip,
        port=port,
        token=token,
        name=host_name,
    )
    return token, payload


# ---------------------------------------------------------------------------
# LAN interface detection
# ---------------------------------------------------------------------------


def detect_primary_lan_ip() -> str:
    """Return the IP the kernel would use to reach an external host.

    No packet is actually sent; we just open a UDP socket and read back the
    bound source address. Falls back to ``127.0.0.1`` when the host is offline.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        try:
            sock.close()
        except Exception:
            pass


def parse_ifconfig_ipv4(output: str) -> list[str]:
    """Parse `ifconfig` text output, returning private/link-local IPv4 addresses.

    Extracted as a pure function so it can be unit-tested with fixture text.
    """
    ips: list[str] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("inet "):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            addr = ipaddress.ip_address(parts[1])
        except ValueError:
            continue
        if addr.is_loopback:
            continue
        if addr.is_private or addr.is_link_local:
            ips.append(str(addr))
    return ips


def list_lan_interfaces() -> list[str]:
    """Best-effort enumeration of LAN IPv4 interfaces on this host.

    Tries ``ifconfig`` (macOS / BSD); falls back to a single result from
    ``detect_primary_lan_ip()`` if enumeration fails or is empty.
    """
    try:
        out = subprocess.run(
            ["ifconfig"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return [detect_primary_lan_ip()]

    if out.returncode != 0:
        return [detect_primary_lan_ip()]

    ips = parse_ifconfig_ipv4(out.stdout)
    if not ips:
        return [detect_primary_lan_ip()]

    primary = detect_primary_lan_ip()
    if primary in ips:
        ips.remove(primary)
        ips.insert(0, primary)
    return ips


# ---------------------------------------------------------------------------
# QR rendering — defer-imports qrcode so the package loads even without it
# ---------------------------------------------------------------------------


class QRDependencyMissing(RuntimeError):
    """Raised when the optional `qrcode` library isn't available."""


def render_qr_png(payload: PairingPayload, *, box_size: int = 10, border: int = 2) -> bytes:
    """Render a payload as a PNG-encoded QR code, returning raw PNG bytes."""
    try:
        import qrcode  # type: ignore
    except ImportError as exc:  # pragma: no cover — depends on env
        raise QRDependencyMissing(
            "the 'qrcode' Python library is required to render the pairing QR"
        ) from exc

    img = qrcode.make(payload.to_json(), box_size=box_size, border=border)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
