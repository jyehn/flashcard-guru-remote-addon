"""Tests for the Anki API method-name fallback logic.

These don't run a real Anki instance; they exercise `_invoke_first` against
a fake reviewer/mw that mirrors the actual method-name pattern Anki ships.

The reference for the camelCase `_showAnswer` / `_answerCard` / `replayAudio`
spelling is `qt/aqt/reviewer.py` in the ankitects/anki release branch —
verified by source inspection 2026-05-10.
"""
from __future__ import annotations

import pytest

from flashcard_guru_remote.anki_bridge import _invoke_first


class FakeReviewer25:
    """Mirrors the Anki 25.x Reviewer surface this add-on touches."""
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    def _showAnswer(self) -> None:
        self.calls.append(("_showAnswer", ()))

    def _answerCard(self, ease: int) -> None:
        self.calls.append(("_answerCard", (ease,)))

    def replayAudio(self) -> None:
        self.calls.append(("replayAudio", ()))


class FakeReviewerFuture:
    """A hypothetical future Anki where everything was snake_cased."""
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    def show_answer(self) -> None:
        self.calls.append(("show_answer", ()))

    def _answer_card(self, ease: int) -> None:
        self.calls.append(("_answer_card", (ease,)))

    def replay_audio(self) -> None:
        self.calls.append(("replay_audio", ()))


def test_invoke_first_picks_existing_method():
    rv = FakeReviewer25()
    _invoke_first(rv, "_showAnswer", "show_answer")
    assert rv.calls == [("_showAnswer", ())]


def test_invoke_first_falls_back_when_first_missing():
    rv = FakeReviewerFuture()
    _invoke_first(rv, "_showAnswer", "show_answer")
    assert rv.calls == [("show_answer", ())]


def test_invoke_first_passes_args():
    rv = FakeReviewer25()
    _invoke_first(rv, "_answerCard", "_answer_card", args=(3,))
    assert rv.calls == [("_answerCard", (3,))]


def test_invoke_first_raises_when_none_match():
    class Empty: ...
    with pytest.raises(AttributeError) as exc:
        _invoke_first(Empty(), "foo", "bar")
    assert "foo" in str(exc.value) and "bar" in str(exc.value)


def test_invoke_first_skips_non_callable_attributes():
    class Mixed:
        show_answer = "not a method, just a string"

        def _showAnswer(self):
            return "called"

    result = _invoke_first(Mixed(), "show_answer", "_showAnswer")
    assert result == "called"


@pytest.mark.parametrize("reviewer_cls", [FakeReviewer25, FakeReviewerFuture])
def test_show_answer_works_on_both_eras(reviewer_cls):
    """The full lookup chain we use in show_answer() works on both spellings."""
    rv = reviewer_cls()
    _invoke_first(rv, "_showAnswer", "show_answer")
    assert len(rv.calls) == 1
    assert rv.calls[0][1] == ()


@pytest.mark.parametrize("reviewer_cls", [FakeReviewer25, FakeReviewerFuture])
def test_answer_card_works_on_both_eras(reviewer_cls):
    rv = reviewer_cls()
    _invoke_first(rv, "_answerCard", "_answer_card", args=(2,))
    assert len(rv.calls) == 1
    assert rv.calls[0][1] == (2,)


@pytest.mark.parametrize("reviewer_cls", [FakeReviewer25, FakeReviewerFuture])
def test_replay_audio_works_on_both_eras(reviewer_cls):
    rv = reviewer_cls()
    _invoke_first(rv, "replayAudio", "replay_audio")
    assert len(rv.calls) == 1
