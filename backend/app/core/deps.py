"""FastAPI dependencies.

ONLY `get_db_with_claims` and `get_db_service_role` are exposed. The former is
what every normal route uses; the latter is reserved for admin paths marked
with `@allow_service_role`. A CI test introspects the route graph and fails if
any endpoint's dependency chain does not include one of them.

There is deliberately no `get_db` — that was the round-2 foot-gun. If you feel
like you need it, you need `get_db_with_claims`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import _get_session_service_role, _get_session_with_claims
from app.core.jwt import verify_jwt

_bearer = HTTPBearer(auto_error=True)


ALLOW_SERVICE_ROLE_ATTR = "__allow_service_role__"


def allow_service_role(func: Any) -> Any:
    """Marker decorator for endpoints that use `get_db_service_role`.

    The CI dependency-graph test rejects any endpoint using the service-role
    session without this marker. Writing the marker forces the PR reviewer to
    justify the RLS bypass.
    """
    setattr(func, ALLOW_SERVICE_ROLE_ATTR, True)
    return func


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """Verify the `Authorization: Bearer <jwt>` header and return the claims."""
    try:
        claims = verify_jwt(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return claims


async def get_db_with_claims(
    claims: Annotated[dict[str, Any], Depends(get_current_user)],
) -> AsyncGenerator[AsyncSession, None]:
    """The ONLY DB dependency normal routes should use.

    Opens a transaction-scoped session with `SET LOCAL role authenticated` and
    `SET LOCAL request.jwt.claims` so that RLS policies evaluate correctly.
    """
    async for session in _get_session_with_claims(claims):
        yield session


async def get_db_service_role(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Admin-only session that bypasses RLS. Endpoint must be `@allow_service_role`.

    Enforced in two places:
    1. CI test introspects route graph and fails on unmarked usage.
    2. Runtime check (below) hard-fails requests to an endpoint without the marker.
    """
    endpoint = request.scope.get("endpoint")
    if endpoint is None or not getattr(endpoint, ALLOW_SERVICE_ROLE_ATTR, False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service-role session used by an endpoint not marked @allow_service_role",
        )
    async for session in _get_session_service_role():
        yield session


# Convenience aliases
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db_with_claims)]
ServiceRoleDbSession = Annotated[AsyncSession, Depends(get_db_service_role)]
