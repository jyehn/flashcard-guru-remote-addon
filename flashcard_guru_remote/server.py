"""WebSocket server — owns the asyncio loop on a daemon thread.

Lifecycle:
  start()  — spawns daemon thread, blocks until server is listening (or fails)
  stop()   — signals shutdown, joins thread

Per-connection flow:
  1. Verify remote address is on a private LAN (reject otherwise)
  2. Verify remote isn't rate-limit banned
  3. Wait for hello frame within HELLO_TIMEOUT_S, validate token
  4. Loop on incoming frames, dispatch, reply
  5. On any disconnect / exception, drop the connection cleanly
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import threading
from typing import Any

from .auth import FailureTracker, constant_time_equals
from .config import RemoteConfig
from .dispatcher import DispatchError, Dispatcher
from .protocol import (
    Event,
    ProtocolError,
    Response,
    error_response,
    ok_response,
    parse_request,
)

log = logging.getLogger(__name__)

HELLO_TIMEOUT_S = 10.0
SERVER_VERSION = "0.1.0"


class RemoteServer:
    def __init__(
        self,
        config: RemoteConfig,
        dispatcher: Dispatcher,
        host: str = "0.0.0.0",
        host_name: str = "Mac",
    ):
        self._config = config
        self._dispatcher = dispatcher
        self._host = host
        self._host_name = host_name
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self._connections: set[Any] = set()
        self._failure_tracker = FailureTracker()
        self._lock = threading.Lock()
        self._bind_error: BaseException | None = None

    @property
    def port(self) -> int:
        return self._config.port

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def bind_error(self) -> BaseException | None:
        return self._bind_error

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="FlashcardGuruRemoteServer",
            args=(ready,),
            daemon=True,
        )
        self._thread.start()
        ready.wait(timeout=5.0)

    def stop(self) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._loop = None
        self._stop_event = None

    def _run(self, ready: threading.Event) -> None:
        try:
            import websockets  # noqa: F401  — vendored
        except ImportError as exc:
            log.error("websockets library missing: %s", exc)
            self._bind_error = exc
            ready.set()
            return

        from websockets.asyncio.server import serve  # type: ignore

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()

        async def main() -> None:
            try:
                async with serve(self._handle, self._host, self._config.port):
                    ready.set()
                    await self._stop_event.wait()
            except OSError as exc:
                log.error("failed to bind %s:%s — %s", self._host, self._config.port, exc)
                self._bind_error = exc
                ready.set()

        try:
            self._loop.run_until_complete(main())
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    async def _handle(self, ws) -> None:
        remote = self._remote_addr(ws)

        if not self._is_lan(remote):
            log.warning("rejecting non-LAN connection from %s", remote)
            await ws.close(code=4403, reason="non-LAN")
            return

        if self._failure_tracker.is_banned(remote):
            log.warning("rejecting rate-limited remote %s", remote)
            await ws.close(code=4429, reason="too many failures")
            return

        device = await self._authenticate(ws, remote)
        if device is None:
            return

        with self._lock:
            self._connections.add(ws)

        try:
            async for raw in ws:
                response = self._handle_request(raw)
                await ws.send(response.to_json())
        except Exception as exc:  # noqa: BLE001
            log.info("client %s disconnected: %s", remote, exc)
        finally:
            with self._lock:
                self._connections.discard(ws)

    async def _authenticate(self, ws, remote: str):
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=HELLO_TIMEOUT_S)
        except asyncio.TimeoutError:
            log.info("hello timeout from %s", remote)
            await ws.close(code=4408, reason="hello timeout")
            return None
        except Exception as exc:  # noqa: BLE001
            log.info("recv before hello failed: %s", exc)
            return None

        if not isinstance(raw, str):
            raw = raw.decode("utf-8", errors="replace")

        try:
            req = parse_request(raw)
        except ProtocolError as exc:
            await ws.send(
                error_response("init", "invalid_frame", str(exc)).to_json()
            )
            await ws.close(code=4400, reason="invalid frame")
            return None

        if req.method != "hello":
            await ws.send(
                error_response(
                    req.id, "auth_failed", "first message must be hello"
                ).to_json()
            )
            await ws.close(code=4401, reason="auth required")
            return None

        token = str(req.params.get("token", ""))
        device_name = str(req.params.get("device_name", "Unknown device"))

        device = self._find_device(token)
        if device is None:
            self._failure_tracker.record_failure(remote)
            await ws.send(
                error_response(req.id, "auth_failed", "invalid token").to_json()
            )
            await ws.close(code=4401, reason="auth failed")
            return None

        self._failure_tracker.reset(remote)
        device.device_name = device_name or device.device_name
        device.touch()
        self._config.save()

        await ws.send(
            ok_response(
                req.id,
                {
                    "ok": True,
                    "server_version": SERVER_VERSION,
                    "host_name": self._host_name,
                },
            ).to_json()
        )
        log.info("paired device connected: %s (%s)", device.device_name, remote)
        return device

    def _handle_request(self, raw: Any) -> Response:
        if not isinstance(raw, str):
            try:
                raw = raw.decode("utf-8")
            except Exception:
                return error_response("unknown", "invalid_frame", "non-text frame")

        try:
            req = parse_request(raw)
        except ProtocolError as exc:
            return error_response("unknown", "invalid_frame", str(exc))

        try:
            result = self._dispatcher.dispatch(req.method, req.params)
            return ok_response(req.id, result)
        except DispatchError as exc:
            return error_response(req.id, exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001
            log.exception("internal error handling %s", req.method)
            return error_response(req.id, "internal_error", str(exc))

    # ------------------------------------------------------------------
    # State broadcast
    # ------------------------------------------------------------------

    def broadcast(self, event: Event) -> None:
        """Push an event to every connected client. Safe from any thread."""
        if self._loop is None:
            return
        msg = event.to_json()

        async def _send_all() -> None:
            with self._lock:
                conns = list(self._connections)
            for ws in conns:
                try:
                    await ws.send(msg)
                except Exception:
                    pass

        try:
            asyncio.run_coroutine_threadsafe(_send_all(), self._loop)
        except RuntimeError:
            pass  # loop already closed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_device(self, token: str):
        if not token:
            return None
        for device in self._config.paired_devices:
            if constant_time_equals(device.token, token):
                return device
        return None

    @staticmethod
    def _remote_addr(ws) -> str:
        peer = getattr(ws, "remote_address", None)
        if peer:
            try:
                return str(peer[0])
            except Exception:
                return "unknown"
        return "unknown"

    @staticmethod
    def _is_lan(remote: str) -> bool:
        try:
            addr = ipaddress.ip_address(remote)
        except ValueError:
            return False
        return addr.is_private or addr.is_loopback or addr.is_link_local
