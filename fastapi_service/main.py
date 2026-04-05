from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.ai_generate import router as ai_router

app = FastAPI(
    title=settings.app_name,
    description="Standalone FastAPI service for AI content generation (mock mode).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "mock_generation": settings.mock_generation,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
