"""Anki lifecycle wiring — only imported when running inside Anki Desktop.

Registers gui_hooks that:
  - start the WebSocket server on profile_did_open
  - stop it on profile_will_close
"""
from __future__ import annotations

import logging
import socket

from aqt import gui_hooks, mw  # type: ignore

from .anki_bridge import MainThreadAnkiBridge
from .config import RemoteConfig
from .dispatcher import Dispatcher
from .server import RemoteServer
from .state import StateBroadcaster

log = logging.getLogger(__name__)

_server: RemoteServer | None = None
_state: StateBroadcaster | None = None


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


gui_hooks.profile_did_open.append(_on_profile_did_open)
gui_hooks.profile_will_close.append(_on_profile_will_close)
