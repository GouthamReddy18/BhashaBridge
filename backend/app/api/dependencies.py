"""FastAPI dependency seam for optional application providers."""
from fastapi import Request

from app.services.google_translation import configured_google_translation_provider
from app.services.translation import TranslationProvider


def get_translation_provider(request: Request) -> TranslationProvider | None:
    """Return an app-injected provider; the default application has none."""
    if hasattr(request.app.state, "translation_provider"):
        return request.app.state.translation_provider
    return configured_google_translation_provider()
