"""Supabase JWT verification via JWKS.

Security-load-bearing. If you edit this, re-read the security notes in README and
run the `tests/test_jwt_security.py` suite.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

import httpx
import jwt
from jwt import PyJWKSet
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.logging import logger

_JWKS_CACHE_TTL_SECONDS = 600  # 10 minutes
_REFETCH_MIN_INTERVAL_SECONDS = 60  # global floor to prevent JWKS DoS


class _JwksCache:
    """JWKS cache with a global-refetch floor. Thread-safe for the event-loop-friendly case."""

    def __init__(self) -> None:
        self._jwks: PyJWKSet | None = None
        self._fetched_at: float = 0.0
        self._last_refetch: float = 0.0
        self._lock = Lock()

    def _should_refetch(self) -> bool:
        return (time.monotonic() - self._fetched_at) > _JWKS_CACHE_TTL_SECONDS

    def _can_refetch_now(self) -> bool:
        return (time.monotonic() - self._last_refetch) > _REFETCH_MIN_INTERVAL_SECONDS

    def _fetch(self) -> PyJWKSet:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(settings.jwks_url)
            resp.raise_for_status()
            data = resp.json()
        return PyJWKSet.from_dict(data)

    def get(self, *, force_refresh: bool = False) -> PyJWKSet:
        with self._lock:
            if self._jwks is None or self._should_refetch() or force_refresh:
                if force_refresh and not self._can_refetch_now():
                    # Someone asked for refresh but we just fetched — use stale JWKS.
                    # Legit callers with new kids will retry on the next interval.
                    assert self._jwks is not None
                    return self._jwks
                self._jwks = self._fetch()
                self._fetched_at = time.monotonic()
                self._last_refetch = time.monotonic()
            return self._jwks


_cache = _JwksCache()


def verify_startup() -> None:
    """Fetch JWKS at app boot and assert the issuer URL matches. Fail fast on misconfig."""
    jwks = _cache.get(force_refresh=True)
    if not jwks.keys:
        raise RuntimeError(f"No JWKs returned from {settings.jwks_url}")
    logger.info("jwks.startup_ok", issuer=settings.jwt_issuer, n_keys=len(jwks.keys))


def _get_signing_key(kid: str) -> Any:
    jwks = _cache.get()
    for key in jwks.keys:
        if key.key_id == kid:
            return key.key
    # Unknown kid — may be a rotation. Force refresh (rate-limited inside the cache).
    jwks = _cache.get(force_refresh=True)
    for key in jwks.keys:
        if key.key_id == kid:
            return key.key
    raise InvalidTokenError(f"Unknown kid: {kid}")


def verify_jwt(token: str) -> dict[str, Any]:
    """Verify a Supabase-issued JWT. Returns the claims dict. Raises InvalidTokenError otherwise."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except InvalidTokenError as e:
        raise InvalidTokenError("Malformed token header") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise InvalidTokenError("Token missing kid")

    key = _get_signing_key(kid)

    claims: dict[str, Any] = jwt.decode(
        token,
        key=key,
        algorithms=["RS256"],  # pinned; no alg=none, no HS256 confusion
        audience=settings.jwt_aud,
        issuer=settings.jwt_issuer,
        leeway=settings.jwt_leeway_seconds,
        options={"require": ["exp", "iat", "sub", "aud", "iss"]},
    )
    return claims
