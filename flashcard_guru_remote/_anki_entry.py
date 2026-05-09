"""Anki lifecycle wiring — only imported when running inside Anki Desktop.

Registers gui_hooks that:
  - start the WebSocket server on profile_did_open
  - stop it on profile_will_close
  - add a `Tools → Connect Phone` menu entry that opens the pairing dialog
"""
from __future__ import annotations

import logging
import socket

from aqt import gui_hooks, mw  # type: ignore
from aqt.qt import QAction  # type: ignore
from aqt.utils import showWarning  # type: ignore

from .anki_bridge import MainThreadAnkiBridge
from .config import RemoteConfig
from .dispatcher import Dispatcher
from .server import RemoteServer
from .state import StateBroadcaster

log = logging.getLogger(__name__)

_server: RemoteServer | None = None
_state: StateBroadcaster | None = None
_menu_action: QAction | None = None


def _on_profile_did_open() -> None:
    global _server, _state
    if _server is not None:
        return  # already running

    config = RemoteConfig.load()
    bridge = MainThreadAnkiBridge(mw)
    dispatcher = Dispatcher(bridge)

    host_name = _detect_host_name()

    _server = RemoteServer(
        config=config,
        dispatcher=dispatcher,
        host_name=host_name,
    )
    _state = StateBroadcaster(_server, bridge)
    _state.install()
    _server.start()

    if _server.bind_error is not None:
        log.error(
            "Flashcard Guru Remote failed to start: %s. "
            "Check the macOS firewall (System Settings → Network → Firewall).",
            _server.bind_error,
        )


def _on_profile_will_close() -> None:
    global _server, _state
    if _state is not None:
        _state.uninstall()
        _state = None
    if _server is not None:
        _server.stop()
        _server = None


def _detect_host_name() -> str:
    try:
        return socket.gethostname() or "Mac"
    except Exception:
        return "Mac"


def _on_main_window_did_init() -> None:
    """Add a `Tools` menu entry for opening the pairing dialog."""
    global _menu_action
    if _menu_action is not None:
        return
    action = QAction("Connect Phone (Flashcard Guru Remote)…", mw)
    action.triggered.connect(_show_pairing_dialog)
    mw.form.menuTools.addAction(action)
    _menu_action = action


def _show_pairing_dialog() -> None:
    if _server is None:
        showWarning(
            "Flashcard Guru Remote isn't running yet — open a profile first.",
            title="Flashcard Guru Remote",
        )
        return
    if _server.bind_error is not None:
        showWarning(
            f"Flashcard Guru Remote couldn't bind port {_server.port}.\n\n"
            "Check that the macOS firewall (System Settings → Network → "
            "Firewall) is allowing incoming connections for Anki, or change "
            "the port in the add-on config and restart Anki.\n\n"
            f"Error: {_server.bind_error}",
            title="Flashcard Guru Remote",
        )
        return

    # Late-import: ui_dialog imports aqt.qt at module level, which is fine
    # inside Anki but breaks tests that don't have Qt.
    from .ui_dialog import ConnectPhoneDialog

    dialog = ConnectPhoneDialog(mw, _server)
    dialog.exec()


gui_hooks.profile_did_open.append(_on_profile_did_open)
gui_hooks.profile_will_close.append(_on_profile_will_close)
gui_hooks.main_window_did_init.append(_on_main_window_did_init)
