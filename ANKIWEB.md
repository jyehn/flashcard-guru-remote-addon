# AnkiWeb listing copy

Source of truth for the public AnkiWeb add-on page. Update here, then
paste into https://ankiweb.net/shared/upload (or the existing entry's
"Edit" page) before each release.

**Live listing**: <https://ankiweb.net/shared/info/1196082853>
**AnkiWeb code (for `Tools → Add-ons → Get Add-ons…`)**: `1196082853`

---

## Title

Flashcard Guru Remote — iPhone wireless remote

(AnkiWeb caps titles at ~60 chars; the above is 50.)

---

## Tagline

Free wireless remote for Anki Desktop, paired in 10 seconds with the
Flashcard Guru iOS app — works with cheap 8BitDo controllers AnkiMobile
won't pair with.

---

## Description (markdown)

> AnkiWeb renders this in a restricted markdown subset — keep it simple.

```markdown
**Flashcard Guru Remote** turns your iPhone into a wireless review remote
for Anki Desktop. Pair in 10 seconds via QR code, then drive
*Show Answer / Again / Hard / Good / Easy / Undo / Replay* from your couch,
treadmill, or wherever you're studying.

This add-on is the **companion to the [Flashcard Guru iOS app][app]**,
which is free in the App Store. Both pieces are required.

### Why another Anki remote?

* **Your phone is already a remote.** No $40-60 hardware purchase.
* **The Flashcard Guru iOS app supports cheap 8BitDo controllers in
  Keyboard Mode** — including the popular Zero 2 and Micro that
  AnkiMobile won't pair with. Plug your 8BitDo into your iPhone, and
  every button press becomes an Anki review action over Wi-Fi.
* **LAN-only.** No cloud, no telemetry. Pairing token never leaves
  your network.
* **Open source** (LGPL-3.0). Audit the code, fork it, contribute fixes.

### Setup

1. Install this add-on (Anki → Tools → Add-ons → Get Add-ons → paste
   this page's code), then **restart Anki**.
2. Install [Flashcard Guru][app] on your iPhone.
3. In Anki: **Tools → Connect Phone (Flashcard Guru Remote)…** — a QR
   code appears.
4. In Flashcard Guru: **Settings → Anki Remote → Pair with Mac** — scan
   the QR code.
5. Done. Open any deck on your Mac and your iPhone takes over.

### First-launch macOS firewall

The first time the server starts, macOS asks
*"Allow incoming connections?"* — **click Allow.** If you missed it,
go to *System Settings → Network → Firewall → Options* and add Python.

### Requirements

* Anki Desktop **2.1.55+** (Qt6 builds recommended). Earlier versions
  don't have the gui_hooks API we rely on.
* macOS — officially supported. Windows works but isn't actively QA'd.
* iPhone with iOS 16 or later, on the same Wi-Fi as the Mac.
* The free [Flashcard Guru iOS app][app].

### Privacy

* No data leaves your LAN. Pairing happens over a local WebSocket the
  add-on opens on a private interface; we reject connections from
  non-private IP ranges as a safety measure.
* Pairing tokens are stored on your Mac (Anki add-on config) and on
  your iPhone (iOS Keychain). Revoking a phone in
  *Tools → Connect Phone* invalidates its token immediately.
* No analytics, no ads, no upload of your decks or cards.

### Source code & support

* Add-on source: <https://github.com/rainverse/flashcard-guru-remote>
* iOS app + support: <https://flashcard-guru.flashify.app>
* Bug reports: <https://flashcard-guru.flashify.app/support>

[app]: https://apps.apple.com/app/flashcard-guru
```

---

## Tags

(AnkiWeb tags are space-separated, ~30 char limit each.)

```
remote ios bluetooth gamepad 8bitdo wireless companion
```

---

## Tested with

```
Anki 2.1.55, 2.1.65, 24.x (Qt6, macOS)
```

---

## Conflicts

```
(none known)
```

---

## Submission checklist

- [ ] Bump `human_version` in `manifest.json` and the entry at the top of
      `CHANGELOG.md`
- [ ] `./scripts/vendor_deps.sh` — refresh vendored websockets / qrcode
- [ ] `pytest` — 68 tests, all green
- [ ] `./scripts/build_ankiaddon.sh` — produces
      `dist/flashcard-guru-remote-<version>.ankiaddon`
- [ ] Sideload that file into a clean Anki profile and pair from a real
      iPhone (see `docs/release/anki-remote-qa-checklist.md`)
- [ ] On <https://ankiweb.net/shared/upload>, replace the body with the
      "Description (markdown)" section above, refresh tags / tested-with,
      attach the new `.ankiaddon`
- [ ] After AnkiWeb assigns a numeric add-on code, paste it into
      `README.md` and the iOS Settings footer copy

---

## Required screenshots (1280×800 max for AnkiWeb)

> Capture the *Mac side* only — AnkiWeb hosts the listing, the iOS side
> goes on the App Store. Use a clean Anki profile with only this add-on
> installed so the menu is uncluttered.

1. **`screenshot-tools-menu.png`** — `Tools` menu with the
   "Connect Phone (Flashcard Guru Remote)…" entry highlighted
2. **`screenshot-pairing-dialog.png`** — the pairing dialog with QR code
   visible and "Paired phones: Jam's iPhone" in the list
3. **`screenshot-multi-nic.png`** — Network interface dropdown expanded
   showing both Wi-Fi and Ethernet IPs, demonstrating multi-interface
   support
