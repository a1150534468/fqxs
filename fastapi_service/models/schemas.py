from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class OutlineRequest(APIBaseModel):
    inspiration_id: int = Field(..., ge=1)
    genre: str = Field(..., min_length=1, max_length=50)
    target_chapters: int = Field(..., ge=1, le=2000)


class OutlineResponse(APIBaseModel):
    outline: str
    estimated_words: int


class ChapterRequest(APIBaseModel):
    project_id: int = Field(..., ge=1)
    chapter_number: int = Field(..., ge=1)
    chapter_title: str = Field(..., min_length=1, max_length=200)
    outline_context: str = Field(default="", max_length=10000)
    context_payload: dict = Field(default_factory=dict)


class ChapterResponse(APIBaseModel):
    content: str
    word_count: int


class ChapterAnalysisRequest(APIBaseModel):
    project_id: int = Field(..., ge=1)
    chapter_number: int = Field(..., ge=1)
    content: str = Field(..., min_length=1, max_length=80000)
    context_payload: dict = Field(default_factory=dict)


class ChapterSummaryAnalysisResponse(APIBaseModel):
    summary: str
    key_events: list[str] = []
    open_threads: list[str] = []


class KnowledgeFactItem(APIBaseModel):
    subject: str
    predicate: str
    object: str
    source_excerpt: str = ""
    confidence: float = 0.0


class KnowledgeFactAnalysisResponse(APIBaseModel):
    facts: list[KnowledgeFactItem] = []


class StyleDriftAnalysisResponse(APIBaseModel):
    score: int
    risk_level: str
    reasons: list[str] = []
    suggestions: list[str] = []


class ConsistencyAnalysisResponse(APIBaseModel):
    status: str
    conflicts: list[str] = []
    risks: list[str] = []
    suggestions: list[str] = []


class ContinueRequest(APIBaseModel):
    current_content: str = Field(..., min_length=1, max_length=50000)
    continue_length: int = Field(..., ge=100, le=5000)


class ContinueResponse(APIBaseModel):
    continued_content: str
    word_count: int


class PriorSetting(APIBaseModel):
    setting_type: str
    title: str = ""
    content: str = ""
    structured_data: dict = {}


class SettingGenerateRequest(APIBaseModel):
    setting_type: Literal[
        'worldview', 'characters', 'map', 'storyline', 'plot_arc', 'opening',
    ]
    book_title: str
    genre: str = ""
    context: str = ""
    prior_settings: list[PriorSetting] = []


class SettingGenerateResponse(APIBaseModel):
    setting_type: str
    title: str
    content: str
    structured_data: dict = {}
    validation_ok: bool = True
    retries: int = 0


class GenerateTitlesRequest(APIBaseModel):
    inspiration: str = Field(..., min_length=1)
    genre: str = Field(default="", max_length=50)
    style_preference: str = Field(default="", max_length=100)
    count: int = Field(default=3, ge=3, le=5)


class GenerateTitlesResponse(APIBaseModel):
    titles: list[str]
