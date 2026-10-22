"""Read-only research readiness route."""
from fastapi import APIRouter

from app.services.project_readiness import project_research_readiness

router = APIRouter(prefix="/api/v1/research", tags=["research readiness"])


@router.get("/readiness")
def research_readiness() -> dict:
    """Return current local dataset, resource, provider, and condition readiness."""
    return project_research_readiness()
