from fastapi import APIRouter

from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.services.pipeline import analyze

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """Normalize, tokenize, and return per-token language labels."""
    return analyze(request)
