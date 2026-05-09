"""Wire protocol — JSON frame encoding for the iOS ⇄ Anki bridge.

Three frame types:

  Request (client → server):
    {"id": "<uuid>", "method": "<name>", "params": {...}}

  Response (server → client, paired by id):
    {"id": "<uuid>", "result": {...}}                     # success
    {"id": "<uuid>", "error": {"code": "...", "message": "..."}}

  Event (server → client, no id):
    {"event": "<name>", "payload": {...}}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class ProtocolError(Exception):
    """Raised when an incoming frame is malformed."""


@dataclass
class Request:
    id: str
    method: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    id: str
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None

    def to_json(self) -> str:
        body: dict[str, Any] = {"id": self.id}
        if self.error is not None:
            body["error"] = self.error
        else:
            body["result"] = self.result if self.result is not None else {}
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


@dataclass
class Event:
    event: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {"event": self.event, "payload": self.payload},
            ensure_ascii=False,
            separators=(",", ":"),
        )


def parse_request(raw: str) -> Request:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProtocolError("frame must be a JSON object")

    msg_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    if not isinstance(msg_id, str) or not msg_id:
        raise ProtocolError("missing or invalid id")
    if not isinstance(method, str) or not method:
        raise ProtocolError("missing or invalid method")
    if not isinstance(params, dict):
        raise ProtocolError("params must be a JSON object")

    return Request(id=msg_id, method=method, params=params)


def ok_response(req_id: str, result: dict[str, Any] | None = None) -> Response:
    return Response(id=req_id, result=result if result is not None else {})


def error_response(req_id: str, code: str, message: str) -> Response:
    return Response(id=req_id, error={"code": code, "message": message})
