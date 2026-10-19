from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="BhashaBridge 2.0", version="0.1.0", description="Phase 1 API scaffold; NLP modules are not yet implemented.")

class ModuleStatus(BaseModel):
    name: str
    status: str
    detail: str

@app.get("/health")
def health() -> dict[str, str]:
    """Confirm that the API process can answer requests."""
    return {"status": "ok"}

@app.get("/ready")
def readiness() -> dict[str, object]:
    """Report configured/available modules separately from future work."""
    modules = [
        ModuleStatus(name="api", status="available", detail="FastAPI process is serving requests."),
        ModuleStatus(name="input_validation", status="configured", detail="Request framework is present; analysis endpoint is not implemented."),
        ModuleStatus(name="normalization", status="not_implemented", detail="No text transformations are performed."),
        ModuleStatus(name="tokenization", status="not_implemented", detail="No token analysis endpoint is available."),
        ModuleStatus(name="language_identification", status="not_implemented", detail="No model or baseline is loaded."),
        ModuleStatus(name="transliteration", status="not_implemented", detail="No transliteration model is loaded."),
        ModuleStatus(name="linguistic_analysis", status="not_implemented", detail="POS/NER are not implemented."),
        ModuleStatus(name="ambiguity_resolution", status="not_implemented", detail="No ambiguity rules or model are implemented."),
        ModuleStatus(name="translation", status="not_implemented", detail="No translation provider is configured."),
        ModuleStatus(name="evaluation", status="not_implemented", detail="No evaluation runner or results exist."),
    ]
    return {"status": "degraded", "ready": False, "modules": [m.model_dump() for m in modules]}
