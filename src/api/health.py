from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Checks the health of the application.
    Returns a simple status indicating if the service is up.
    """
    return {"status": "ok"}
