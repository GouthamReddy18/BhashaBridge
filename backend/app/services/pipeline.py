from app.schemas.analysis import AnalyzeResponse, AnalyzeRequest, AnalyzedToken, ModuleStatus
from app.services.transliteration import TransliterationEngine, transliterate_tokens
from app.services.ambiguity_resolution import resolve_ambiguities
from app.services.language_identification import resolve_identifier
from app.services.preprocessing import normalize_whitespace
from app.services.tokenization import tokenize


def analyze(
    request: AnalyzeRequest,
    *,
    transliteration_enabled: bool | None = None,
    transliteration_engine: TransliterationEngine | None = None,
) -> AnalyzeResponse:
    """Run preprocessing, token-level identification, transliteration, and ambiguity rules."""
    normalized_text = normalize_whitespace(request.text)
    tokens = tokenize(normalized_text)
    identifier, model_status = resolve_identifier()
    annotations = identifier.identify(tokens)
    analyzed_tokens = [
        AnalyzedToken(**token.model_dump(), language=annotation)
        for token, annotation in zip(tokens, annotations, strict=True)
    ]
    transliterations, transliteration_status, transliteration_detail = transliterate_tokens(
        analyzed_tokens, enabled=transliteration_enabled, engine=transliteration_engine
    )
    ambiguities = resolve_ambiguities(
        normalized_text=normalized_text,
        tokens=analyzed_tokens,
        transliterations=transliterations,
    )
    return AnalyzeResponse(
        original_text=request.text,
        normalized_text=normalized_text,
        tokens=analyzed_tokens,
        transliterations=transliterations,
        ambiguities=ambiguities,
        modules=[
            ModuleStatus(name="input_validation", status="available", detail="Request type, non-empty content, and size are validated."),
            ModuleStatus(name="normalization", status="available", detail="Only leading/trailing and repeated whitespace is normalized."),
            ModuleStatus(name="tokenization", status="available", detail="Unicode word and punctuation tokenization with normalized-text offsets."),
            ModuleStatus(name="language_identification", status="available", detail="Conservative token-level baseline is active; labels include script/category rules, exact seed lexicons, and abstentions."),
            ModuleStatus(name="indic_lid_model", status=model_status.status, detail=model_status.detail),
            ModuleStatus(name="transliteration", status=transliteration_status, detail=transliteration_detail),
            ModuleStatus(name="linguistic_analysis", status="not_implemented", detail="POS tagging and NER are not implemented."),
            ModuleStatus(name="ambiguity_resolution", status="available", detail="One deterministic illustrative fixture rule; behavior is not validated for Telugu-English code-mixed text."),
            ModuleStatus(name="translation", status="not_implemented", detail="No translation is performed."),
        ],
    )
