import asyncio
import itertools
import json
import re

import httpx

from config import settings

NON_WHITESPACE_PATTERN = re.compile(r"\S")


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

    def __init__(self):
        self._use_mock = settings.mock_generation or not settings.llm_api_key

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
    # Public API methods
    # ------------------------------------------------------------------

    async def generate_outline(self, inspiration_id: int, genre: str, target_chapters: int):
        if self._use_mock:
            return await self._mock_generate_outline(inspiration_id, genre, target_chapters)
        return await self._real_generate_outline(inspiration_id, genre, target_chapters)

    async def generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
    ):
        if self._use_mock:
            return await self._mock_generate_chapter(
                project_id, chapter_number, chapter_title, outline_context
            )
        return await self._real_generate_chapter(
            project_id, chapter_number, chapter_title, outline_context
        )

    async def continue_content(self, current_content: str, continue_length: int):
        if self._use_mock:
            return await self._mock_continue_content(current_content, continue_length)
        return await self._real_continue_content(current_content, continue_length)

    # ------------------------------------------------------------------
    # Real LLM methods
    # ------------------------------------------------------------------

    async def _real_generate_outline(self, inspiration_id: int, genre: str, target_chapters: int):
        user_msg = (
            f"请为以下题材生成小说大纲：\n"
            f"题材：{genre}\n"
            f"灵感来源ID：{inspiration_id}\n"
            f"目标章节数：{target_chapters}\n"
            f"请按章节给出剧情大纲，标注每段剧情的核心冲突与主角成长线。"
        )
        content = await self._call_llm(self.SYSTEM_OUTLINE, user_msg)
        estimated_words = target_chapters * 2200
        return content, estimated_words

    async def _real_generate_chapter(
        self,
        project_id: int,
        chapter_number: int,
        chapter_title: str,
        outline_context: str = "",
    ):
        user_msg = (
            f"项目ID: {project_id}\n"
            f"章节：第{chapter_number}章《{chapter_title}》\n"
        )
        if outline_context:
            user_msg += f"大纲参考：{outline_context}\n"
        user_msg += "请写出该章节的正文内容。"
        content = await self._call_llm(self.SYSTEM_CHAPTER, user_msg)
        return content, self._count_words(content)

    async def _real_continue_content(self, current_content: str, continue_length: int):
        user_msg = (
            f"请续写以下故事内容，目标长度约 {continue_length} 个汉字：\n\n"
            f"{current_content[-1200:] if len(current_content) > 1200 else current_content}"
        )
        content = await self._call_llm(self.SYSTEM_CONTINUE, user_msg)
        return content, self._count_words(content)

    async def _call_llm(self, system_message: str, user_message: str) -> str:
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

    @staticmethod
    def _count_words(content: str) -> int:
        return len(NON_WHITESPACE_PATTERN.findall(content or ""))

    @staticmethod
    def _clamp(value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, int(value)))


llm_client = LLMClient()
