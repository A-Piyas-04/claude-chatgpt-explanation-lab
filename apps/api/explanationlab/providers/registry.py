"""Provider resolution.

Demo mode substitution is explicit and visible: when a provider has no
credentials we return a :class:`DemoProvider` that *announces itself* on every
result, rather than silently falling back to a different real model (which §10
of the brief forbids).
"""

from __future__ import annotations

from ..config import get_settings
from ..enums import Provider
from .anthropic_provider import AnthropicProvider
from .base import BaseProvider, ProviderError
from .demo import DemoProvider
from .openai_provider import OpenAIProvider

_CACHE: dict[str, BaseProvider] = {}


def provider_configured(provider: str) -> bool:
    settings = get_settings()
    if provider == Provider.OPENAI.value:
        return settings.has_openai
    if provider == Provider.ANTHROPIC.value:
        return settings.has_anthropic
    if provider == Provider.MANUAL.value:
        return True
    return False


def get_provider(provider: str, *, allow_demo: bool = True) -> BaseProvider:
    """Return an adapter for ``provider``.

    When credentials are absent and ``allow_demo`` is set, a demo adapter is
    returned that tags its output synthetic. With ``allow_demo=False`` the
    missing credential is raised instead — used by endpoints that must not
    fabricate data.
    """
    if provider_configured(provider) and provider != Provider.MANUAL.value:
        if provider not in _CACHE:
            _CACHE[provider] = (
                OpenAIProvider() if provider == Provider.OPENAI.value else AnthropicProvider()
            )
        return _CACHE[provider]

    if not allow_demo:
        raise ProviderError(
            f"Provider '{provider}' is not configured and demo substitution is disabled.",
            error_type="provider_not_configured",
        )

    key = f"demo::{provider}"
    if key not in _CACHE:
        _CACHE[key] = DemoProvider(emulating=provider)
    return _CACHE[key]


def provider_status() -> list[dict]:
    """Availability indicators for the UI."""
    settings = get_settings()
    return [
        {
            "provider": Provider.OPENAI.value,
            "configured": settings.has_openai,
            "mode": "live" if settings.has_openai else "demo",
        },
        {
            "provider": Provider.ANTHROPIC.value,
            "configured": settings.has_anthropic,
            "mode": "live" if settings.has_anthropic else "demo",
        },
    ]


def reset_cache() -> None:
    """Test hook; also used after a credential change."""
    _CACHE.clear()
