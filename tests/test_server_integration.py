"""End-to-end test: spin up a real RemoteServer on a free port and exercise
the full hello → request → response loop with a websockets client.

Skipped when websockets isn't available (e.g., CI without dev deps).
"""
from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

import pytest

websockets = pytest.importorskip("websockets")
from websockets.asyncio.client import connect  # type: ignore  # noqa: E402

from flashcard_guru_remote.config import RemoteConfig  # noqa: E402
from flashcard_guru_remote.dispatcher import Dispatcher  # noqa: E402
from flashcard_guru_remote.protocol import Event  # noqa: E402
from flashcard_guru_remote.server import RemoteServer  # noqa: E402


class FakeBridge:
    def __init__(self):
        self.in_review = True
        self.last_ease: int | None = None
        self.replays = 0
        self.undos = 0

    def is_in_review(self) -> bool:
        return self.in_review

    def show_answer(self) -> dict[str, Any]:
        return {"phase": "answer"}

    def answer_card(self, ease: int) -> dict[str, Any]:
        self.last_ease = ease
        return {"phase": "question", "next_card": {"id": 7}}

    def replay_audio(self) -> None:
        self.replays += 1

    def undo(self) -> dict[str, Any]:
        self.undos += 1
        return {"phase": "answer"}

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "phase": "question",
            "deck": "TestDeck",
            "queues": {"new": 1, "learning": 0, "review": 2},
            "card": {"id": 7, "due": 0},
        }


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


@pytest.fixture
def running_server():
    """Start a server on loopback with a known token; tear down after test."""
    port = _free_port()
    config = RemoteConfig(port=port)
    config.add_device(token="test-token", device_name="Test Phone")

    bridge = FakeBridge()
    dispatcher = Dispatcher(bridge)
    server = RemoteServer(
        config=config,
        dispatcher=dispatcher,
        host="127.0.0.1",
        host_name="test-host",
    )
    server.start()
    assert server.bind_error is None, f"bind error: {server.bind_error}"

    try:
        yield server, bridge, port
    finally:
        server.stop()


async def _hello(ws, token="test-token") -> dict:
    await ws.send(
        json.dumps(
            {
                "id": "hello-1",
                "method": "hello",
                "params": {"token": token, "device_name": "Pytest iPhone"},
            }
        )
    )
    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
    return json.loads(raw)


async def _request(ws, method: str, params: dict | None = None, req_id: str = "r-1") -> dict:
    await ws.send(
        json.dumps(
            {"id": req_id, "method": method, "params": params or {}}
        )
    )
    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
    return json.loads(raw)


@pytest.mark.asyncio
async def test_hello_succeeds_with_valid_token(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        resp = await _hello(ws)
        assert resp["id"] == "hello-1"
        assert resp["result"]["ok"] is True
        assert resp["result"]["server_version"] == "0.1.0"
        assert resp["result"]["host_name"] == "test-host"


@pytest.mark.asyncio
async def test_hello_rejects_invalid_token(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        resp = await _hello(ws, token="wrong")
        assert resp["error"]["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_request_before_hello_is_rejected(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await ws.send(json.dumps({"id": "r", "method": "ping"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        resp = json.loads(raw)
        assert resp["error"]["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_full_review_round_trip(running_server):
    _, bridge, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)

        show = await _request(ws, "review.showAnswer")
        assert show["result"]["phase"] == "answer"

        ans = await _request(ws, "review.answerCard", {"ease": 3}, req_id="r-2")
        assert ans["result"]["phase"] == "question"
        assert bridge.last_ease == 3

        replay = await _request(ws, "review.replayAudio", req_id="r-3")
        assert replay["result"] == {}
        assert bridge.replays == 1

        undo = await _request(ws, "review.undo", req_id="r-4")
        assert undo["result"]["phase"] == "answer"
        assert bridge.undos == 1


@pytest.mark.asyncio
async def test_invalid_ease_returns_error(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)
        resp = await _request(ws, "review.answerCard", {"ease": 99}, req_id="bad")
        assert resp["error"]["code"] == "invalid_ease"


@pytest.mark.asyncio
async def test_not_in_review_blocks_show_answer(running_server):
    server, bridge, port = running_server
    bridge.in_review = False
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)
        resp = await _request(ws, "review.showAnswer")
        assert resp["error"]["code"] == "not_in_review"


@pytest.mark.asyncio
async def test_state_get_returns_snapshot(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)
        resp = await _request(ws, "state.get")
        assert resp["result"]["deck"] == "TestDeck"
        assert resp["result"]["queues"]["new"] == 1


@pytest.mark.asyncio
async def test_unknown_method_returns_error(running_server):
    _, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)
        resp = await _request(ws, "review.flyToMars")
        assert resp["error"]["code"] == "unknown_method"


@pytest.mark.asyncio
async def test_broadcast_event_reaches_client(running_server):
    server, _, port = running_server
    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws)

        # Server pushes an event from its asyncio loop
        server.broadcast(Event(event="state.changed", payload={"phase": "answer"}))

        # Drain pushes; the event arrives without a request
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["event"] == "state.changed"
        assert msg["payload"]["phase"] == "answer"


@pytest.mark.asyncio
async def test_on_device_paired_callback_fires(running_server):
    server, _, port = running_server
    paired_devices: list = []
    server.on_device_paired = paired_devices.append

    async with connect(f"ws://127.0.0.1:{port}") as ws:
        resp = await _hello(ws)
        assert resp["result"]["ok"] is True

    # Give the server's event loop a tick to deliver the callback (it runs
    # synchronously inside _authenticate, so by the time hello returns the
    # callback has already fired).
    await asyncio.sleep(0.05)

    assert len(paired_devices) == 1
    assert paired_devices[0].token == "test-token"
    assert paired_devices[0].device_name == "Pytest iPhone"


@pytest.mark.asyncio
async def test_on_device_paired_not_called_on_auth_failure(running_server):
    server, _, port = running_server
    paired_devices: list = []
    server.on_device_paired = paired_devices.append

    async with connect(f"ws://127.0.0.1:{port}") as ws:
        await _hello(ws, token="wrong-token")

    await asyncio.sleep(0.05)
    assert paired_devices == []


@pytest.mark.asyncio
async def test_invalid_token_three_strikes_bans(running_server):
    _, _, port = running_server

    # Each connection fails auth → tracker records a failure.
    for _ in range(3):
        async with connect(f"ws://127.0.0.1:{port}") as ws:
            await _hello(ws, token="bad")

    # Fourth attempt should be closed before hello roundtrip completes.
    with pytest.raises(Exception):
        async with connect(f"ws://127.0.0.1:{port}") as ws:
            # The server closes immediately with code 4429; the client may
            # raise on close handshake. We just need _something_ to fail.
            await asyncio.wait_for(_hello(ws, token="bad"), timeout=2.0)
