"""Researcher authentication and participant token handling.

Two separate access paths, by design:

- **Researcher routes** require a bearer token. If no token is configured, the
  API refuses non-local requests rather than silently running open — a research
  tool holding API keys and participant data should not be reachable from the
  network by accident.
- **Participant routes** are authenticated only by an unguessable study token.
  That token grants exactly one thing: taking the assessment. It can never
  reach researcher controls, because those routes have a different dependency.
"""

from __future__ import annotations

import ipaddress
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "testclient"}


def new_study_token() -> str:
    """URL-safe, unguessable participant link token."""
    return secrets.token_urlsafe(24)


def _is_local(request: Request) -> bool:
    client = request.client
    if client is None:
        return True  # ASGI test transport
    host = client.host
    if host in _LOCAL_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_researcher(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> str:
    """Dependency guarding every researcher route."""
    if settings.auth_enabled:
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Researcher token required. Send 'Authorization: Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Constant-time comparison: this token also gates spend.
        if not secrets.compare_digest(
            credentials.credentials, settings.researcher_api_token
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid researcher token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return "researcher"

    # No token configured: permit local use only.
    if _is_local(request) and settings.explab_allow_insecure_local:
        return "local-researcher"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "No RESEARCHER_API_TOKEN is configured, so this API only accepts local "
            "requests. Set RESEARCHER_API_TOKEN in .env to allow remote access."
        ),
    )
