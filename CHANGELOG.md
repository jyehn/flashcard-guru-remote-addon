# Flashcard Guru Remote — Changelog

## 0.1.1 (2026-05-10)

Bug fix: opening **Tools → Connect Phone…** crashed on Anki 25.x
(Python 3.13, Qt 6.9) with `ModuleNotFoundError: No module named 'PIL'`.
Older Anki point versions bundled Pillow alongside their Python; newer
ones don't, and the QR code library's PIL-backed PNG path fell over.

Switched QR rendering to the SVG path (`qrcode.image.svg.SvgImage`)
which is pure Python — no Pillow required. The Qt dialog now decodes
the SVG with `QSvgRenderer` into a `QPixmap` for display. Visually
identical; works on every Anki version we support (2.1.55 through
25.x).

## 0.1.0 (2026-05-09)

Published to AnkiWeb as code [`1196082853`](https://ankiweb.net/shared/info/1196082853).

Initial public release. Pairs with the Flashcard Guru iOS app via QR code
to drive Anki Desktop reviews from an iPhone.

- WebSocket server bound to a private LAN interface (default port 39847),
  rejects connections from outside RFC 1918 / loopback / link-local ranges.
- Token-based auth on the first frame; 3 failed attempts within 2 minutes
  ban the remote address. Constant-time token comparison.
- `Tools → Connect Phone (Flashcard Guru Remote)…` shows a QR code,
  manages a list of paired phones (multi-device supported).
- Multi-NIC dropdown for Macs with multiple active interfaces (Wi-Fi +
  Ethernet + VPN).
- Reviewer methods: `review.showAnswer`, `review.answerCard`,
  `review.replayAudio`, `review.undo`. State changes broadcast as
  `state.changed` events for live UI updates.
- Tested against Anki Desktop 2.1.55+ on macOS. Windows/Linux work but
  are not actively QA'd.
