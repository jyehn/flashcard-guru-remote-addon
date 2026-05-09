"""Bridges Anki gui_hooks → server.broadcast() so clients see live state."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .protocol import Event

if TYPE_CHECKING:
    from .server import RemoteServer


class StateBroadcaster:
    """Push state.changed events on review phase / app state transitions."""

    def __init__(self, server: "RemoteServer", bridge: Any):
        self._server = server
        self._bridge = bridge
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        try:
            from aqt import gui_hooks  # type: ignore
        except ImportError:
            return
        gui_hooks.reviewer_did_show_question.append(self._on_question)
        gui_hooks.reviewer_did_show_answer.append(self._on_answer)
        gui_hooks.state_did_change.append(self._on_state_change)
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        try:
            from aqt import gui_hooks  # type: ignore
        except ImportError:
            return
        try:
            gui_hooks.reviewer_did_show_question.remove(self._on_question)
        except ValueError:
            pass
        try:
            gui_hooks.reviewer_did_show_answer.remove(self._on_answer)
        except ValueError:
            pass
        try:
            gui_hooks.state_did_change.remove(self._on_state_change)
        except ValueError:
            pass
        self._installed = False

    def broadcast_now(self) -> None:
        try:
            payload = self._bridge.state_snapshot()
        except Exception:
            return
        self._server.broadcast(Event(event="state.changed", payload=payload))

    def _on_question(self, _card) -> None:
        self.broadcast_now()

    def _on_answer(self, _card) -> None:
        self.broadcast_now()

    def _on_state_change(self, *_args) -> None:
        self.broadcast_now()
