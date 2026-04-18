import asyncio
import itertools
import json
import logging
import re
from typing import Optional

import httpx

from config import settings
from services.llm_provider_manager import llm_provider_manager
from services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

NON_WHITESPACE_PATTERN = re.compile(r"\S")
JSON_FENCE_RE = re.compile(r'```json\s*\n(.*?)\n\s*```', re.DOTALL)
MARKDOWN_FENCE_RE = re.compile(r'```markdown\s*\n(.*?)\n\s*```', re.DOTALL)

# ------------------------------------------------------------------ #
# System prompts for 6 setting types
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
}

LABEL_MAP = {
    'worldview': '世界观',
    'characters': '人物设定',
    'map': '地图与场景',
    'storyline': '故事线',
    'plot_arc': '情节弧',
    'opening': '开篇场景',
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
        context_payload: dict | None = None,
        user_token: str | None = None,
    ):
        if await self._should_use_mock(user_token):
            return await self._mock_generate_chapter(
                project_id, chapter_number, chapter_title, outline_context, context_payload
            )
        return await self._real_generate_chapter(
            project_id, chapter_number, chapter_title, outline_context,
            context_payload=context_payload,
            user_token=user_token,
        )

    async def generate_chapter_stream(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
        context_payload: dict | None = None,
        user_token: str | None = None,
    ):
        """Async generator yielding (type, data) tuples for chapter streaming.

        Yields:
            ("status", message_str)
            ("chunk", delta_text)
            ("done", {"content": str, "word_count": int})
        """
        use_mock = await self._should_use_mock(user_token)

        if use_mock:
            async for item in self._mock_generate_chapter_stream(
                project_id, chapter_number, chapter_title, outline_context, context_payload
            ):
                yield item
            return

        # Real LLM path — use call_llm_stream
        providers = []
        try:
            providers = await llm_provider_manager.fetch_providers_from_django(
                user_token, task_type='chapter'
            )
        except Exception:
            pass

        if not providers:
            async for item in self._mock_generate_chapter_stream(
                project_id, chapter_number, chapter_title, outline_context, context_payload
            ):
                yield item
            return

        user_msg = PromptBuilder.build_chapter_context_prompt(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            context_payload=context_payload,
            outline_context=outline_context,
        )

        full_text = ""
        try:
            async for delta in llm_provider_manager.call_llm_stream(
                system_message=self.SYSTEM_CHAPTER,
                user_message=user_msg,
                providers=providers,
            ):
                if delta == '\x00THINKING\x00':
                    continue
                full_text += delta
                yield ("chunk", delta)
        except Exception as e:
            logger.warning(f"[chapter_stream] Real LLM failed: {e}, falling back to mock")
            if not full_text:
                async for item in self._mock_generate_chapter_stream(
                    project_id, chapter_number, chapter_title, outline_context, context_payload
                ):
                    yield item
                return

        yield ("done", {"content": full_text, "word_count": self._count_words(full_text)})

    async def _mock_generate_chapter_stream(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
        context_payload: dict | None = None,
    ):
        """Mock streaming chapter generation — yields chunks then done."""
        content, word_count = await self._mock_generate_chapter(
            project_id, chapter_number, chapter_title, outline_context, context_payload
        )
        chunk_size = 8
        for i in range(0, len(content), chunk_size):
            yield ("chunk", content[i:i + chunk_size])
            await asyncio.sleep(0.04)
        yield ("done", {"content": content, "word_count": word_count})

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
        thinking_sent = False
        try:
            logger.info(f"Streaming from provider: {providers[0].get('name', '?')}")
            async for delta in llm_provider_manager.call_llm_stream(
                system_message=system_msg,
                user_message=user_msg,
                providers=providers,
            ):
                # Sentinel from reasoning models — notify client once
                if delta == '\x00THINKING\x00':
                    if not thinking_sent:
                        thinking_sent = True
                        yield ("thinking", "AI 正在深度思考中...")
                    continue
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
        context_payload: dict | None = None,
        user_token: str | None = None,
    ):
        user_msg = PromptBuilder.build_chapter_context_prompt(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            context_payload=context_payload,
            outline_context=outline_context,
        )
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
        context_payload: dict | None = None,
    ):
        await asyncio.sleep(0.08)

        target_length = self._clamp(
            700 + chapter_number * 35 + len(outline_context) // 5,
            lower=700,
            upper=3200,
        )
        payload = context_payload or {}
        chapter_goal = (payload.get('chapter_goal') or '').strip()
        context_snippet = chapter_goal[:80] if chapter_goal else (
            outline_context[:80] if outline_context else "主线进入关键转折阶段。"
        )
        style_hint = (payload.get('style_profile') or {}).get('content', '')
        focus_card = payload.get('focus_card') or {}
        micro_beats = payload.get('micro_beats') or []
        must_payoff = (focus_card.get('must_payoff') or [])[:2]

        paragraphs = [
            f"第{chapter_number}章《{chapter_title}》",
            f"项目{project_id}的故事推进到这一刻，{context_snippet}",
            f"文风约束：{style_hint[:48] or '保持悬念推进与角色一致性。'}",
        ]
        if focus_card.get('mission'):
            paragraphs.append(f"本章任务是：{focus_card['mission']}")
        if focus_card.get('conflict'):
            paragraphs.append(f"角色此刻面临的核心冲突是：{focus_card['conflict']}")
        if must_payoff:
            paragraphs.append(f"本章必须触碰的旧线索包括：{'、'.join(must_payoff)}。")

        for beat in micro_beats[:4]:
            paragraphs.append(
                f"{beat.get('label', '节拍')}：{beat.get('objective', '')}"
                f" 本段重点放在{beat.get('focus', 'scene')}，"
                f"目标篇幅约{beat.get('target_words', 600)}字。"
            )

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
        """Return structured mock data for all 6 setting types."""
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

    async def analyze_chapter_summary(
        self,
        project_id: int,
        chapter_number: int,
        content: str,
        context_payload: dict | None = None,
    ) -> dict:
        sentences = self._split_sentences(content)
        summary_parts: list[str] = []
        for sentence in sentences:
            if sum(len(item) for item in summary_parts) + len(sentence) > 220 and summary_parts:
                break
            summary_parts.append(sentence)
        open_threads = [sentence[:180] for sentence in sentences if '？' in sentence or '?' in sentence][:5]
        return {
            'summary': ''.join(summary_parts)[:240],
            'key_events': [sentence[:180] for sentence in sentences[:3]],
            'open_threads': open_threads,
        }

    async def analyze_facts(
        self,
        project_id: int,
        chapter_number: int,
        content: str,
        context_payload: dict | None = None,
    ) -> dict:
        facts = []
        for item in (context_payload or {}).get('knowledge_facts', [])[:8]:
            subject = item.get('subject') or ''
            if subject and subject in content:
                facts.append({
                    'subject': subject,
                    'predicate': item.get('predicate') or '关联事实',
                    'object': item.get('object') or f'第{chapter_number}章涉及',
                    'source_excerpt': next((sentence[:220] for sentence in self._split_sentences(content) if subject in sentence), ''),
                    'confidence': 0.78,
                })
        if not facts:
            for sentence in self._split_sentences(content)[:3]:
                facts.append({
                    'subject': f'第{chapter_number}章',
                    'predicate': '关键事件',
                    'object': sentence[:60],
                    'source_excerpt': sentence[:220],
                    'confidence': 0.66,
                })
        return {'facts': facts[:8]}

    async def analyze_style_drift(
        self,
        project_id: int,
        chapter_number: int,
        content: str,
        context_payload: dict | None = None,
    ) -> dict:
        sentences = self._split_sentences(content)
        average_sentence_length = round(sum(len(sentence) for sentence in sentences) / max(len(sentences), 1))
        exclamations = content.count('！') + content.count('!')
        risk_level = 'low'
        reasons = []
        if average_sentence_length < 18:
            risk_level = 'medium'
            reasons.append('句子偏短，节奏较急')
        if exclamations > max(2, len(sentences) // 2):
            risk_level = 'high'
            reasons.append('感叹号密度偏高，可能影响文风稳定性')
        tone = (((context_payload or {}).get('style_profile') or {}).get('structured_data') or {}).get('tone')
        if tone:
            reasons.append(f'基线基调：{tone}')
        score = 90 if risk_level == 'low' else 72 if risk_level == 'medium' else 55
        return {
            'score': score,
            'risk_level': risk_level,
            'reasons': reasons,
            'suggestions': ['保留核心语气，但适度拉开句长层次', '强化环境与动作描写，减少单一情绪堆叠'],
        }

    async def analyze_consistency(
        self,
        project_id: int,
        chapter_number: int,
        content: str,
        context_payload: dict | None = None,
    ) -> dict:
        conflicts = []
        risks = []
        for fact in (context_payload or {}).get('knowledge_facts', [])[:6]:
            subject = fact.get('subject') or ''
            if subject and subject not in content:
                risks.append(f'未触达关键实体：{subject}')
        if len(content) < 800:
            risks.append('章节篇幅偏短，信息可能不足')
        suggestions = ['发布前人工核查角色状态与地点连续性']
        if not (context_payload or {}).get('recent_summaries'):
            suggestions.append('补充最近章节摘要后再继续增强上下文')
        return {
            'status': 'warning' if risks or conflicts else 'ok',
            'conflicts': conflicts,
            'risks': risks[:6],
            'suggestions': suggestions[:4],
        }

    @staticmethod
    def _count_words(content: str) -> int:
        return len(NON_WHITESPACE_PATTERN.findall(content or ""))

    @staticmethod
    def _clamp(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, int(value)))

    @staticmethod
    def _split_sentences(content: str) -> list[str]:
        return [part.strip() for part in re.split(r'(?<=[。！？?!])', content or '') if part.strip()]


llm_client = LLMClient()
