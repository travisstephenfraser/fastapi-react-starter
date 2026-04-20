"""CRITICAL test: every DB-touching endpoint must use `get_db_with_claims` OR be
explicitly marked `@allow_service_role`. If this test fails, a new route is
silently bypassing RLS.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.core.deps import (
    ALLOW_SERVICE_ROLE_ATTR,
    get_db_service_role,
    get_db_with_claims,
)
from app.main import app


def _dependency_names(route: APIRoute) -> set[str]:
    """Walk the endpoint's dependency tree and collect callable names.

    Functions expose `__name__`; callable class instances (e.g. `HTTPBearer()`
    from fastapi.security) don't, so fall back to the type's name.
    """
    names: set[str] = set()
    stack = [route.dependant]
    while stack:
        dep = stack.pop()
        if dep.call is not None:
            name = getattr(dep.call, "__name__", None) or type(dep.call).__name__
            names.add(name)
        stack.extend(dep.dependencies)
    return names


def test_every_db_route_uses_claimed_session() -> None:
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        deps = _dependency_names(route)
        touches_db = get_db_with_claims.__name__ in deps or get_db_service_role.__name__ in deps
        if not touches_db:
            continue
        uses_service_role = get_db_service_role.__name__ in deps
        if uses_service_role:
            if not getattr(route.endpoint, ALLOW_SERVICE_ROLE_ATTR, False):
                offenders.append(
                    f"{route.path} uses service-role session without @allow_service_role"
                )
    assert not offenders, "\n".join(offenders)


def test_no_public_get_db_export() -> None:
    """`get_db` was the round-2 foot-gun. It must not exist on `core.deps`."""
    from app.core import deps

    assert not hasattr(deps, "get_db"), (
        "`get_db` reintroduced — that was the whole point of deleting it. "
        "Use `get_db_with_claims` or `get_db_service_role`."
    )
