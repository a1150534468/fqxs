from typing import Optional

from fastapi import APIRouter, Header

from models.inspiration_schemas import (
    InspirationGenerateRequest,
    InspirationGenerateResponse,
    CustomInspirationRequest,
)
from models.schemas import (
    ChapterRequest,
    ChapterResponse,
    ChapterAnalysisRequest,
    ChapterSummaryAnalysisResponse,
    ContinueRequest,
    ContinueResponse,
    ConsistencyAnalysisResponse,
    GenerateTitlesRequest,
    GenerateTitlesResponse,
    KnowledgeFactAnalysisResponse,
    OutlineRequest,
    OutlineResponse,
    SettingGenerateRequest,
    SettingGenerateResponse,
    StyleDriftAnalysisResponse,
)
from services.llm_client import llm_client

router = APIRouter(prefix="/api/ai", tags=["AI Generation"])


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if authorization and authorization.startswith('Bearer '):
        return authorization.replace('Bearer ', '', 1)
    return None


@router.post("/generate/outline", response_model=OutlineResponse)
async def generate_outline(
    payload: OutlineRequest,
    authorization: Optional[str] = Header(None),
) -> OutlineResponse:
    token = _extract_token(authorization)
    outline, estimated_words = await llm_client.generate_outline(
        inspiration_id=payload.inspiration_id,
        genre=payload.genre,
        target_chapters=payload.target_chapters,
        user_token=token,
    )
    return OutlineResponse(outline=outline, estimated_words=estimated_words)


@router.post("/generate/chapter", response_model=ChapterResponse)
async def generate_chapter(
    payload: ChapterRequest,
    authorization: Optional[str] = Header(None),
) -> ChapterResponse:
    token = _extract_token(authorization)
    content, word_count = await llm_client.generate_chapter(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        chapter_title=payload.chapter_title,
        outline_context=payload.outline_context,
        context_payload=payload.context_payload,
        user_token=token,
    )
    return ChapterResponse(content=content, word_count=word_count)


@router.post("/continue", response_model=ContinueResponse)
async def continue_content(
    payload: ContinueRequest,
    authorization: Optional[str] = Header(None),
) -> ContinueResponse:
    token = _extract_token(authorization)
    content, word_count = await llm_client.continue_content(
        current_content=payload.current_content,
        continue_length=payload.continue_length,
        user_token=token,
    )
    return ContinueResponse(continued_content=content, word_count=word_count)


@router.post("/generate/inspiration", response_model=InspirationGenerateResponse)
async def generate_inspiration(
    payload: InspirationGenerateRequest,
    authorization: Optional[str] = Header(None),
) -> InspirationGenerateResponse:
    token = _extract_token(authorization)
    trending_books = [book.model_dump() for book in payload.trending_books]
    result = await llm_client.generate_inspiration(
        trending_books=trending_books,
        genre_preference=payload.genre_preference,
        user_token=token,
    )
    return InspirationGenerateResponse(**result)


@router.post("/generate/custom-inspiration", response_model=InspirationGenerateResponse)
async def generate_custom_inspiration(
    payload: CustomInspirationRequest,
    authorization: Optional[str] = Header(None),
) -> InspirationGenerateResponse:
    token = _extract_token(authorization)
    result = await llm_client.generate_custom_inspiration(
        custom_prompt=payload.custom_prompt,
        count=payload.count,
        user_token=token,
    )
    return InspirationGenerateResponse(**result)


@router.post("/generate/setting", response_model=SettingGenerateResponse)
async def generate_setting(
    payload: SettingGenerateRequest,
    authorization: Optional[str] = Header(None),
) -> SettingGenerateResponse:
    token = _extract_token(authorization)
    prior_settings = [ps.model_dump() for ps in payload.prior_settings]
    result = await llm_client.generate_setting(
        setting_type=payload.setting_type,
        book_title=payload.book_title,
        genre=payload.genre,
        context=payload.context,
        prior_settings=prior_settings,
        user_token=token,
    )
    return SettingGenerateResponse(**result)


@router.post("/generate/titles", response_model=GenerateTitlesResponse)
async def generate_titles(
    payload: GenerateTitlesRequest,
    authorization: Optional[str] = Header(None),
) -> GenerateTitlesResponse:
    token = _extract_token(authorization)
    titles = await llm_client.generate_titles(
        inspiration=payload.inspiration,
        genre=payload.genre,
        style_preference=payload.style_preference,
        count=payload.count,
        user_token=token,
    )
    return GenerateTitlesResponse(titles=titles)


@router.post("/analyze/chapter-summary", response_model=ChapterSummaryAnalysisResponse)
async def analyze_chapter_summary(
    payload: ChapterAnalysisRequest,
) -> ChapterSummaryAnalysisResponse:
    result = await llm_client.analyze_chapter_summary(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        content=payload.content,
        context_payload=payload.context_payload,
    )
    return ChapterSummaryAnalysisResponse(**result)


@router.post("/analyze/facts", response_model=KnowledgeFactAnalysisResponse)
async def analyze_facts(
    payload: ChapterAnalysisRequest,
) -> KnowledgeFactAnalysisResponse:
    result = await llm_client.analyze_facts(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        content=payload.content,
        context_payload=payload.context_payload,
    )
    return KnowledgeFactAnalysisResponse(**result)


@router.post("/analyze/style-drift", response_model=StyleDriftAnalysisResponse)
async def analyze_style_drift(
    payload: ChapterAnalysisRequest,
) -> StyleDriftAnalysisResponse:
    result = await llm_client.analyze_style_drift(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        content=payload.content,
        context_payload=payload.context_payload,
    )
    return StyleDriftAnalysisResponse(**result)


@router.post("/analyze/consistency", response_model=ConsistencyAnalysisResponse)
async def analyze_consistency(
    payload: ChapterAnalysisRequest,
) -> ConsistencyAnalysisResponse:
    result = await llm_client.analyze_consistency(
        project_id=payload.project_id,
        chapter_number=payload.chapter_number,
        content=payload.content,
        context_payload=payload.context_payload,
    )
    return ConsistencyAnalysisResponse(**result)
