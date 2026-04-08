from typing import Optional

from fastapi import APIRouter, Header

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
async def generate_outline(
    payload: OutlineRequest,
    authorization: Optional[str] = Header(None),
) -> OutlineResponse:
    # Extract token from Authorization header
    if authorization and authorization.startswith('Bearer '):
        token = authorization.replace('Bearer ', '')
        llm_client.set_user_token(token)

    outline, estimated_words = await llm_client.generate_outline(
        inspiration_id=payload.inspiration_id,
        genre=payload.genre,
        target_chapters=payload.target_chapters,
    )
    return OutlineResponse(outline=outline, estimated_words=estimated_words)


@router.post("/generate/chapter", response_model=ChapterResponse)
async def generate_chapter(
    payload: ChapterRequest,
    authorization: Optional[str] = Header(None),
) -> ChapterResponse:
    # Extract token from Authorization header
    if authorization and authorization.startswith('Bearer '):
        token = authorization.replace('Bearer ', '')
        llm_client.set_user_token(token)

    content, word_count = await llm_client.generate_chapter(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        chapter_title=payload.chapter_title,
        outline_context=payload.outline_context,
    )
    return ChapterResponse(content=content, word_count=word_count)


@router.post("/continue", response_model=ContinueResponse)
async def continue_content(
    payload: ContinueRequest,
    authorization: Optional[str] = Header(None),
) -> ContinueResponse:
    # Extract token from Authorization header
    if authorization and authorization.startswith('Bearer '):
        token = authorization.replace('Bearer ', '')
        llm_client.set_user_token(token)

    content, word_count = await llm_client.continue_content(
        current_content=payload.current_content,
        continue_length=payload.continue_length,
    )
    return ContinueResponse(continued_content=content, word_count=word_count)
