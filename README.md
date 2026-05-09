# Flashcard Guru Remote

A free Anki desktop add-on that pairs with the [Flashcard Guru](https://flashcard-guru.flashify.app) iOS app to turn your iPhone into a wireless review remote.

- 10-second QR pairing — no IP / port juggling
- Supports cheap controllers (8BitDo Zero 2, micro) when bridged through your phone — even ones AnkiMobile rejects
- LAN-only, no cloud, no telemetry
- Open source (LGPL-3.0)

> **Companion app required.** This add-on does nothing on its own — install the [Flashcard Guru](https://flashcard-guru.flashify.app) iOS app to use it.

## Install

1. In Anki Desktop, open `Tools → Add-ons → Get Add-ons…`
2. Paste the AnkiWeb code: *(coming soon)*
3. Restart Anki
4. The first time the add-on starts, macOS asks **"Allow incoming connections?"** — click **Allow**. If you missed it, go to `System Settings → Network → Firewall → Options` and add Python.

## Use

1. In Anki: `Tools → Connect Phone (Flashcard Guru Remote)…` — a QR code appears
2. In the iOS app: `Settings → Anki Remote → Pair with Mac` — scan the QR code
3. Done — open any deck on your Mac and your iPhone takes over

## Development

```bash
# Install dev dependencies (only for running tests)
pip install -e ".[test]"

# Run tests
pytest
```

Vendored runtime deps live under `flashcard_guru_remote/vendor/` and are populated by:

```bash
./scripts/vendor_deps.sh
```

## License

LGPL-3.0-or-later. See `LICENSE`. The companion iOS app (Flashcard Guru) is closed-source; only this add-on is open source.

## Requirements

- Anki Desktop **2.1.55+** (Qt6 builds recommended)
- macOS (officially supported); Windows works but is not actively QA'd
