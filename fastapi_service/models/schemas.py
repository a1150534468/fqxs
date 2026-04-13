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


class ChapterResponse(APIBaseModel):
    content: str
    word_count: int


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
        'worldview', 'characters', 'map', 'storyline', 'plot_arc',
        'opening', 'dimension_framework', 'main_characters',
        'map_system', 'main_sub_plots', 'plot_extraction',
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
