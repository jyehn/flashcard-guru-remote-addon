from flashcard_guru_remote.auth import (
    FailureTracker,
    constant_time_equals,
    generate_token,
)


def test_generate_token_length():
    token = generate_token()
    assert len(token) == 32  # 16 bytes hex


def test_generate_token_uniqueness():
    tokens = {generate_token() for _ in range(100)}
    assert len(tokens) == 100


def test_constant_time_equals():
    assert constant_time_equals("abc", "abc") is True
    assert constant_time_equals("abc", "abd") is False
    assert constant_time_equals("abc", "abcd") is False
    assert constant_time_equals("", "") is True


def test_failure_tracker_under_limit():
    tracker = FailureTracker(max_failures=3, window_seconds=60)
    tracker.record_failure("1.2.3.4")
    tracker.record_failure("1.2.3.4")
    assert tracker.is_banned("1.2.3.4") is False


def test_failure_tracker_at_limit():
    tracker = FailureTracker(max_failures=3, window_seconds=60)
    for _ in range(3):
        tracker.record_failure("1.2.3.4")
    assert tracker.is_banned("1.2.3.4") is True


def test_failure_tracker_per_remote_isolation():
    tracker = FailureTracker(max_failures=2, window_seconds=60)
    tracker.record_failure("1.1.1.1")
    tracker.record_failure("1.1.1.1")
    assert tracker.is_banned("1.1.1.1") is True
    assert tracker.is_banned("2.2.2.2") is False


def test_failure_tracker_reset_clears_ban():
    tracker = FailureTracker(max_failures=2, window_seconds=60)
    tracker.record_failure("host")
    tracker.record_failure("host")
    assert tracker.is_banned("host") is True
    tracker.reset("host")
    assert tracker.is_banned("host") is False
