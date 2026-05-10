"""`Tools → Connect Phone` dialog.

Shows a QR code for pairing a new iPhone and a list of currently paired
devices. Logic is intentionally thin — token / QR / IP helpers live in
`pairing.py` so they're testable without a Qt event loop.

This module imports `aqt.qt` at import time, so it must only be imported
when running inside Anki Desktop.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aqt import mw  # type: ignore
from aqt.qt import (  # type: ignore
    QColor,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QImage,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPixmap,
    QPushButton,
    Qt,
    QTimer,
    QVBoxLayout,
    qRgb,
)

from .config import PairedDevice, RemoteConfig
from .pairing import (
    QRDependencyMissing,
    compute_qr_matrix,
    list_lan_interfaces,
    make_pairing_payload,
)

if TYPE_CHECKING:
    from .server import RemoteServer

log = logging.getLogger(__name__)

QR_DISPLAY_PX = 280


class ConnectPhoneDialog(QDialog):
    """Single-window pairing dialog.

    Top half: QR + network-interface picker — for pairing a new phone.
    Bottom half: list of paired phones with a "Forget selected" button.

    Lifecycle:
      - On open: generate a fresh token, add device to config (status
        "Awaiting connection…"), render QR.
      - When server fires on_device_paired with that token, flip status to
        "✅ Paired with <name>".
      - On close: if the pending token was never used, remove it.
    """

    def __init__(self, parent, server: "RemoteServer"):
        super().__init__(parent)
        self._server = server
        self._config: RemoteConfig = server.config
        self._host_name: str = server.host_name
        self._pending_token: str | None = None

        self.setWindowTitle("Connect Phone — Flashcard Guru Remote")
        self.setMinimumWidth(440)

        self._build_ui()
        self._populate_interface_dropdown()
        self._refresh_paired_list()
        self._start_pairing()

        # Server pushes us a callback when a phone successfully says hello.
        server.on_device_paired = self._on_device_paired_from_server

        # Periodically refresh the paired-device list to reflect last_seen
        # updates that happen while the dialog is open.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_paired_list)
        self._refresh_timer.start(2000)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Pair a new iPhone")
        title.setStyleSheet("font-weight: 600; font-size: 14pt;")
        layout.addWidget(title)

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setMinimumSize(QR_DISPLAY_PX, QR_DISPLAY_PX)
        layout.addWidget(self._qr_label)

        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        nic_row = QHBoxLayout()
        nic_row.addWidget(QLabel("Network interface:"))
        self._nic_combo = QComboBox()
        self._nic_combo.setMinimumWidth(180)
        nic_row.addWidget(self._nic_combo, stretch=1)
        regen_btn = QPushButton("Regenerate code")
        regen_btn.clicked.connect(self._regenerate)
        nic_row.addWidget(regen_btn)
        layout.addLayout(nic_row)

        layout.addSpacing(12)

        paired_title = QLabel("Paired phones")
        paired_title.setStyleSheet("font-weight: 600; font-size: 13pt;")
        layout.addWidget(paired_title)

        self._paired_list = QListWidget()
        self._paired_list.setMinimumHeight(120)
        layout.addWidget(self._paired_list)

        forget_row = QHBoxLayout()
        forget_row.addStretch()
        forget_btn = QPushButton("Forget selected")
        forget_btn.clicked.connect(self._forget_selected)
        forget_row.addWidget(forget_btn)
        layout.addLayout(forget_row)

        layout.addSpacing(8)

        close_row = QHBoxLayout()
        close_row.addStretch()
        done_btn = QPushButton("Done")
        done_btn.setDefault(True)
        done_btn.clicked.connect(self.accept)
        close_row.addWidget(done_btn)
        layout.addLayout(close_row)

    def _populate_interface_dropdown(self) -> None:
        """Fill the NIC dropdown with detected LAN interfaces (primary first)."""
        self._nic_combo.blockSignals(True)
        self._nic_combo.clear()
        for ip in list_lan_interfaces():
            self._nic_combo.addItem(ip)

        if self._config.bound_interface:
            idx = self._nic_combo.findText(self._config.bound_interface)
            if idx >= 0:
                self._nic_combo.setCurrentIndex(idx)
        self._nic_combo.blockSignals(False)
        self._nic_combo.currentTextChanged.connect(self._on_interface_changed)

    # ------------------------------------------------------------------
    # Pairing actions
    # ------------------------------------------------------------------

    def _selected_ip(self) -> str:
        text = self._nic_combo.currentText()
        return text or "127.0.0.1"

    def _start_pairing(self) -> None:
        host_ip = self._selected_ip()
        token, payload = make_pairing_payload(
            port=self._config.port,
            host_ip=host_ip,
            host_name=self._host_name,
        )
        self._pending_token = token
        self._config.add_device(token=token, device_name="Awaiting connection…")
        self._refresh_paired_list()

        try:
            matrix, border = compute_qr_matrix(payload)
        except QRDependencyMissing as exc:
            log.error("QR render failed: %s", exc)
            self._qr_label.clear()
            self._status_label.setText(
                "Cannot render QR — the 'qrcode' library is missing. "
                "Reinstall the add-on or run scripts/vendor_deps.sh."
            )
            return

        # Build the QR via QImage.setPixel — the lowest-possible-level Qt
        # API for a raster bitmap. No painter, no brush, no pen, no float
        # rounding. Earlier 0.1.x releases all crashed on different layers
        # of Qt's painting pipeline; this one writes pixel bytes directly.
        n = len(matrix)
        total = n + 2 * border
        img = QImage(total, total, QImage.Format.Format_RGB32)
        img.fill(qRgb(255, 255, 255))  # white background
        black = qRgb(0, 0, 0)
        on_count = 0
        for r in range(n):
            row = matrix[r]
            for c in range(n):
                if row[c]:
                    img.setPixel(c + border, r + border, black)
                    on_count += 1

        # Diagnostic dump so we can verify the small image is correct
        # without round-tripping through the full Qt scale path.
        try:
            img.save("/tmp/flashcard-guru-qr-debug.png")
        except Exception:
            pass
        log.info(
            "QR debug: matrix=%dx%d, border=%d, total=%d, on_modules=%d",
            n, n, border, total, on_count,
        )

        pixmap = QPixmap.fromImage(img).scaled(
            QR_DISPLAY_PX,
            QR_DISPLAY_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        log.info(
            "QR debug: small=%dx%d, scaled=%dx%d",
            img.width(), img.height(), pixmap.width(), pixmap.height(),
        )
        self._qr_label.setPixmap(pixmap)
        self._status_label.setText(
            "Open Flashcard Guru on your iPhone, then\n"
            "Settings → Anki Remote → Pair with Mac. Scan this code."
        )

    def _regenerate(self) -> None:
        self._discard_pending()
        self._start_pairing()

    def _on_interface_changed(self, text: str) -> None:
        self._config.bound_interface = text or None
        self._config.save()
        self._regenerate()

    # ------------------------------------------------------------------
    # Paired devices list
    # ------------------------------------------------------------------

    def _refresh_paired_list(self) -> None:
        if self._paired_list is None:
            return
        self._paired_list.clear()
        for device in self._config.paired_devices:
            label = device.device_name
            if device.last_seen_at:
                stamp = device.last_seen_at[:19].replace("T", " ")
                label += f"   ·   last seen {stamp} UTC"
            else:
                label += "   ·   pending"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, device.token)
            self._paired_list.addItem(item)

    def _forget_selected(self) -> None:
        item = self._paired_list.currentItem()
        if item is None:
            return
        token = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(token, str) or not token:
            return
        if token == self._pending_token:
            self._pending_token = None
        self._config.remove_device(token)
        self._refresh_paired_list()

    # ------------------------------------------------------------------
    # Server callback
    # ------------------------------------------------------------------

    def _on_device_paired_from_server(self, device: PairedDevice) -> None:
        # Fired on the asyncio worker thread — bounce to the main thread so we
        # can touch Qt widgets safely.
        if mw is None:
            return
        mw.taskman.run_on_main(lambda d=device: self._handle_device_paired(d))

    def _handle_device_paired(self, device: PairedDevice) -> None:
        if self._pending_token is not None and device.token == self._pending_token:
            self._pending_token = None
            self._status_label.setText(f"✅ Paired with {device.device_name}")
        self._refresh_paired_list()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reject(self) -> None:  # type: ignore[override]
        self._cleanup()
        super().reject()

    def accept(self) -> None:  # type: ignore[override]
        self._cleanup()
        super().accept()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cleanup()
        super().closeEvent(event)

    def _cleanup(self) -> None:
        self._discard_pending()
        try:
            self._server.on_device_paired = None
        except Exception:
            pass
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()

    def _discard_pending(self) -> None:
        """Drop a pending token if the phone never finished pairing."""
        if self._pending_token is None:
            return
        device = self._config.find_device(self._pending_token)
        if device is not None and device.last_seen_at is None:
            self._config.remove_device(self._pending_token)
        self._pending_token = None
