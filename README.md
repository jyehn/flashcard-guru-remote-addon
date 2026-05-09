# Flashcard Guru Remote

A free Anki desktop add-on that pairs with the [Flashcard Guru](https://flashcard-guru.flashify.app) iOS app to turn your iPhone into a wireless review remote.

- 10-second QR pairing — no IP / port juggling
- Supports cheap controllers (8BitDo Zero 2, micro) when bridged through your phone — even ones AnkiMobile rejects
- LAN-only, no cloud, no telemetry
- Open source (LGPL-3.0)

> **Companion app required.** This add-on does nothing on its own — install the [Flashcard Guru](https://flashcard-guru.flashify.app) iOS app to use it.

## Install

**End users:**

1. In Anki Desktop, open `Tools → Add-ons → Get Add-ons…`
2. Paste the AnkiWeb code: **`1196082853`** ([listing](https://ankiweb.net/shared/info/1196082853))
3. Restart Anki
4. The first time the add-on starts, macOS asks **"Allow incoming connections?"** — click **Allow**. If you missed it, go to `System Settings → Network → Firewall → Options` and add Python.

**Sideload (testing pre-release builds):**

Run `./scripts/build_ankiaddon.sh` — this produces
`dist/flashcard-guru-remote-<version>.ankiaddon`. Drag that file onto
Anki, or `open -a Anki dist/flashcard-guru-remote-<version>.ankiaddon`.

## Use

1. In Anki: `Tools → Connect Phone (Flashcard Guru Remote)…` — a QR code appears
2. In the iOS app: `Settings → Anki Remote → Pair with Mac` — scan the QR code
3. Done — open any deck on your Mac and your iPhone takes over

## Development

```bash
# Install dev dependencies (only for running tests)
pip install -e ".[test]"

# Run tests (68 passing)
pytest
```

Vendored runtime deps live under `flashcard_guru_remote/vendor/` and are populated by:

```bash
./scripts/vendor_deps.sh
```

To produce a release `.ankiaddon`:

```bash
./scripts/build_ankiaddon.sh
```

The output zip flattens the `flashcard_guru_remote/` package contents to
the zip root (Anki expects `__init__.py` at the top level of the addon
folder), so dev imports `from .server import …` keep working unchanged.

## Release process

See [`ANKIWEB.md`](ANKIWEB.md) for the listing copy + submission
checklist, [`CHANGELOG.md`](CHANGELOG.md) for the version history, and
[`docs/release/anki-remote-qa-checklist.md`](../../docs/release/anki-remote-qa-checklist.md)
for the manual QA passes.

## License

LGPL-3.0-or-later. See `LICENSE`. The companion iOS app (Flashcard Guru) is closed-source; only this add-on is open source.

## Requirements

- Anki Desktop **2.1.55+** (Qt6 builds recommended)
- macOS (officially supported); Windows works but is not actively QA'd
