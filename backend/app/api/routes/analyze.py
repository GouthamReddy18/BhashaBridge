from fastapi import APIRouter, Depends

from app.api.dependencies import get_translation_provider
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.translation import TranslationProvider
from app.services.pipeline import analyze

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze_text(
    request: AnalyzeRequest,
    translation_provider: TranslationProvider | None = Depends(get_translation_provider),
) -> AnalyzeResponse:
    """Analyze text and optionally invoke an injected translation provider."""
    return analyze(request, translation_provider=translation_provider)
