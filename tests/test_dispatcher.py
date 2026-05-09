from typing import Any

import pytest

from flashcard_guru_remote.dispatcher import DispatchError, Dispatcher


class FakeBridge:
    def __init__(self):
        self.in_review = True
        self.last_ease: int | None = None
        self.replay_calls = 0
        self.undo_calls = 0
        self.show_answer_calls = 0

    def is_in_review(self) -> bool:
        return self.in_review

    def show_answer(self) -> dict[str, Any]:
        self.show_answer_calls += 1
        return {"phase": "answer"}

    def answer_card(self, ease: int) -> dict[str, Any]:
        self.last_ease = ease
        return {"phase": "question", "next_card": {"id": 1}}

    def replay_audio(self) -> None:
        self.replay_calls += 1

    def undo(self) -> dict[str, Any]:
        self.undo_calls += 1
        return {"phase": "answer"}

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "phase": "question" if self.in_review else "no-card",
            "deck": "Test",
            "queues": {"new": 1, "learning": 0, "review": 0},
            "card": {"id": 1, "due": 0},
        }


@pytest.fixture
def bridge() -> FakeBridge:
    return FakeBridge()


@pytest.fixture
def dispatcher(bridge: FakeBridge) -> Dispatcher:
    return Dispatcher(bridge)


def test_show_answer_passes_through(bridge, dispatcher):
    out = dispatcher.dispatch("review.showAnswer", {})
    assert out == {"phase": "answer"}
    assert bridge.show_answer_calls == 1


def test_answer_card_with_valid_ease(bridge, dispatcher):
    out = dispatcher.dispatch("review.answerCard", {"ease": 3})
    assert bridge.last_ease == 3
    assert out["phase"] == "question"


@pytest.mark.parametrize("bad", [0, 5, -1, "good", None, 1.5, True, False])
def test_answer_card_rejects_invalid_ease(dispatcher, bad):
    with pytest.raises(DispatchError) as exc:
        dispatcher.dispatch("review.answerCard", {"ease": bad})
    assert exc.value.code == "invalid_ease"


def test_show_answer_blocked_outside_review(bridge, dispatcher):
    bridge.in_review = False
    with pytest.raises(DispatchError) as exc:
        dispatcher.dispatch("review.showAnswer", {})
    assert exc.value.code == "not_in_review"


def test_answer_card_blocked_outside_review(bridge, dispatcher):
    bridge.in_review = False
    with pytest.raises(DispatchError) as exc:
        dispatcher.dispatch("review.answerCard", {"ease": 3})
    assert exc.value.code == "not_in_review"


def test_replay_audio_blocked_outside_review(bridge, dispatcher):
    bridge.in_review = False
    with pytest.raises(DispatchError) as exc:
        dispatcher.dispatch("review.replayAudio", {})
    assert exc.value.code == "not_in_review"


def test_replay_audio_returns_empty(bridge, dispatcher):
    out = dispatcher.dispatch("review.replayAudio", {})
    assert out == {}
    assert bridge.replay_calls == 1


def test_undo_works_outside_review(bridge, dispatcher):
    bridge.in_review = False
    out = dispatcher.dispatch("review.undo", {})
    assert bridge.undo_calls == 1
    assert out == {"phase": "answer"}


def test_state_get_works_outside_review(bridge, dispatcher):
    bridge.in_review = False
    out = dispatcher.dispatch("state.get", {})
    assert out["phase"] == "no-card"
    assert out["deck"] == "Test"


def test_unknown_method_rejected(dispatcher):
    with pytest.raises(DispatchError) as exc:
        dispatcher.dispatch("review.nope", {})
    assert exc.value.code == "unknown_method"


def test_ping(dispatcher):
    out = dispatcher.dispatch("ping", {})
    assert "pong" in out
    assert isinstance(out["pong"], float)
