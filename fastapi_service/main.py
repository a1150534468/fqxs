from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.ai_generate import router as ai_router
from routers.ws_generate import router as ws_router
from services.llm_provider_manager import llm_provider_manager

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

# Initialize provider manager
llm_provider_manager.set_django_api_url(settings.django_api_url)

app.include_router(ai_router)
app.include_router(ws_router)


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
