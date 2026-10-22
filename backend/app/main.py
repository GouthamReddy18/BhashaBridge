from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.api.routes.analyze import router as analyze_router
from app.api.routes.research import router as research_router
from app.api.dependencies import get_translation_provider
from app.services.language_identification import configured_model_status
from app.services.google_translation import google_translation_readiness
from app.services.transliteration import configured_transliteration_status

app = FastAPI(title="BhashaBridge 2.0", version="0.3.0", description="Whitespace normalization, Unicode tokenization, and conservative token-level language identification.")
app.include_router(analyze_router)
app.include_router(research_router)

class ModuleStatus(BaseModel):
    name: str
    status: str
    detail: str

@app.get("/health")
def health() -> dict[str, str]:
    """Confirm that the API process can answer requests."""
    return {"status": "ok"}

@app.get("/ready")
def readiness(request: Request) -> dict[str, object]:
    """Report baseline and optional pretrained model readiness separately."""
    model_status = configured_model_status()
    transliteration_status, transliteration_detail = configured_transliteration_status()
    translation_provider = get_translation_provider(request)
    translation_status = (
        google_translation_readiness()
        if translation_provider is None
        else None
    )
    modules = [
        ModuleStatus(name="api", status="available", detail="FastAPI process is serving requests."),
        ModuleStatus(name="input_validation", status="available", detail="Analyze requests validate type, non-empty text, and maximum length."),
        ModuleStatus(name="normalization", status="available", detail="Whitespace-only normalization is implemented."),
        ModuleStatus(name="tokenization", status="available", detail="Unicode word and punctuation tokenization is implemented."),
        ModuleStatus(name="language_identification", status="available", detail="Conservative token-level script/category rules, small seed lexicons, and UNKNOWN abstention are active."),
        ModuleStatus(name="indic_lid_model", status=model_status.status, detail=model_status.detail),
        ModuleStatus(name="transliteration", status=transliteration_status, detail=transliteration_detail),
        ModuleStatus(name="linguistic_analysis", status="not_implemented", detail="POS tagging and NER are not implemented."),
        ModuleStatus(name="ambiguity_resolution", status="available", detail="One deterministic illustrative fixture rule is active; broader contextual interpretation is not validated."),
        ModuleStatus(
            name="translation",
            status="configured" if translation_provider is not None else translation_status.status,
            detail="An application-injected provider is available; requests are opt-in."
            if translation_provider is not None else translation_status.detail,
        ),
        ModuleStatus(name="evaluation", status="available", detail="Offline evaluation and report-validation tools are implemented; this analysis API does not execute experiments."),
    ]
    return {"status": "degraded", "ready": False, "modules": [m.model_dump() for m in modules]}
