"""Method dispatch — routes incoming WebSocket requests to AnkiBridge calls.

The dispatcher is intentionally Anki-agnostic; it talks to an `AnkiBridge`
abstraction so unit tests can substitute a fake.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Protocol


class DispatchError(Exception):
    """Raised on a request the dispatcher rejects (validation or state)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class AnkiBridge(Protocol):
    """Surface the dispatcher needs from the Anki main window.

    The concrete implementation (`MainThreadAnkiBridge`) handles thread
    marshalling so all calls happen on Anki's main thread.
    """

    def is_in_review(self) -> bool: ...
    def show_answer(self) -> dict[str, Any]: ...
    def answer_card(self, ease: int) -> dict[str, Any]: ...
    def replay_audio(self) -> None: ...
    def undo(self) -> dict[str, Any]: ...
    def state_snapshot(self) -> dict[str, Any]: ...


HandlerFn = Callable[[dict[str, Any]], dict[str, Any]]


class Dispatcher:
    def __init__(self, bridge: AnkiBridge):
        self._bridge = bridge
        self._handlers: dict[str, HandlerFn] = {
            "review.showAnswer": self._show_answer,
            "review.answerCard": self._answer_card,
            "review.replayAudio": self._replay_audio,
            "review.undo": self._undo,
            "state.get": self._state_get,
            "ping": self._ping,
        }

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(method)
        if handler is None:
            raise DispatchError("unknown_method", f"Unknown method: {method}")
        return handler(params)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _require_review(self) -> None:
        if not self._bridge.is_in_review():
            raise DispatchError(
                "not_in_review",
                "Open a deck on your Mac to start reviewing.",
            )

    def _show_answer(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_review()
        return self._bridge.show_answer()

    def _answer_card(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_review()
        ease = params.get("ease")
        if not isinstance(ease, int) or isinstance(ease, bool) or ease not in (1, 2, 3, 4):
            raise DispatchError(
                "invalid_ease",
                f"ease must be one of 1, 2, 3, 4 (got {ease!r})",
            )
        return self._bridge.answer_card(ease)

    def _replay_audio(self, params: dict[str, Any]) -> dict[str, Any]:
        self._require_review()
        self._bridge.replay_audio()
        return {}

    def _undo(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._bridge.undo()

    def _state_get(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._bridge.state_snapshot()

    def _ping(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"pong": time.time()}
