"""Concrete AnkiBridge — calls aqt.mw.reviewer on Anki's main thread.

WebSocket message handling runs on a worker thread (asyncio loop in a daemon
thread), but Anki UI APIs must be touched from the main thread. We marshall
each call via `mw.taskman.run_on_main` and block the worker until the result
is available, so the WebSocket handler returns a synchronous response.
"""
from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, TypeVar

T = TypeVar("T")

CALL_TIMEOUT_S = 5.0


def _invoke_first(obj: Any, *names: str, args: tuple = ()) -> Any:
    """Call the first method on `obj` whose name matches one in `names`.

    Lets us support both snake_case (Anki 25.x+) and camelCase (≤2.1.x)
    surfaces of the same method without branching the caller. Raises
    AttributeError if none of the candidates exist as callables.
    """
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            return method(*args)
    raise AttributeError(
        f"{type(obj).__name__} has none of {names!r} (Anki API changed?)"
    )


class MainThreadAnkiBridge:
    """Bridges WebSocket worker thread → Anki's Qt main thread."""

    def __init__(self, mw):
        self._mw = mw

    # ------------------------------------------------------------------
    # AnkiBridge protocol
    # ------------------------------------------------------------------

    def is_in_review(self) -> bool:
        return self._call(lambda: self._mw.state == "review")

    def show_answer(self) -> dict[str, Any]:
        def fn() -> dict[str, Any]:
            # Anki's Reviewer exposes _showAnswer (single underscore prefix
            # despite being the public-by-convention API; snake_case fallback
            # is defensive in case a future version rename happens).
            # Verified against ankitects/anki release branch reviewer.py.
            _invoke_first(self._mw.reviewer, "_showAnswer", "show_answer")
            return self._snapshot()

        return self._call(fn)

    def answer_card(self, ease: int) -> dict[str, Any]:
        def fn() -> dict[str, Any]:
            _invoke_first(
                self._mw.reviewer,
                "_answerCard", "_answer_card",
                args=(ease,),
            )
            return self._snapshot()

        return self._call(fn)

    def replay_audio(self) -> None:
        def fn() -> None:
            _invoke_first(self._mw.reviewer, "replayAudio", "replay_audio")

        self._call(fn)

    def undo(self) -> dict[str, Any]:
        def fn() -> dict[str, Any]:
            # mw.undo() is the real method (the Reviewer's "u" shortcut goes
            # straight to it). mw.col.undo() is a final fallback if a future
            # version moves the entry point.
            for target, names in (
                (self._mw, ("undo", "on_undo", "onUndo")),
                (getattr(self._mw, "col", None), ("undo",)),
            ):
                if target is None:
                    continue
                try:
                    _invoke_first(target, *names)
                    return self._snapshot()
                except AttributeError:
                    continue
            raise AttributeError(
                "no undo method found on mw or mw.col — Anki API changed?"
            )

        return self._call(fn)

    def state_snapshot(self) -> dict[str, Any]:
        return self._call(self._snapshot)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _snapshot(self) -> dict[str, Any]:
        if self._mw.state != "review":
            return {
                "phase": "no-card",
                "deck": None,
                "queues": None,
                "card": None,
            }
        reviewer = self._mw.reviewer
        card = reviewer.card
        phase = "answer" if reviewer.state == "answer" else "question"
        deck = self._deck_name(card)
        return {
            "phase": phase,
            "deck": deck,
            "queues": self._queue_counts(),
            "card": self._card_summary(card) if card else None,
        }

    def _deck_name(self, card) -> str | None:
        if card is None:
            return None
        try:
            return self._mw.col.decks.name(card.did)
        except Exception:
            return None

    def _queue_counts(self) -> dict[str, int]:
        try:
            counts = self._mw.col.sched.counts()
            return {
                "new": int(counts[0]),
                "learning": int(counts[1]),
                "review": int(counts[2]),
            }
        except Exception:
            return {"new": 0, "learning": 0, "review": 0}

    def _card_summary(self, card) -> dict[str, Any]:
        return {
            "id": int(card.id),
            "due": int(card.due),
        }

    def _call(self, fn: Callable[[], T]) -> T:
        future: concurrent.futures.Future = concurrent.futures.Future()

        def runner() -> None:
            try:
                future.set_result(fn())
            except Exception as exc:  # noqa: BLE001
                future.set_exception(exc)

        self._mw.taskman.run_on_main(runner)
        return future.result(timeout=CALL_TIMEOUT_S)
