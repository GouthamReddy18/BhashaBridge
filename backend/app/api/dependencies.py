"""FastAPI dependency seam for optional application providers."""
from fastapi import Request

from app.services.translation import TranslationProvider


def get_translation_provider(request: Request) -> TranslationProvider | None:
    """Return an app-injected provider; the default application has none."""
    return getattr(request.app.state, "translation_provider", None)
