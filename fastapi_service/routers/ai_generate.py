from fastapi import APIRouter

from models.schemas import (
    ChapterRequest,
    ChapterResponse,
    ContinueRequest,
    ContinueResponse,
    OutlineRequest,
    OutlineResponse,
)
from services.llm_client import llm_client

router = APIRouter(prefix="/api/ai", tags=["AI Generation"])


@router.post("/generate/outline", response_model=OutlineResponse)
async def generate_outline(payload: OutlineRequest) -> OutlineResponse:
    outline, estimated_words = await llm_client.generate_outline(
        inspiration_id=payload.inspiration_id,
        genre=payload.genre,
        target_chapters=payload.target_chapters,
    )
    return OutlineResponse(outline=outline, estimated_words=estimated_words)


@router.post("/generate/chapter", response_model=ChapterResponse)
async def generate_chapter(payload: ChapterRequest) -> ChapterResponse:
    content, word_count = await llm_client.generate_chapter(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        chapter_title=payload.chapter_title,
        outline_context=payload.outline_context,
    )
    return ChapterResponse(content=content, word_count=word_count)


@router.post("/continue", response_model=ContinueResponse)
async def continue_content(payload: ContinueRequest) -> ContinueResponse:
    content, word_count = await llm_client.continue_content(
        current_content=payload.current_content,
        continue_length=payload.continue_length,
    )
    return ContinueResponse(continued_content=content, word_count=word_count)
