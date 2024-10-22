from unittest.mock import Mock

import pytest
from requests.exceptions import HTTPError

from nyx_client.utils import auth_retry, ensure_setup


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = f"Error {status_code}"


def TestHTTPError(status_code):
    """Create an HTTPError with a mock response."""
    response = MockResponse(status_code)
    return HTTPError(response=response)


class MockNyxClient:
    def __init__(self):
        self._is_setup = False
        self._authorise = Mock()
        self.setup_called = 0
        self.auth_called = 0
        self._attempt = 0  # Track which attempt we're on

    def _setup(self):
        self._is_setup = True
        self.setup_called += 1

    @ensure_setup
    def test_ensure_setup(self):
        return "success"

    @auth_retry
    def test_auth_retry(self, should_fail_first=False, should_fail_second=False, first_status=401, second_status=None):
        self.auth_called += 1

        if self._attempt == 0 and should_fail_first:
            self._attempt += 1
            raise TestHTTPError(first_status)
        elif self._attempt == 1 and should_fail_second:
            self._attempt += 1
            raise TestHTTPError(second_status or first_status)

        return "success"

    @ensure_setup
    @auth_retry
    def test_combined_decorators(self, should_fail=False, status_code=401):
        self.auth_called += 1
        if should_fail:
            raise TestHTTPError(status_code)
        return "success"


def test_ensure_setup_decorator():
    client = MockNyxClient()
    assert client._is_setup is False

    # First call should trigger setup
    result = client.test_ensure_setup()
    assert result == "success"
    assert client._is_setup is True
    assert client.setup_called == 1

    # Second call should not trigger setup
    result = client.test_ensure_setup()
    assert result == "success"
    assert client.setup_called == 1  # Setup count should not increase


@pytest.mark.parametrize(
    "test_case",
    [
        # (should_fail_first, should_fail_second, first_status, second_status, expected_auth_calls, should_raise)
        (True, False, 401, None, 2, False),  # Successful retry
        (True, True, 401, 401, 2, True),  # Failed retry
        (True, True, 401, 403, 2, True),  # Different error on retry
        (False, False, None, None, 1, False),  # No failure
        (True, False, 403, None, 1, True),  # Non-401 error
    ],
)
def test_auth_retry_decorator(test_case):
    should_fail_first, should_fail_second, first_status, second_status, expected_auth_calls, should_raise = test_case
    client = MockNyxClient()

    if should_raise:
        with pytest.raises(HTTPError):
            client.test_auth_retry(
                should_fail_first=should_fail_first,
                should_fail_second=should_fail_second,
                first_status=first_status,
                second_status=second_status,
            )
    else:
        result = client.test_auth_retry(
            should_fail_first=should_fail_first,
            should_fail_second=should_fail_second,
            first_status=first_status,
            second_status=second_status,
        )
        assert result == "success"

    # Verify number of auth calls
    if first_status == 401 and should_fail_first:
        client._authorise.assert_called_once_with(refresh=True)
    assert client.auth_called == expected_auth_calls


@pytest.mark.parametrize(
    "test_case",
    [
        # (setup_fails, auth_fails, auth_status, expected_setup_calls, expected_auth_calls, should_raise)
        (False, False, None, 1, 1, False),  # Everything succeeds
        (False, True, 401, 1, 2, True),  # Auth fails with 401
        (False, True, 403, 1, 1, True),  # Auth fails with non-401
        (True, False, None, 1, 0, True),  # Setup fails
    ],
)
def test_combined_decorators(test_case):
    setup_fails, auth_fails, auth_status, expected_setup_calls, expected_auth_calls, should_raise = test_case
    client = MockNyxClient()

    if setup_fails:
        client._setup = Mock(side_effect=Exception("Setup failed"))

    if should_raise:
        with pytest.raises((Exception, HTTPError)):
            client.test_combined_decorators(should_fail=auth_fails, status_code=auth_status)
    else:
        result = client.test_combined_decorators(should_fail=auth_fails, status_code=auth_status)
        assert result == "success"

    if not setup_fails:
        assert client.setup_called == expected_setup_calls
        assert client.auth_called <= expected_auth_calls


def test_ensure_setup_no_infinite_loop():
    client = MockNyxClient()
    setup_count = 0
    max_setups = 5  # Safety limit

    def mock_setup():
        nonlocal setup_count
        setup_count += 1
        if setup_count > max_setups:
            pytest.fail("Potential infinite loop detected")
        # Always fail setup
        raise TestHTTPError(401)

    client._setup = mock_setup

    with pytest.raises(HTTPError):
        client.test_ensure_setup()

    assert setup_count == 1, "Setup should only be called once even on failure"


class MockNyxClientWithSequence(MockNyxClient):
    def __init__(self, error_sequence):
        super().__init__()
        self.error_sequence = error_sequence
        self.call_count = 0

    @auth_retry
    def test_sequence(self):
        if self.call_count >= len(self.error_sequence):
            return "success"

        status_code, should_fail = self.error_sequence[self.call_count]
        self.call_count += 1

        if should_fail:
            raise TestHTTPError(status_code)
        return "success"


@pytest.mark.parametrize(
    "error_sequence",
    [
        [(401, True), (401, True), (401, True)],  # Multiple 401s
        [(401, True), (403, True)],  # 401 then different error
        [(401, True), (401, False)],  # 401 then success
        [(500, True), (401, True)],  # Different error then 401
    ],
)
def test_auth_retry_error_sequences(error_sequence):
    client = MockNyxClientWithSequence(error_sequence)

    if any(code != 401 for code, _ in error_sequence):
        # Should fail on non-401 errors
        with pytest.raises(HTTPError):
            client.test_sequence()
    elif all(fail for _, fail in error_sequence):
        # Should fail after retry on continuous 401s
        with pytest.raises(HTTPError):
            client.test_sequence()
    else:
        # Should eventually succeed
        result = client.test_sequence()
        assert result == "success"

    # Verify we didn't make too many calls
    assert client.call_count <= len(error_sequence)
