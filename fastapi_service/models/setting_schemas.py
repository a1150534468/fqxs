"""Pydantic v2 schemas for the 11 novel setting types.

Each schema defines the structured JSON contract that the LLM must produce.
Fields are deliberately lax (defaults everywhere) so minor LLM mistakes
don't hard-fail validation.  Cross-step entity references use plain
Chinese name strings -- no IDs.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ #
# 1. worldview
# ------------------------------------------------------------------ #

class WorldviewSchema(BaseModel):
    """世界观 8 维度：时间/地点/社会/文化/科技/力量/历史/自然法则。"""

    time_setting: str = ""        # 时间设定：故事发生的年代
    place_setting: str = ""       # 地点设定：地理环境与空间布局
    social_structure: str = ""    # 社会结构：政治制度、经济状况、社会阶层
    cultural_background: str = "" # 文化背景：语言、宗教、艺术、习俗
    tech_level: str = ""          # 科技水平：技术水平对生活的影响
    power_system: str = ""        # 力量体系：魔法、科技或超能力规则
    history: str = ""             # 历史背景：世界的历史沿革
    natural_laws: str = ""        # 自然法则：世界的物理规律


# ------------------------------------------------------------------ #
# 2. characters (initial roster)
# ------------------------------------------------------------------ #

class CharacterBrief(BaseModel):
    name: str = ""
    role: str = ""
    alignment: str = ""
    brief: str = ""
    origin: str = ""


class CharactersSchema(BaseModel):
    characters: List[CharacterBrief] = []


# ------------------------------------------------------------------ #
# 3. map
# ------------------------------------------------------------------ #

class Region(BaseModel):
    name: str = ""
    type: str = ""
    description: str = ""
    connected_to: List[str] = []


class MapSchema(BaseModel):
    regions: List[Region] = []


# ------------------------------------------------------------------ #
# 4. storyline
# ------------------------------------------------------------------ #

class StorylineSchema(BaseModel):
    premise: str = ""
    central_conflict: str = ""
    themes: List[str] = []
    stakes: str = ""


# ------------------------------------------------------------------ #
# 5. plot_arc
# ------------------------------------------------------------------ #

class Act(BaseModel):
    name: str = ""
    description: str = ""
    key_events: List[str] = []


class PlotArcSchema(BaseModel):
    acts: List[Act] = []
    climax: str = ""
    resolution: str = ""


# ------------------------------------------------------------------ #
# 6. opening
# ------------------------------------------------------------------ #

class OpeningSchema(BaseModel):
    scene: str = ""
    hook: str = ""
    pov_character: str = ""
    first_chapter_goal: str = ""
    tone: str = ""


# ------------------------------------------------------------------ #
# 7. dimension_framework
# ------------------------------------------------------------------ #

class TimeJump(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(default="", alias="from")
    to: str = ""
    purpose: str = ""


class DimensionFrameworkSchema(BaseModel):
    timeline_structure: str = ""
    pov_mode: str = ""
    pov_characters: List[str] = []
    time_jumps: List[TimeJump] = []
    narrative_devices: List[str] = []


# ------------------------------------------------------------------ #
# 8. main_characters (deep cards)
# ------------------------------------------------------------------ #

class Relationship(BaseModel):
    target: str = ""
    type: str = ""
    dynamic: str = ""


class DeepCharacter(BaseModel):
    name: str = ""
    motivation: str = ""
    inner_conflict: str = ""
    growth_arc: str = ""
    backstory: str = ""
    relationships: List[Relationship] = []


class MainCharactersSchema(BaseModel):
    characters: List[DeepCharacter] = []


# ------------------------------------------------------------------ #
# 9. map_system
# ------------------------------------------------------------------ #

class Faction(BaseModel):
    name: str = ""
    influence: str = ""
    base: str = ""


class RegionSystem(BaseModel):
    name: str = ""
    factions: List[Faction] = []
    routes: List[str] = []
    resources: List[str] = []
    significance: str = ""


class MapSystemSchema(BaseModel):
    regions: List[RegionSystem] = []


# ------------------------------------------------------------------ #
# 10. main_sub_plots
# ------------------------------------------------------------------ #

class PlotEvent(BaseModel):
    chapter_range: str = ""
    event: str = ""
    characters: List[str] = []


class MainPlot(BaseModel):
    theme: str = ""
    events: List[PlotEvent] = []


class SubPlot(BaseModel):
    name: str = ""
    characters: List[str] = []
    events: List[PlotEvent] = []
    crosses_main: str = ""


class MainSubPlotsSchema(BaseModel):
    main_plot: MainPlot = MainPlot()
    sub_plots: List[SubPlot] = []


# ------------------------------------------------------------------ #
# 11. plot_extraction
# ------------------------------------------------------------------ #

class ExtractedAct(BaseModel):
    name: str = ""
    span: str = ""
    summary: str = ""
    turning_point: str = ""


class KeyTurn(BaseModel):
    chapter: int = 0
    type: str = ""
    description: str = ""


class PlotExtractionSchema(BaseModel):
    structure: str = ""
    acts: List[ExtractedAct] = []
    key_turns: List[KeyTurn] = []
    pacing: str = ""
    theme_distillation: str = ""


# ------------------------------------------------------------------ #
# Lookup map  setting_type str -> schema class
# ------------------------------------------------------------------ #

SETTING_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    'worldview': WorldviewSchema,
    'characters': CharactersSchema,
    'map': MapSchema,
    'storyline': StorylineSchema,
    'plot_arc': PlotArcSchema,
    'opening': OpeningSchema,
    'dimension_framework': DimensionFrameworkSchema,
    'main_characters': MainCharactersSchema,
    'map_system': MapSystemSchema,
    'main_sub_plots': MainSubPlotsSchema,
    'plot_extraction': PlotExtractionSchema,
}
