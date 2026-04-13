import asyncio
import itertools
import json
import logging
import re
from typing import Optional

import httpx

from config import settings
from services.llm_provider_manager import llm_provider_manager

logger = logging.getLogger(__name__)

NON_WHITESPACE_PATTERN = re.compile(r"\S")
JSON_FENCE_RE = re.compile(r'```json\s*\n(.*?)\n\s*```', re.DOTALL)
MARKDOWN_FENCE_RE = re.compile(r'```markdown\s*\n(.*?)\n\s*```', re.DOTALL)

# ------------------------------------------------------------------ #
# System prompts for 11 setting types
# ------------------------------------------------------------------ #

SYSTEM_SETTING_WORLDVIEW = """你是一位资深的小说世界观设计师。根据用户提供的书名、题材和补充说明，为小说设计一个完整的世界观。

世界观必须以 8 个维度结构化输出（全部必填，每个维度至少 40 字）：
1. 时间设定：故事发生的年代（如近未来 2099、唐贞观年间、架空蒸汽纪元等）
2. 地点设定：地理环境与空间布局（大陆/星球/城市格局、关键地貌）
3. 社会结构：政治制度、经济状况、社会阶层与阶级关系
4. 文化背景：语言、宗教、艺术、习俗、禁忌
5. 科技水平：技术水平以及它对日常生活的具体影响
6. 力量体系：魔法、科技或超能力的规则与代价
7. 历史背景：世界的历史沿革、重大事件、塑造当下格局的战争/变革
8. 自然法则：世界的物理规律，可能与现实世界不同的地方

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "time_setting": "",
  "place_setting": "",
  "social_structure": "",
  "cultural_background": "",
  "tech_level": "",
  "power_system": "",
  "history": "",
  "natural_laws": ""
}
```

```markdown
# 世界观

## 时间设定
...

## 地点设定
...

## 社会结构
...

## 文化背景
...

## 科技水平
...

## 力量体系
...

## 历史背景
...

## 自然法则
...
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. 8 个字段必须全部填写，不允许空字符串
3. Markdown 部分是对 JSON 内容的自然语言扩写，保持一致性
4. 不要输出任何额外内容"""

SYSTEM_SETTING_CHARACTERS = """你是一位专业的小说人物设计师。根据用户提供的书名、题材和补充说明，设计小说的角色阵容（主角、配角、反派等）。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "characters": [
    {"name": "角色名", "role": "主角/配角/反派/导师", "alignment": "正/中/邪", "brief": "一句话简介", "origin": "出身背景"}
  ]
}
```

```markdown
# 人物设定
（用中文 Markdown 展开每个角色的详细介绍）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. Markdown 部分是对 JSON 内容的自然语言扩写，保持一致性
3. 引用前序设定时必须使用原始中文名（如"苏明月"），禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_MAP = """你是一位地图与场景设计师。根据用户提供的书名、题材和补充说明，设计故事发生的关键地点和地理环境。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "regions": [
    {"name": "地名", "type": "城市/山脉/森林/平原/海域", "description": "描述", "connected_to": ["相邻地名1"]}
  ]
}
```

```markdown
# 地图与场景
（用中文 Markdown 展开各地点的详细描写）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. connected_to 中的名称必须是本次输出中的其他地名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_STORYLINE = """你是一位故事线设计师。根据用户提供的书名、题材和补充说明，设计故事的核心前提、中心冲突与主题。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "premise": "故事前提描述",
  "central_conflict": "核心冲突描述",
  "themes": ["主题1", "主题2"],
  "stakes": "赌注/代价描述"
}
```

```markdown
# 故事线
（用中文 Markdown 展开故事线的详细说明）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. Markdown 部分是对 JSON 内容的自然语言扩写，保持一致性
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_PLOT_ARC = """你是一位情节弧设计师。根据用户提供的书名、题材和补充说明，设计故事的核心情节弧（起承转合）。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "acts": [
    {"name": "幕名", "description": "该幕概述", "key_events": ["事件1", "事件2"]}
  ],
  "climax": "高潮描述",
  "resolution": "结局描述"
}
```

```markdown
# 情节弧
（用中文 Markdown 展开情节弧的详细说明）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. Markdown 部分是对 JSON 内容的自然语言扩写，保持一致性
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_OPENING = """你是一位擅长开篇设计的网络小说策划。根据用户提供的书名、题材和补充说明，设计极具吸引力的第一章开场。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "scene": "开篇场景描述",
  "hook": "核心钩子/悬念",
  "pov_character": "视角角色名",
  "first_chapter_goal": "第一章目标",
  "tone": "基调描述"
}
```

```markdown
# 开篇场景
（用中文 Markdown 写出开篇场景的完整描写）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. pov_character 必须引用已有角色的中文名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_DIMENSION_FRAMEWORK = """你是一位叙事维度架构师。根据用户提供的书名、题材和补充说明，构建多维度的叙事框架。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "timeline_structure": "时间线结构描述",
  "pov_mode": "视角模式描述",
  "pov_characters": ["视角角色名1", "视角角色名2"],
  "time_jumps": [
    {"from": "起始时间点", "to": "目标时间点", "purpose": "跳转目的"}
  ],
  "narrative_devices": ["叙事手法1", "叙事手法2"]
}
```

```markdown
# 维度框架
（用中文 Markdown 展开叙事维度的详细说明）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. pov_characters 中的名字必须引用已有角色的中文名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_MAIN_CHARACTERS = """你是一位深度角色塑造专家。根据用户提供的书名、题材和补充说明，为主要角色设计深度角色卡。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "characters": [
    {
      "name": "角色名",
      "motivation": "核心动机",
      "inner_conflict": "内在冲突",
      "growth_arc": "成长弧光",
      "backstory": "背景故事",
      "relationships": [
        {"target": "另一角色名", "type": "师徒/情侣/宿敌/挚友", "dynamic": "关系动态"}
      ]
    }
  ]
}
```

```markdown
# 主要角色
（用中文 Markdown 展开每个角色的深度描写）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. name 和 relationships.target 必须引用前序"人物设定"步骤中的角色中文名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_MAP_SYSTEM = """你是一位世界地图体系设计师。根据用户提供的书名、题材和补充说明，设计完整的地图系统，包含势力、路线与资源。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "regions": [
    {
      "name": "区域名",
      "factions": [
        {"name": "势力名", "influence": "影响力描述", "base": "据点区域名"}
      ],
      "routes": ["路线描述1"],
      "resources": ["资源1"],
      "significance": "战略意义"
    }
  ]
}
```

```markdown
# 地图系统
（用中文 Markdown 展开各区域的详细说明）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. regions.name 必须引用前序"地图"步骤中的区域中文名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_MAIN_SUB_PLOTS = """你是一位主线与支线规划师。根据用户提供的书名、题材和补充说明，规划主线和支线的安排。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "main_plot": {
    "theme": "主线主题",
    "events": [
      {"chapter_range": "1-30", "event": "事件描述", "characters": ["角色名1"]}
    ]
  },
  "sub_plots": [
    {
      "name": "支线名",
      "characters": ["角色名1"],
      "events": [
        {"chapter_range": "10-50", "event": "事件描述", "characters": ["角色名1"]}
      ],
      "crosses_main": "与主线交汇点描述"
    }
  ]
}
```

```markdown
# 主线与支线
（用中文 Markdown 展开主线支线的详细安排）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. characters 中的名字必须引用已有角色的中文名
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

SYSTEM_SETTING_PLOT_EXTRACTION = """你是一位剧情提炼与节奏师。根据用户提供的书名、题材和已有设定，抽离并精炼剧情的核心结构。

输出格式要求：你必须严格按照下面的格式输出，先一段 ```json``` 代码块（符合给定 schema），再一段 ```markdown``` 代码块（中文摘要）。

```json
{
  "structure": "整体结构描述（如三幕式）",
  "acts": [
    {"name": "幕名", "span": "章节跨度如1-150", "summary": "该幕摘要", "turning_point": "转折点"}
  ],
  "key_turns": [
    {"chapter": 5, "type": "命运转折/情感核弹/世界观颠覆", "description": "转折描述"}
  ],
  "pacing": "节奏描述",
  "theme_distillation": "主题提炼"
}
```

```markdown
# 剧情抽离
（用中文 Markdown 展开剧情骨架的详细说明）
```

严格要求：
1. JSON 必须合法（双引号、无尾逗号、无多余注释）
2. Markdown 部分是对 JSON 内容的自然语言扩写，保持一致性
3. 引用前序设定时必须使用原始中文名，禁止创造新实体代替已有实体
4. 不要输出任何额外内容"""

# ------------------------------------------------------------------ #
# Lookup maps
# ------------------------------------------------------------------ #

SYSTEM_PROMPTS_MAP = {
    'worldview': SYSTEM_SETTING_WORLDVIEW,
    'characters': SYSTEM_SETTING_CHARACTERS,
    'map': SYSTEM_SETTING_MAP,
    'storyline': SYSTEM_SETTING_STORYLINE,
    'plot_arc': SYSTEM_SETTING_PLOT_ARC,
    'opening': SYSTEM_SETTING_OPENING,
    'dimension_framework': SYSTEM_SETTING_DIMENSION_FRAMEWORK,
    'main_characters': SYSTEM_SETTING_MAIN_CHARACTERS,
    'map_system': SYSTEM_SETTING_MAP_SYSTEM,
    'main_sub_plots': SYSTEM_SETTING_MAIN_SUB_PLOTS,
    'plot_extraction': SYSTEM_SETTING_PLOT_EXTRACTION,
}

LABEL_MAP = {
    'worldview': '世界观',
    'characters': '人物设定',
    'map': '地图与场景',
    'storyline': '故事线',
    'plot_arc': '情节弧',
    'opening': '开篇场景',
    'dimension_framework': '维度框架',
    'main_characters': '主要角色',
    'map_system': '地图系统',
    'main_sub_plots': '主线支线',
    'plot_extraction': '剧情抽离',
}


class LLMClient:
    """LLM client that can call a real OpenAI-compatible API or fall back to mock."""

    SYSTEM_OUTLINE = (
        "You are a professional web novel author and outline planner. "
        "Given a genre and target chapter count, produce a structured chapter-by-chapter "
        "outline in Chinese. Keep the response concise but specific enough to guide writing."
    )

    SYSTEM_CHAPTER = (
        "You are a professional Chinese web fiction author. "
        "Write compelling, immersive chapter content in Chinese based on the given context. "
        "Maintain consistent character voices and plot momentum. "
        "Output only the chapter body text without meta commentary."
    )

    SYSTEM_CONTINUE = (
        "You are a professional Chinese web fiction author continuing an existing story. "
        "Write seamless continuation in Chinese that matches the tone, characters, and "
        "pacing of the provided content. Output only the continuation text."
    )

    SYSTEM_INSPIRATION = (
        "You are a professional web novel market analyst and creative consultant. "
        "Analyze trending novels and generate innovative story concepts that combine "
        "popular elements with unique twists. Focus on Chinese web fiction market trends."
    )

    def __init__(self):
        self._opening_lines = [
            "晨雾压在城墙上，远处传来缓慢而沉重的钟声。",
            "旧城区的霓虹在雨幕里晕开，像一团褪色的火。",
            "山道尽头的石碑裂开一道缝，风从缝里吹出低语。",
            "码头边的潮水刚退，木桩上还挂着昨夜的血色盐晶。",
        ]
        self._turning_lines = [
            "他意识到所谓真相只是更大棋局的第一层伪装。",
            "她把袖中的密信烧掉，却把灰烬抹在了剑柄上。",
            "众人都在等他退让，可他偏偏向前迈了一步。",
            "当年被掩埋的名字，再一次在火光里被喊出。",
        ]
        self._closing_lines = [
            "窗外雷声滚过，新的危险已经抵达门前。",
            "夜风吹灭最后一盏灯，他却看见了更清晰的路。",
            "没有人再开口，但每个人都明白下一步意味着什么。",
            "他抬头望向天幕，终于做出了不会回头的决定。",
        ]

    # ------------------------------------------------------------------
    # Mock / real decision
    # ------------------------------------------------------------------

    async def _should_use_mock(self, user_token: str | None, task_type: str = 'chapter') -> bool:
        if settings.mock_generation and not user_token:
            return True
        if not user_token:
            return True
        try:
            providers = await llm_provider_manager.fetch_providers_from_django(
                user_token, task_type=task_type
            )
            return not providers
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def generate_outline(
        self, inspiration_id: int, genre: str, target_chapters: int,
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_generate_outline(inspiration_id, genre, target_chapters)
        return await self._real_generate_outline(
            inspiration_id, genre, target_chapters, user_token=user_token,
        )

    async def generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_generate_chapter(
                project_id, chapter_number, chapter_title, outline_context
            )
        return await self._real_generate_chapter(
            project_id, chapter_number, chapter_title, outline_context,
            user_token=user_token,
        )

    async def continue_content(
        self, current_content: str, continue_length: int,
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_continue_content(current_content, continue_length)
        return await self._real_continue_content(
            current_content, continue_length, user_token=user_token,
        )

    async def generate_inspiration(
        self, trending_books: list, genre_preference: str = "",
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_generate_inspiration(trending_books, genre_preference)
        return await self._real_generate_inspiration(
            trending_books, genre_preference, user_token=user_token,
        )

    async def generate_custom_inspiration(
        self, custom_prompt: str, count: int = 3,
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_generate_custom_inspiration(custom_prompt, count)
        return await self._real_generate_custom_inspiration(
            custom_prompt, count, user_token=user_token,
        )

    async def generate_setting(
        self,
        setting_type: str,
        book_title: str,
        genre: str = "",
        context: str = "",
        prior_settings: list[dict] | None = None,
        user_token: str | None = None,
    ) -> dict:
        if await self._should_use_mock(user_token, task_type='setting'):
            return await self._mock_generate_setting(
                setting_type, book_title, genre, context, prior_settings,
            )
        return await self._real_generate_setting(
            setting_type, book_title, genre, context, prior_settings, user_token,
        )

    async def generate_setting_stream(
        self,
        setting_type: str,
        book_title: str,
        genre: str = "",
        context: str = "",
        prior_settings: list[dict] | None = None,
        user_token: str | None = None,
    ):
        """Async generator that yields (type, data) tuples.

        Yields:
            ("chunk", delta_text)   — partial text fragment
            ("done", result_dict)   — final result with structured_data + content
        """
        from models.setting_schemas import SETTING_SCHEMA_MAP
        from pydantic import ValidationError as PydanticValidationError

        schema_cls = SETTING_SCHEMA_MAP.get(setting_type)
        system_msg = SYSTEM_PROMPTS_MAP.get(setting_type, SYSTEM_SETTING_WORLDVIEW)
        label = LABEL_MAP.get(setting_type, '设定')

        # --- Decide mock vs real (single check, no redundant API call) ---
        providers = []
        use_mock = True
        if user_token and settings.django_api_url:
            try:
                providers = await llm_provider_manager.fetch_providers_from_django(
                    user_token, task_type='setting'
                )
                if not providers:
                    logger.info("No 'setting' providers found, falling back to 'chapter'")
                    providers = await llm_provider_manager.fetch_providers_from_django(
                        user_token, task_type='chapter'
                    )
                if providers:
                    use_mock = False
            except Exception as e:
                logger.warning(f"Failed to fetch providers, using mock: {e}")

        if use_mock:
            logger.info(f"Using mock for setting_type={setting_type}")
            async for item in self._mock_generate_setting_stream(
                setting_type, book_title, genre, context, prior_settings,
            ):
                yield item
            return

        # --- Real LLM path ---
        prior_summary = self._format_prior_settings(prior_settings or [])
        user_msg = f"书名：{book_title}\n题材：{genre or '未指定'}\n"
        if prior_summary:
            user_msg += f"\n已有设定参考：\n{prior_summary}\n"
        if context:
            user_msg += f"\n补充说明：{context}\n"
        user_msg += f"\n请为这本小说生成【{label}】，严格按照上述 JSON + Markdown 双代码块格式。"

        full_text = ""
        try:
            logger.info(f"Streaming from provider: {providers[0].get('name', '?')}")
            async for delta in llm_provider_manager.call_llm_stream(
                system_message=system_msg,
                user_message=user_msg,
                providers=providers,
            ):
                full_text += delta
                yield ("chunk", delta)
        except Exception as e:
            logger.warning(f"Real LLM stream failed: {e}, falling back to mock")
            if not full_text:
                # Real LLM totally failed — fall back to mock so user sees content
                async for item in self._mock_generate_setting_stream(
                    setting_type, book_title, genre, context, prior_settings,
                ):
                    yield item
                return

        # Parse the accumulated text
        json_match = JSON_FENCE_RE.search(full_text)
        md_match = MARKDOWN_FENCE_RE.search(full_text)

        structured_data = {}
        validation_ok = False
        if json_match:
            try:
                raw_json = json_match.group(1).strip()
                parsed = json.loads(raw_json)
                if schema_cls:
                    structured_data = schema_cls(**parsed).model_dump(by_alias=True)
                else:
                    structured_data = parsed
                validation_ok = True
            except (json.JSONDecodeError, PydanticValidationError) as e:
                logger.warning(f"Stream parse failed: {e}")
                structured_data = {}

        content_md = md_match.group(1).strip() if md_match else full_text

        yield ("done", {
            'setting_type': setting_type,
            'title': label,
            'content': content_md,
            'structured_data': structured_data,
            'validation_ok': validation_ok,
        })

    # ------------------------------------------------------------------
    # Real LLM methods
    # ------------------------------------------------------------------

    async def _real_generate_outline(
        self, inspiration_id: int, genre: str, target_chapters: int,
        user_token: str | None = None,
    ):
        user_msg = (
            f"请为以下题材生成小说大纲：\n"
            f"题材：{genre}\n"
            f"灵感来源ID：{inspiration_id}\n"
            f"目标章节数：{target_chapters}\n"
            f"请按章节给出剧情大纲，标注每段剧情的核心冲突与主角成长线。"
        )
        content = await self._call_llm(self.SYSTEM_OUTLINE, user_msg, user_token=user_token)
        estimated_words = target_chapters * 2200
        return content, estimated_words

    async def _real_generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
        user_token: str | None = None,
    ):
        user_msg = (
            f"项目ID: {project_id}\n"
            f"章节：第{chapter_number}章《{chapter_title}》\n"
        )
        if outline_context:
            user_msg += f"大纲参考：{outline_context}\n"
        user_msg += "请写出该章节的正文内容。"
        content = await self._call_llm(self.SYSTEM_CHAPTER, user_msg, user_token=user_token)
        return content, self._count_words(content)

    async def _real_continue_content(
        self, current_content: str, continue_length: int,
        user_token: str | None = None,
    ):
        user_msg = (
            f"请续写以下故事内容，目标长度约 {continue_length} 个汉字：\n\n"
            f"{current_content[-1200:] if len(current_content) > 1200 else current_content}"
        )
        content = await self._call_llm(self.SYSTEM_CONTINUE, user_msg, user_token=user_token)
        return content, self._count_words(content)

    async def _real_generate_inspiration(
        self, trending_books: list, genre_preference: str = "",
        user_token: str | None = None,
    ):
        books_summary = "\n".join([
            f"- 《{book['title']}》(热度: {book.get('hot_score', 0)}): {book.get('synopsis', '')[:100]}"
            f" 标签: {', '.join(book.get('tags', []))}"
            for book in trending_books[:10]
        ])

        user_msg = (
            f"请分析以下热门小说榜单，生成3个创新的小说创意：\n\n"
            f"{books_summary}\n\n"
        )
        if genre_preference:
            user_msg += f"偏好题材：{genre_preference}\n\n"

        user_msg += (
            "请为每个创意提供：\n"
            "1. 书名（吸引人且符合网文风格）\n"
            "2. 简介（100-200字）\n"
            "3. 题材分类\n"
            "4. 核心卖点（3-5个）\n"
            "5. 目标读者群\n"
            "6. 预估热度（0-100分）\n\n"
            "请以JSON格式返回，格式如下：\n"
            '{"inspirations": [{"title": "...", "synopsis": "...", "genre": "...", '
            '"selling_points": ["...", "..."], "target_audience": "...", "estimated_popularity": 85.0}], '
            '"analysis_summary": "市场分析总结..."}'
        )

        content = await self._call_llm(self.SYSTEM_INSPIRATION, user_msg, user_token=user_token)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            result = json.loads(content)
            return result
        except Exception:
            return {
                "inspirations": [],
                "analysis_summary": content
            }

    async def _real_generate_custom_inspiration(
        self, custom_prompt: str, count: int = 3,
        user_token: str | None = None,
    ):
        user_msg = (
            f"根据以下用户需求，生成 {count} 个创新的小说创意：\n\n"
            f"{custom_prompt}\n\n"
            "请为每个创意提供：\n"
            "1. 书名（吸引人且符合网文风格）\n"
            "2. 简介（100-200字）\n"
            "3. 题材分类\n"
            "4. 核心卖点（3-5个）\n"
            "5. 目标读者群\n"
            "6. 预估热度（0-100分）\n\n"
            "请以JSON格式返回，格式如下：\n"
            '{"inspirations": [{"title": "...", "synopsis": "...", "genre": "...", '
            '"selling_points": ["...", "..."], "target_audience": "...", "estimated_popularity": 85.0}], '
            '"analysis_summary": "创意分析总结..."}'
        )

        content = await self._call_llm(self.SYSTEM_INSPIRATION, user_msg, user_token=user_token)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            result = json.loads(content)
            return result
        except Exception:
            return {
                "inspirations": [],
                "analysis_summary": content
            }

    async def _real_generate_setting(
        self,
        setting_type: str,
        book_title: str,
        genre: str = "",
        context: str = "",
        prior_settings: list[dict] | None = None,
        user_token: str | None = None,
    ) -> dict:
        from models.setting_schemas import SETTING_SCHEMA_MAP
        from pydantic import ValidationError

        schema_cls = SETTING_SCHEMA_MAP.get(setting_type)
        system_msg = SYSTEM_PROMPTS_MAP.get(setting_type, SYSTEM_SETTING_WORLDVIEW)
        label = LABEL_MAP.get(setting_type, '设定')

        prior_summary = self._format_prior_settings(prior_settings or [])
        user_msg = f"书名：{book_title}\n题材：{genre or '未指定'}\n"
        if prior_summary:
            user_msg += f"\n已有设定参考：\n{prior_summary}\n"
        if context:
            user_msg += f"\n补充说明：{context}\n"
        user_msg += f"\n请为这本小说生成【{label}】，严格按照上述 JSON + Markdown 双代码块格式。"

        last_raw = ""
        retries = 0
        for attempt in range(2):
            try:
                response = await self._call_llm(
                    system_msg, user_msg, user_token=user_token,
                    task_type='setting',
                )
                last_raw = response
                json_match = JSON_FENCE_RE.search(response)
                md_match = MARKDOWN_FENCE_RE.search(response)
                if not json_match:
                    retries = attempt + 1
                    continue
                raw_json = json_match.group(1).strip()
                parsed = json.loads(raw_json)
                if schema_cls:
                    validated = schema_cls(**parsed).model_dump(by_alias=True)
                else:
                    validated = parsed
                content_md = (
                    md_match.group(1).strip()
                    if md_match
                    else f"# {label}\n\n{raw_json}"
                )
                return {
                    'setting_type': setting_type,
                    'title': label,
                    'content': content_md,
                    'structured_data': validated,
                    'validation_ok': True,
                    'retries': attempt,
                }
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    f"Setting generation parse failed (attempt {attempt + 1}): {e}"
                )
                retries = attempt + 1
                continue
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

        return {
            'setting_type': setting_type,
            'title': LABEL_MAP.get(setting_type, '设定'),
            'content': last_raw or '生成失败',
            'structured_data': {},
            'validation_ok': False,
            'retries': retries,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_prior_settings(prior_settings: list[dict]) -> str:
        """Build a compact bullet summary of prior settings for the LLM prompt."""
        if not prior_settings:
            return ""
        lines: list[str] = []
        for ps in prior_settings:
            st = ps.get('setting_type', '')
            sd = ps.get('structured_data') or {}
            label = LABEL_MAP.get(st, st)
            summary_parts: list[str] = []

            if st == 'worldview':
                dims = ['time_setting', 'place_setting', 'power_system', 'social_structure']
                parts = [f"{k}：{sd[k][:40]}" for k in dims if sd.get(k)]
                if parts:
                    summary_parts.append("；".join(parts[:3]))
            elif st == 'characters':
                chars = sd.get('characters', [])
                names = [c.get('name', '') for c in chars if c.get('name')]
                if names:
                    summary_parts.append(f"角色：{'、'.join(names[:6])}")
            elif st == 'map':
                regions = sd.get('regions', [])
                names = [r.get('name', '') for r in regions if r.get('name')]
                if names:
                    summary_parts.append(f"地点：{'、'.join(names[:6])}")
            elif st == 'storyline':
                premise = sd.get('premise', '')
                if premise:
                    summary_parts.append(f"前提：{premise[:80]}")
            elif st == 'plot_arc':
                acts = sd.get('acts', [])
                names = [a.get('name', '') for a in acts if a.get('name')]
                if names:
                    summary_parts.append(f"幕次：{'、'.join(names[:5])}")
            elif st == 'opening':
                hook = sd.get('hook', '')
                if hook:
                    summary_parts.append(f"钩子：{hook[:80]}")
            elif st == 'dimension_framework':
                pov = sd.get('pov_mode', '')
                if pov:
                    summary_parts.append(f"视角：{pov[:60]}")
            elif st == 'main_characters':
                chars = sd.get('characters', [])
                names = [c.get('name', '') for c in chars if c.get('name')]
                if names:
                    summary_parts.append(f"深度角色：{'、'.join(names[:5])}")
            elif st == 'map_system':
                regions = sd.get('regions', [])
                names = [r.get('name', '') for r in regions if r.get('name')]
                if names:
                    summary_parts.append(f"区域系统：{'、'.join(names[:5])}")
            elif st == 'main_sub_plots':
                theme = (sd.get('main_plot') or {}).get('theme', '')
                if theme:
                    summary_parts.append(f"主线主题：{theme[:60]}")
            elif st == 'plot_extraction':
                structure = sd.get('structure', '')
                if structure:
                    summary_parts.append(f"结构：{structure[:60]}")

            if not summary_parts:
                content = ps.get('content', '')
                if content:
                    summary_parts.append(content[:120])

            if summary_parts:
                lines.append(f"- 【{label}】{'；'.join(summary_parts)}")

        result = "\n".join(lines)
        return result[:2000]

    async def _call_llm(
        self, system_message: str, user_message: str,
        user_token: str | None = None,
        task_type: str = 'chapter',
    ) -> str:
        """Call LLM using provider manager or fallback to default settings."""
        if user_token and settings.django_api_url:
            try:
                providers = await llm_provider_manager.fetch_providers_from_django(
                    user_token, task_type=task_type
                )
                if providers:
                    return await llm_provider_manager.call_llm(
                        system_message=system_message,
                        user_message=user_message,
                        providers=providers,
                        temperature=0.8,
                        max_tokens=4096,
                    )
            except Exception as e:
                logger.warning(f'Provider manager failed, using default: {e}')

        # Fallback to default settings
        url = f"{settings.llm_api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.8,
            "max_tokens": 4096,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Mock methods
    # ------------------------------------------------------------------

    async def _mock_generate_outline(self, inspiration_id: int, genre: str, target_chapters: int):
        await asyncio.sleep(0.05)

        arc_count = max(4, min(10, target_chapters // 8 or 1))
        estimated_words = target_chapters * 2200
        chapter_each_arc = max(1, target_chapters // arc_count)

        lines = [
            f"【题材】{genre}",
            f"【灵感来源ID】{inspiration_id}",
            f"【目标章节】{target_chapters}",
            "【剧情大纲】",
        ]

        for idx in range(1, arc_count + 1):
            start_chapter = (idx - 1) * chapter_each_arc + 1
            end_chapter = (
                target_chapters if idx == arc_count else min(target_chapters, idx * chapter_each_arc)
            )
            lines.append(
                f"{idx}. 第{start_chapter}-{end_chapter}章："
                f"{genre}主线推进，主角在外部冲突与内部抉择中成长。"
            )

        return "\n".join(lines), estimated_words

    async def _mock_generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
    ):
        await asyncio.sleep(0.08)

        target_length = self._clamp(
            700 + chapter_number * 35 + len(outline_context) // 5,
            lower=700,
            upper=3200,
        )
        context_snippet = outline_context[:80] if outline_context else "主线进入关键转折阶段。"

        paragraphs = [
            f"第{chapter_number}章《{chapter_title}》",
            f"项目{project_id}的故事推进到这一刻，{context_snippet}",
        ]

        line_iter = itertools.cycle(zip(self._opening_lines, self._turning_lines, self._closing_lines))
        while self._count_words("\n".join(paragraphs)) < target_length:
            opening, turning, closing = next(line_iter)
            paragraphs.append(f"{opening}{turning}{closing}")

        content = "\n\n".join(paragraphs)
        return content, self._count_words(content)

    async def _mock_continue_content(self, current_content: str, continue_length: int):
        await asyncio.sleep(0.05)

        target_length = self._clamp(continue_length, lower=100, upper=5000)
        seed = current_content.strip()[-48:] if current_content.strip() else "故事尚未开始"

        paragraphs = [f"承接上文：{seed}"]
        line_iter = itertools.cycle(zip(self._opening_lines, self._turning_lines, self._closing_lines))
        while self._count_words("\n".join(paragraphs)) < target_length:
            opening, turning, closing = next(line_iter)
            paragraphs.append(f"{opening}{turning}{closing}")

        continued_content = "\n\n".join(paragraphs)
        return continued_content, self._count_words(continued_content)

    async def _mock_generate_inspiration(self, trending_books: list, genre_preference: str = ""):
        await asyncio.sleep(0.1)

        genres = ["都市", "玄幻", "仙侠", "科幻", "悬疑", "历史"]
        selected_genre = genre_preference if genre_preference else genres[len(trending_books) % len(genres)]

        inspirations = []
        for i in range(3):
            inspirations.append({
                "title": f"{selected_genre}之{['觉醒', '逆袭', '崛起', '传说'][i % 4]}",
                "synopsis": f"这是一个关于{selected_genre}题材的创新故事，融合了热门元素与独特设定。主角在逆境中成长，最终改变命运。",
                "genre": selected_genre,
                "selling_points": [
                    "独特的世界观设定",
                    "快节奏爽文风格",
                    "强大的主角成长线",
                    "丰富的配角群像"
                ],
                "target_audience": "18-35岁男性读者",
                "estimated_popularity": 75.0 + i * 5
            })

        return {
            "inspirations": inspirations,
            "analysis_summary": f"基于{len(trending_books)}本热门书籍分析，当前{selected_genre}题材热度较高，建议融合创新元素。"
        }

    async def _mock_generate_custom_inspiration(self, custom_prompt: str, count: int = 3):
        await asyncio.sleep(0.1)

        genres = ["都市", "玄幻", "仙侠", "科幻", "悬疑", "历史"]
        selected_genre = genres[len(custom_prompt) % len(genres)]

        inspirations = []
        for i in range(count):
            inspirations.append({
                "title": f"{selected_genre}之{['觉醒', '逆袭', '崛起', '传说', '重生'][i % 5]}",
                "synopsis": f"基于用户需求「{custom_prompt[:30]}...」创作的{selected_genre}题材故事。主角在逆境中成长，最终改变命运。",
                "genre": selected_genre,
                "selling_points": [
                    "符合用户需求的独特设定",
                    "快节奏爽文风格",
                    "强大的主角成长线",
                    "丰富的配角群像"
                ],
                "target_audience": "18-35岁读者",
                "estimated_popularity": 70.0 + i * 5
            })

        return {
            "inspirations": inspirations,
            "analysis_summary": f"基于用户自定义需求生成了{count}个{selected_genre}题材创意。"
        }

    async def _mock_generate_setting(
        self,
        setting_type: str,
        book_title: str,
        genre: str = "",
        context: str = "",
        prior_settings: list[dict] | None = None,
    ) -> dict:
        """Return structured mock data for all 11 setting types."""
        await asyncio.sleep(0.08)

        genre_display = genre or '玄幻'
        label = LABEL_MAP.get(setting_type, setting_type)

        # Build structured_data and content for every type
        if setting_type == 'worldview':
            structured_data = {
                "time_setting": "架空远古纪元，距今约万年。人族刚从蒙昧走向文明，修行体系初立，天地灵气充沛。",
                "place_setting": "大陆分为东胜、西极、南荒、北漠、中州五大版图。中州为修行界核心，九大宗门环列；北漠冰寒荒芜；南荒原始密林。",
                "social_structure": "世俗王朝与修行门派并立。帝都掌世俗权力，九大宗门统御修行界。修士地位高于凡人，阶级分明。",
                "cultural_background": "修行文化渗透日常：祭天问道是最高仪式，每年万灵大会为各宗门交流盛事。语言以通用古语为主，各域方言并存。",
                "tech_level": "类中古世界，修行替代科技。符阵代替机械，传音玉简替代通讯工具，飞剑和传送阵为主要交通方式。",
                "power_system": "灵气修行体系：吸纳天地灵气入体，修行分九境（筑基→凝神→铸魂→通玄→化虚→合道→破劫→飞升→证道），每境突破伴天地异象。",
                "history": "万年前仙神之战后，上古仙人飞升或陨落。五千年前九大宗门建立，奠定当今格局。近百年魔道抬头，暗流涌动。",
                "natural_laws": "灵气为世界运转根基，可被修行者引导但不可创造。天劫是突破高境的天道考验，日月交替受灵气潮汐影响。",
            }
            content = (
                f"# 世界观\n\n"
                f"## 时间设定\n架空远古纪元，修行体系初立，天地灵气充沛。\n\n"
                f"## 地点设定\n大陆分五大版图，中州为修行界核心。\n\n"
                f"## 社会结构\n世俗王朝与修行门派并立，九大宗门统御修行界。\n\n"
                f"## 文化背景\n修行文化渗透日常，万灵大会为最高盛事。\n\n"
                f"## 科技水平\n类中古世界，符阵与飞剑替代科技。\n\n"
                f"## 力量体系\n灵气修行分九境，每境突破伴天地异象。\n\n"
                f"## 历史背景\n万年前仙神之战，五千年前九大宗门建立。\n\n"
                f"## 自然法则\n灵气为根基，天劫为天道考验。"
            )

        elif setting_type == 'characters':
            structured_data = {
                "characters": [
                    {"name": "林渊", "role": "主角", "alignment": "正", "brief": "北漠寒村少年，天生下品灵根却获上古传承", "origin": "北漠落霞村"},
                    {"name": "苏清霜", "role": "女主", "alignment": "正", "brief": "中州名门之女，天资卓绝", "origin": "中州苏家"},
                    {"name": "玄真子", "role": "导师", "alignment": "正", "brief": "隐世高人，主角的引路之师", "origin": "九大宗门长老"},
                    {"name": "周铁柱", "role": "配角", "alignment": "正", "brief": "主角同村兄弟，忠义无双", "origin": "北漠落霞村"},
                    {"name": "血影老祖", "role": "反派", "alignment": "邪", "brief": "魔道巨擘，觊觎主角传承", "origin": "魔道"},
                ]
            }
            content = (
                f"# 人物设定\n\n"
                f"主角林渊出身北漠寒村，获上古传承；"
                f"女主苏清霜为中州名门之女；导师玄真子为隐世高人；"
                f"挚友周铁柱忠义无双；反派血影老祖为魔道巨擘。"
            )

        elif setting_type == 'map':
            structured_data = {
                "regions": [
                    {"name": "落霞村", "type": "村庄", "description": "北漠边陲寒冷小村，主角出身地", "connected_to": ["断魂崖", "北漠荒原"]},
                    {"name": "断魂崖", "type": "秘境", "description": "主角获得传承之处", "connected_to": ["落霞村"]},
                    {"name": "青云宗", "type": "宗门", "description": "九大宗门之一，云海之上", "connected_to": ["中州帝都"]},
                    {"name": "万妖林", "type": "森林", "description": "南荒深处原始密林，妖兽横行", "connected_to": ["南荒边境"]},
                    {"name": "中州帝都", "type": "城市", "description": "权力中心，风云际会之所", "connected_to": ["青云宗", "黄沙古墟"]},
                    {"name": "黄沙古墟", "type": "遗迹", "description": "西极黄沙之下的上古战场", "connected_to": ["中州帝都"]},
                ]
            }
            content = (
                f"# 地图与场景\n\n"
                f"故事从落霞村出发，经断魂崖、青云宗、万妖林、中州帝都，"
                f"最终抵达黄沙古墟。各地相互连通，构成完整冒险路线。"
            )

        elif setting_type == 'storyline':
            structured_data = {
                "premise": "北漠少年获上古传承，踏上修行之路，追寻身世真相与仙神之战的秘密",
                "central_conflict": "主角与幕后势力围绕上古传承和天道重构的对抗",
                "themes": ["逆天崛起", "命运选择", "天道本质"],
                "stakes": "若失败，天道重构将抹杀现世一切生灵",
            }
            content = (
                f"# 故事线\n\n"
                f"北漠少年获传承后踏上修行路，核心冲突在于"
                f"对抗企图重构天道的幕后势力，赌注是现世苍生的存亡。"
            )

        elif setting_type == 'plot_arc':
            structured_data = {
                "acts": [
                    {"name": "起·觉醒", "description": "平凡少年获传承，初入修行界", "key_events": ["断魂崖奇遇", "入青云宗"]},
                    {"name": "承·成长", "description": "历练磨砺，实力提升，铺设伏笔", "key_events": ["万妖林苦修", "初遇血影老祖"]},
                    {"name": "转·真相", "description": "秘辛揭露，世界观颠覆", "key_events": ["古墟之行", "师父坦白", "主角身世"]},
                    {"name": "合·决战", "description": "终极对决，因果回收", "key_events": ["九天云海之战", "证道抉择"]},
                ],
                "climax": "九天云海终极之战，所有伏笔收束",
                "resolution": "主角证道成仙，留下开放性余韵",
            }
            content = (
                f"# 情节弧\n\n"
                f"起承转合四幕：从觉醒、成长、真相到决战，"
                f"高潮在九天云海，结局证道成仙。"
            )

        elif setting_type == 'opening':
            structured_data = {
                "scene": "北漠落霞村黎明前，断魂崖冰裂，青光冲天",
                "hook": "少年林渊梦中反复听到神秘声音，断魂崖突然异变",
                "pov_character": "林渊",
                "first_chapter_goal": "建立主角形象，抛出传承悬念，让读者迅速沉浸",
                "tone": "冷峻、神秘、带有宿命感",
            }
            content = (
                f"# 开篇场景\n\n"
                f"黎明前的落霞村，少年林渊在断魂崖的青光中踏出命运的第一步。"
                f"冷峻神秘的基调，悬念钩子：那道反复在梦中出现的苍老声音。"
            )

        elif setting_type == 'dimension_framework':
            structured_data = {
                "timeline_structure": "双时间线：现世修行线 + 万年前仙神之战远古线",
                "pov_mode": "第三人称有限视角为主（70%），穿插反派视角（15%）与群像视角（15%）",
                "pov_characters": ["林渊", "血影老祖", "苏清霜"],
                "time_jumps": [
                    {"from": "现世", "to": "远古仙神之战", "purpose": "通过传承记忆揭示历史真相"},
                ],
                "narrative_devices": ["梦境闪回", "遗迹幻象", "传承记忆", "信息差悬念"],
            }
            content = (
                f"# 维度框架\n\n"
                f"双时间线结构，以林渊第三人称有限视角为主，"
                f"穿插反派与群像视角。通过梦境、遗迹幻象实现时间跳转。"
            )

        elif setting_type == 'main_characters':
            structured_data = {
                "characters": [
                    {
                        "name": "林渊",
                        "motivation": "追寻父亲失踪真相，揭开传承秘密",
                        "inner_conflict": "渴望力量却恐惧失控",
                        "growth_arc": "自卑隐忍→锋芒初露→背负使命→学会信任",
                        "backstory": "北漠寒村少年，父亲在断魂崖失踪",
                        "relationships": [
                            {"target": "玄真子", "type": "师徒", "dynamic": "亦师亦父"},
                            {"target": "苏清霜", "type": "情侣", "dynamic": "从冷眼到生死与共"},
                        ],
                    },
                    {
                        "name": "苏清霜",
                        "motivation": "摆脱家族联姻，以实力证明自身",
                        "inner_conflict": "家族责任与个人自由的撕裂",
                        "growth_arc": "冷傲疏离→信任萌芽→并肩作战→打破桎梏",
                        "backstory": "中州名门之女，天资卓绝",
                        "relationships": [
                            {"target": "林渊", "type": "情侣", "dynamic": "从不屑到生死相依"},
                        ],
                    },
                ]
            }
            content = (
                f"# 主要角色\n\n"
                f"林渊：追寻真相，从自卑到担当；"
                f"苏清霜：挣脱命运，从冷傲到并肩。二人关系从冷眼到生死与共。"
            )

        elif setting_type == 'map_system':
            structured_data = {
                "regions": [
                    {
                        "name": "中州",
                        "factions": [
                            {"name": "九大宗门", "influence": "修行界主导力量", "base": "中州"},
                            {"name": "凡人帝都", "influence": "世俗政权中心", "base": "中州"},
                        ],
                        "routes": ["中州↔东胜海运线", "中州↔北漠陆运线"],
                        "resources": ["灵石矿脉", "丹药材料"],
                        "significance": "修行界政治经济中心",
                    },
                    {
                        "name": "北漠",
                        "factions": [
                            {"name": "游牧部族联盟", "influence": "北漠主导势力", "base": "北漠"},
                        ],
                        "routes": ["北漠↔中州陆运线"],
                        "resources": ["上古冰系遗宝"],
                        "significance": "主角起源地，断魂崖所在",
                    },
                ]
            }
            content = (
                f"# 地图系统\n\n"
                f"中州为政治经济中心，九大宗门与帝都并立；"
                f"北漠为主角起源地，游牧部族联盟主导。"
            )

        elif setting_type == 'main_sub_plots':
            structured_data = {
                "main_plot": {
                    "theme": "追寻传承真相，对抗天道重构",
                    "events": [
                        {"chapter_range": "1-30", "event": "传承觉醒，踏上修行路", "characters": ["林渊"]},
                        {"chapter_range": "31-150", "event": "入宗历练，实力提升", "characters": ["林渊", "苏清霜", "周铁柱"]},
                        {"chapter_range": "151-350", "event": "揭示真相，风云际会", "characters": ["林渊", "玄真子"]},
                        {"chapter_range": "351-500", "event": "终极对决，证道飞升", "characters": ["林渊", "苏清霜"]},
                    ],
                },
                "sub_plots": [
                    {
                        "name": "红颜劫",
                        "characters": ["林渊", "苏清霜"],
                        "events": [
                            {"chapter_range": "40-250", "event": "从冷眼到同生共死", "characters": ["林渊", "苏清霜"]},
                        ],
                        "crosses_main": "苏家阴谋与仙神之战旧事相关",
                    },
                    {
                        "name": "师父的秘密",
                        "characters": ["玄真子", "林渊"],
                        "events": [
                            {"chapter_range": "100-360", "event": "逐步揭露师父过去", "characters": ["玄真子"]},
                        ],
                        "crosses_main": "师父秘密关系传承本质和终极反派身份",
                    },
                ],
            }
            content = (
                f"# 主线与支线\n\n"
                f"主线：追寻传承真相，对抗天道重构。"
                f"支线：红颜劫（感情线）、师父的秘密（伏笔线）。"
            )

        elif setting_type == 'plot_extraction':
            structured_data = {
                "structure": "三幕式结构",
                "acts": [
                    {"name": "第一幕·建置", "span": "1-150", "summary": "建立世界观、引入角色、完成第一次大转折", "turning_point": "南荒历练惨胜"},
                    {"name": "第二幕·对抗", "span": "151-380", "summary": "升级冲突、揭示真相、逼近抉择", "turning_point": "古墟真相曝光"},
                    {"name": "第三幕·解决", "span": "381-500", "summary": "收束线索、终极决战", "turning_point": "九天云海之战"},
                ],
                "key_turns": [
                    {"chapter": 5, "type": "命运转折", "description": "断魂崖传承觉醒"},
                    {"chapter": 145, "type": "认知转折", "description": "认识到力量的代价"},
                    {"chapter": 250, "type": "世界观颠覆", "description": "古墟揭示仙神之战真相"},
                    {"chapter": 360, "type": "情感核弹", "description": "师父牺牲"},
                    {"chapter": 480, "type": "主题升华", "description": "九天抉择"},
                ],
                "pacing": "慢→快→爆发→喘息→急促→爆发→缓落",
                "theme_distillation": "命运非天定，天道非绝对，逆天者未必是叛逆而是觉醒",
            }
            content = (
                f"# 剧情抽离\n\n"
                f"三幕式结构：建置→对抗→解决。五大转折点贯穿全书，"
                f"节奏从慢到快再到爆发。主题：命运非天定，天道非绝对。"
            )

        else:
            structured_data = {}
            content = f"# {label}\n\n未知的设定类型。"

        return {
            'setting_type': setting_type,
            'title': label,
            'content': content,
            'structured_data': structured_data,
            'validation_ok': True,
            'retries': 0,
        }

    async def _mock_generate_setting_stream(
        self,
        setting_type: str,
        book_title: str,
        genre: str = "",
        context: str = "",
        prior_settings: list[dict] | None = None,
    ):
        """Mock streaming: yield the mock content character by character."""
        result = await self._mock_generate_setting(
            setting_type, book_title, genre, context, prior_settings,
        )
        # Simulate streaming by yielding small chunks
        full_text = result['content']
        chunk_size = 4
        for i in range(0, len(full_text), chunk_size):
            chunk = full_text[i:i + chunk_size]
            yield ("chunk", chunk)
            await asyncio.sleep(0.03)

        yield ("done", result)

    @staticmethod
    def _count_words(content: str) -> int:
        return len(NON_WHITESPACE_PATTERN.findall(content or ""))

    @staticmethod
    def _clamp(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, int(value)))


llm_client = LLMClient()
