from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Performs a health check on the application.
    Returns a simple status to indicate the application is running.
    """
    return {"status": "ok"}
