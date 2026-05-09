import json

import pytest

from flashcard_guru_remote.pairing import (
    PAIRING_PAYLOAD_VERSION,
    PairingPayload,
    detect_primary_lan_ip,
    list_lan_interfaces,
    make_pairing_payload,
    parse_ifconfig_ipv4,
)


def test_make_pairing_payload_uniqueness():
    t1, p1 = make_pairing_payload(port=39847, host_ip="192.168.1.5", host_name="Mac")
    t2, p2 = make_pairing_payload(port=39847, host_ip="192.168.1.5", host_name="Mac")
    assert t1 != t2
    assert p1.token == t1
    assert p2.token == t2
    assert p1.version == PAIRING_PAYLOAD_VERSION


def test_pairing_payload_round_trip():
    _, payload = make_pairing_payload(
        port=39847, host_ip="192.168.1.5", host_name="Jam's Mac"
    )
    raw = payload.to_json()
    restored = PairingPayload.from_json(raw)
    assert restored == payload


def test_pairing_payload_json_shape():
    _, payload = make_pairing_payload(
        port=39847, host_ip="192.168.1.5", host_name="Mac"
    )
    data = json.loads(payload.to_json())
    assert set(data.keys()) == {"v", "host", "port", "token", "name"}
    assert data["v"] == 1
    assert data["host"] == "192.168.1.5"
    assert data["port"] == 39847
    assert isinstance(data["token"], str) and len(data["token"]) == 32


def test_pairing_payload_unicode_host_name():
    _, payload = make_pairing_payload(port=1, host_ip="10.0.0.1", host_name="家里的Mac")
    data = json.loads(payload.to_json())
    assert data["name"] == "家里的Mac"


def test_pairing_payload_from_json_rejects_garbage():
    with pytest.raises((KeyError, ValueError, TypeError)):
        PairingPayload.from_json('{"not":"a payload"}')


def test_parse_ifconfig_picks_private_ipv4():
    sample = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet6 fe80::1%lo0 prefixlen 64 scopeid 0x1
\tinet 192.168.1.42 netmask 0xffffff00 broadcast 192.168.1.255
\tnd6 options=201<PERFORMNUD,DAD>
lo0: flags=8049<UP,LOOPBACK,RUNNING,MULTICAST> mtu 16384
\tinet 127.0.0.1 netmask 0xff000000
\tinet6 ::1 prefixlen 128
utun0: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 1380
\tinet 10.10.0.5 --> 10.10.0.1 netmask 0xffffffff
"""
    ips = parse_ifconfig_ipv4(sample)
    assert "192.168.1.42" in ips
    assert "10.10.0.5" in ips
    assert "127.0.0.1" not in ips


def test_parse_ifconfig_handles_empty_output():
    assert parse_ifconfig_ipv4("") == []


def test_parse_ifconfig_skips_link_local_to_internet_only():
    # 169.254.x.x is link-local; we still surface it (preferable to 127.0.0.1
    # when nothing else is available).
    sample = "en1: flags=...\n\tinet 169.254.1.5 netmask 0xffff0000\n"
    ips = parse_ifconfig_ipv4(sample)
    assert ips == ["169.254.1.5"]


def test_parse_ifconfig_rejects_public_ip():
    sample = "wan0: flags=...\n\tinet 8.8.8.8 netmask 0xffffffff\n"
    assert parse_ifconfig_ipv4(sample) == []


def test_detect_primary_lan_ip_returns_string():
    # We can't assert a specific IP — depends on the host — but the function
    # must always return something.
    ip = detect_primary_lan_ip()
    assert isinstance(ip, str)
    assert ip  # non-empty


def test_list_lan_interfaces_never_empty():
    # Worst case it falls back to the primary IP (or 127.0.0.1).
    ips = list_lan_interfaces()
    assert isinstance(ips, list)
    assert len(ips) >= 1
    assert all(isinstance(ip, str) and ip for ip in ips)
