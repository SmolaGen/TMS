from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Monitoring"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint to verify the application is running.
    """
    return {"status": "ok"}
