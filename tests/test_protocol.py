import json

import pytest

from flashcard_guru_remote.protocol import (
    Event,
    ProtocolError,
    error_response,
    ok_response,
    parse_request,
)


def test_parse_request_minimal():
    req = parse_request('{"id":"1","method":"ping"}')
    assert req.id == "1"
    assert req.method == "ping"
    assert req.params == {}


def test_parse_request_with_params():
    req = parse_request(
        '{"id":"abc","method":"review.answerCard","params":{"ease":3}}'
    )
    assert req.method == "review.answerCard"
    assert req.params == {"ease": 3}


def test_parse_request_invalid_json():
    with pytest.raises(ProtocolError):
        parse_request("not json at all")


def test_parse_request_must_be_object():
    with pytest.raises(ProtocolError):
        parse_request('["array","not","object"]')


def test_parse_request_missing_id():
    with pytest.raises(ProtocolError):
        parse_request('{"method":"ping"}')


def test_parse_request_empty_id():
    with pytest.raises(ProtocolError):
        parse_request('{"id":"","method":"ping"}')


def test_parse_request_missing_method():
    with pytest.raises(ProtocolError):
        parse_request('{"id":"1"}')


def test_parse_request_non_object_params():
    with pytest.raises(ProtocolError):
        parse_request('{"id":"1","method":"ping","params":[1,2,3]}')


def test_ok_response_default_empty_result():
    raw = ok_response("abc").to_json()
    assert json.loads(raw) == {"id": "abc", "result": {}}


def test_ok_response_with_result():
    raw = ok_response("abc", {"phase": "answer"}).to_json()
    assert json.loads(raw) == {"id": "abc", "result": {"phase": "answer"}}


def test_error_response_shape():
    raw = error_response("xyz", "invalid_ease", "must be 1-4").to_json()
    assert json.loads(raw) == {
        "id": "xyz",
        "error": {"code": "invalid_ease", "message": "must be 1-4"},
    }


def test_event_shape():
    raw = Event(event="state.changed", payload={"phase": "question"}).to_json()
    assert json.loads(raw) == {
        "event": "state.changed",
        "payload": {"phase": "question"},
    }


def test_response_unicode_preserved():
    raw = ok_response("u", {"deck": "中文牌组"}).to_json()
    data = json.loads(raw)
    assert data["result"]["deck"] == "中文牌组"
