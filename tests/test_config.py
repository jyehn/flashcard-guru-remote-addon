from flashcard_guru_remote.config import DEFAULT_PORT, PairedDevice, RemoteConfig


def test_default_config():
    cfg = RemoteConfig()
    assert cfg.port == DEFAULT_PORT
    assert cfg.bound_interface is None
    assert cfg.paired_devices == []


def test_add_device():
    cfg = RemoteConfig()
    device = cfg.add_device(token="abc123", device_name="Jam's iPhone")
    assert device.token == "abc123"
    assert device.device_name == "Jam's iPhone"
    assert device.paired_at  # ISO timestamp populated
    assert len(cfg.paired_devices) == 1


def test_find_device_hit_and_miss():
    cfg = RemoteConfig()
    cfg.add_device(token="abc", device_name="A")
    cfg.add_device(token="xyz", device_name="B")
    assert cfg.find_device("abc").device_name == "A"
    assert cfg.find_device("xyz").device_name == "B"
    assert cfg.find_device("nope") is None


def test_remove_device_returns_status():
    cfg = RemoteConfig()
    cfg.add_device(token="abc", device_name="A")
    assert cfg.remove_device("abc") is True
    assert cfg.remove_device("abc") is False
    assert cfg.find_device("abc") is None


def test_to_dict_round_trip():
    cfg = RemoteConfig(port=12345)
    cfg.add_device(token="t", device_name="Phone")
    raw = cfg.to_dict()
    restored = RemoteConfig(
        port=int(raw["port"]),
        bound_interface=raw["bound_interface"],
        paired_devices=[PairedDevice.from_dict(d) for d in raw["paired_devices"]],
    )
    assert restored.port == 12345
    assert restored.paired_devices[0].token == "t"
    assert restored.paired_devices[0].device_name == "Phone"


def test_paired_device_touch_updates_timestamp():
    device = PairedDevice(token="t", device_name="P", paired_at="2026-01-01T00:00:00+00:00")
    assert device.last_seen_at is None
    device.touch()
    assert device.last_seen_at is not None


def test_paired_device_from_dict_tolerates_missing_keys():
    device = PairedDevice.from_dict({"token": "t", "device_name": "P", "paired_at": "x"})
    assert device.token == "t"
    assert device.last_seen_at is None
