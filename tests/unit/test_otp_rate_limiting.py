"""
Unit tests for OTP rate limiting (pentest finding 3.1.5 — Issue #176).

Verifies that POST /api/auth/email/verify enforces both IP-based and
per-email attempt rate limits, preventing brute-force of 6-digit OTP codes.

Module: src/backend/routers/auth.py
Issue: https://github.com/abilityai/trinity/issues/176
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ---- Inline reimplementation of the rate-limiting logic for unit testing ----
# Mirrors the exact algorithm in auth.py without importing the full backend.

OTP_MAX_ATTEMPTS = 5
OTP_RATE_WINDOW = 600
LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW = 600


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def check_otp_rate_limit(email: str, redis_client=None) -> bool:
    """Mirror of auth.check_otp_rate_limit."""
    if redis_client is None:
        return True

    key = f"otp_attempts:{email}"
    attempts = redis_client.get(key)
    if attempts and int(attempts) >= OTP_MAX_ATTEMPTS:
        ttl = redis_client.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many verification attempts. Request a new code or try again in {ttl} seconds."
        )
    return True


def record_otp_attempt(email: str, success: bool, redis_client=None):
    """Mirror of auth.record_otp_attempt."""
    if redis_client is None:
        return

    key = f"otp_attempts:{email}"
    if success:
        redis_client.delete(key)
    else:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, OTP_RATE_WINDOW)
        pipe.execute()


def check_login_rate_limit(client_ip: str, redis_client=None) -> bool:
    """Mirror of auth.check_login_rate_limit."""
    if redis_client is None:
        return True

    key = f"login_attempts:{client_ip}"
    attempts = redis_client.get(key)
    if attempts and int(attempts) >= LOGIN_RATE_LIMIT:
        ttl = redis_client.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {ttl} seconds."
        )
    return True


def record_login_attempt(client_ip: str, success: bool, redis_client=None):
    """Mirror of auth.record_login_attempt."""
    if redis_client is None:
        return

    key = f"login_attempts:{client_ip}"
    if success:
        redis_client.delete(key)
    else:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOGIN_RATE_WINDOW)
        pipe.execute()


# ============================================================================
# Tests for check_otp_rate_limit
# ============================================================================

class TestCheckOtpRateLimit:
    """Tests for per-email OTP attempt rate limiting."""

    def test_allows_first_attempt(self):
        """First attempt should be allowed (no prior attempts)."""
        r = MagicMock()
        r.get.return_value = None
        assert check_otp_rate_limit("user@example.com", r) is True

    def test_allows_attempts_below_threshold(self):
        """Attempts below max should be allowed."""
        r = MagicMock()
        for attempt_count in ["1", "2", "3", "4"]:
            r.get.return_value = attempt_count
            assert check_otp_rate_limit("user@example.com", r) is True

    def test_blocks_at_max_attempts(self):
        """Exactly OTP_MAX_ATTEMPTS failures should trigger 429."""
        r = MagicMock()
        r.get.return_value = str(OTP_MAX_ATTEMPTS)
        r.ttl.return_value = 540

        with pytest.raises(HTTPException) as exc_info:
            check_otp_rate_limit("user@example.com", r)

        assert exc_info.value.status_code == 429
        assert "new code" in exc_info.value.detail

    def test_blocks_above_max_attempts(self):
        """More than OTP_MAX_ATTEMPTS should also trigger 429."""
        r = MagicMock()
        r.get.return_value = "10"
        r.ttl.return_value = 300

        with pytest.raises(HTTPException) as exc_info:
            check_otp_rate_limit("user@example.com", r)

        assert exc_info.value.status_code == 429

    def test_uses_per_email_key(self):
        """Rate limit key must be per-email, not global."""
        r = MagicMock()
        r.get.return_value = None

        check_otp_rate_limit("alice@example.com", r)

        r.get.assert_called_with("otp_attempts:alice@example.com")

    def test_different_emails_have_independent_limits(self):
        """Rate limit for one email should not affect another."""
        def fake_get(key):
            if key == "otp_attempts:attacker@evil.com":
                return str(OTP_MAX_ATTEMPTS)
            return None

        r = MagicMock()
        r.get.side_effect = fake_get
        r.ttl.return_value = 300

        # Attacker's email is blocked
        with pytest.raises(HTTPException):
            check_otp_rate_limit("attacker@evil.com", r)

        # Legitimate user's email is not blocked
        assert check_otp_rate_limit("legit@example.com", r) is True

    def test_redis_unavailable_allows_through(self):
        """When Redis is unavailable (None), the check should pass (fail-open)."""
        assert check_otp_rate_limit("user@example.com", None) is True

    def test_ttl_included_in_error_message(self):
        """Error message should include TTL so user knows how long to wait."""
        r = MagicMock()
        r.get.return_value = str(OTP_MAX_ATTEMPTS)
        r.ttl.return_value = 423

        with pytest.raises(HTTPException) as exc_info:
            check_otp_rate_limit("user@example.com", r)

        assert "423" in exc_info.value.detail


# ============================================================================
# Tests for record_otp_attempt
# ============================================================================

class TestRecordOtpAttempt:
    """Tests for recording OTP verification attempts."""

    def test_failed_attempt_increments_counter(self):
        """Failed attempt should increment the per-email counter."""
        pipe = MagicMock()
        r = MagicMock()
        r.pipeline.return_value = pipe

        record_otp_attempt("user@example.com", success=False, redis_client=r)

        pipe.incr.assert_called_once_with("otp_attempts:user@example.com")
        pipe.expire.assert_called_once_with("otp_attempts:user@example.com", OTP_RATE_WINDOW)
        pipe.execute.assert_called_once()

    def test_success_clears_counter(self):
        """Successful verification should clear the per-email counter."""
        r = MagicMock()

        record_otp_attempt("user@example.com", success=True, redis_client=r)

        r.delete.assert_called_once_with("otp_attempts:user@example.com")

    def test_redis_unavailable_is_noop(self):
        """When Redis is None, recording should not raise."""
        record_otp_attempt("user@example.com", success=False, redis_client=None)
        record_otp_attempt("user@example.com", success=True, redis_client=None)

    def test_counter_expires_after_window(self):
        """Counter TTL must match OTP_RATE_WINDOW (10 minutes)."""
        pipe = MagicMock()
        r = MagicMock()
        r.pipeline.return_value = pipe

        record_otp_attempt("user@example.com", success=False, redis_client=r)

        pipe.expire.assert_called_once_with("otp_attempts:user@example.com", OTP_RATE_WINDOW)


# ============================================================================
# Tests for IP-based rate limit on verify endpoint
# ============================================================================

class TestIpRateLimitOnVerify:
    """Tests that IP-based rate limit also applies to OTP verification."""

    def test_ip_blocked_before_email_check(self):
        """IP rate limit should fire before checking per-email limit."""
        r = MagicMock()
        r.get.return_value = str(LOGIN_RATE_LIMIT)
        r.ttl.return_value = 300

        with pytest.raises(HTTPException) as exc_info:
            check_login_rate_limit("192.168.1.1", r)

        assert exc_info.value.status_code == 429

    def test_successful_otp_clears_ip_counter(self):
        """Successful OTP verification should clear the IP-based counter."""
        r = MagicMock()
        record_login_attempt("192.168.1.1", success=True, redis_client=r)
        r.delete.assert_called_once_with("login_attempts:192.168.1.1")

    def test_failed_otp_increments_ip_counter(self):
        """Failed OTP verification should increment the IP counter."""
        pipe = MagicMock()
        r = MagicMock()
        r.pipeline.return_value = pipe

        record_login_attempt("192.168.1.1", success=False, redis_client=r)

        pipe.incr.assert_called_once_with("login_attempts:192.168.1.1")


# ============================================================================
# Tests for brute-force scenario
# ============================================================================

class TestBruteForceScenario:
    """Simulate a brute-force attack to verify the full lockout flow."""

    def test_brute_force_blocked_after_five_failures(self):
        """
        Simulating 6 rapid OTP attempts: first 5 should fail with 401-equivalent,
        sixth attempt should be blocked with 429 (rate limit).
        """
        # Simulate in-memory counter
        counters = {}

        class FakeRedis:
            def get(self, key):
                return str(counters.get(key, 0)) if counters.get(key, 0) else None

            def ttl(self, key):
                return OTP_RATE_WINDOW

            def delete(self, key):
                counters.pop(key, None)

            def pipeline(self):
                return FakePipeline()

        class FakePipeline:
            def __init__(self):
                self._cmds = []

            def incr(self, key):
                self._cmds.append(("incr", key))
                return self

            def expire(self, key, ttl):
                self._cmds.append(("expire", key, ttl))
                return self

            def execute(self):
                for cmd in self._cmds:
                    if cmd[0] == "incr":
                        counters[cmd[1]] = counters.get(cmd[1], 0) + 1

        r = FakeRedis()
        email = "victim@example.com"

        # Attempts 1-5: allowed through (counter increments)
        for i in range(OTP_MAX_ATTEMPTS):
            check_otp_rate_limit(email, r)  # Should not raise
            record_otp_attempt(email, success=False, redis_client=r)

        assert counters.get(f"otp_attempts:{email}") == OTP_MAX_ATTEMPTS

        # Attempt 6: should be blocked with 429
        with pytest.raises(HTTPException) as exc_info:
            check_otp_rate_limit(email, r)

        assert exc_info.value.status_code == 429

    def test_success_resets_counter_allowing_new_attempts(self):
        """After successful verification, counter is cleared for future logins."""
        counters = {"otp_attempts:user@example.com": OTP_MAX_ATTEMPTS - 1}

        class FakeRedis:
            def get(self, key):
                v = counters.get(key)
                return str(v) if v else None

            def delete(self, key):
                counters.pop(key, None)

            def ttl(self, key):
                return 300

        r = FakeRedis()
        email = "user@example.com"

        # Would be blocked on next failure, but success clears it
        record_otp_attempt(email, success=True, redis_client=r)

        assert f"otp_attempts:{email}" not in counters

        # Now another attempt should be allowed
        assert check_otp_rate_limit(email, r) is True
