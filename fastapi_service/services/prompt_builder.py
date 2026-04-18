import os
from typing import Any

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')

class PromptBuilder:
    @staticmethod
    def _load_template(filename: str) -> str:
        filepath = os.path.join(PROMPTS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def build_outline_prompt(genre: str, target_chapters: int, user_preferences: str = "") -> str:
        template = PromptBuilder._load_template('outline_template.txt')
        return template.format(
            genre=genre,
            target_chapters=target_chapters,
            user_preferences=user_preferences or "None"
        )

    @staticmethod
    def build_chapter_prompt(chapter_number: int, chapter_title: str, outline_context: str, previous_content: str = "") -> str:
        template = PromptBuilder._load_template('chapter_template.txt')
        return template.format(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            outline_context=outline_context,
            previous_content=previous_content or "None"
        )

    @staticmethod
    def _bullet_block(title: str, items: list[str]) -> str:
        rows = [f"- {item}" for item in items if str(item or "").strip()]
        if not rows:
            return ""
        return f"{title}：\n" + "\n".join(rows)

    @staticmethod
    def build_chapter_context_prompt(
        chapter_number: int,
        chapter_title: str,
        context_payload: dict[str, Any] | None = None,
        outline_context: str = "",
    ) -> str:
        context_payload = context_payload or {}
        project = context_payload.get('project') or {}
        chapter_goal = context_payload.get('chapter_goal') or ''
        focus_card = context_payload.get('focus_card') or {}
        context_layers = context_payload.get('context_layers') or {}
        micro_beats = context_payload.get('micro_beats') or []
        continuity_alerts = context_payload.get('continuity_alerts') or []
        style_profile = context_payload.get('style_profile') or {}
        style_content = style_profile.get('content') or ''
        style_structured = style_profile.get('structured_data') or {}

        sections: list[str] = []

        sections.append("\n".join([
            "【项目卡】",
            f"书名：{project.get('title') or '未命名项目'}",
            f"题材：{project.get('genre') or '未指定'}",
            f"章节：第{chapter_number}章《{chapter_title}》",
            *( [f"项目简介：{project['synopsis']}"] if project.get('synopsis') else [] ),
            *( [f"补充大纲：{outline_context}"] if outline_context else [] ),
        ]))

        sections.append("\n".join([
            "【章节任务卡】",
            f"- 主任务：{focus_card.get('mission') or chapter_goal or '围绕当前主线推进章节内容。'}",
            f"- 核心冲突：{focus_card.get('conflict') or '让角色在推进目标时遭遇明确阻力。'}",
            f"- 关键转折：{focus_card.get('key_turn') or chapter_goal or '在中后段给出足以改变后续行动的转折。'}",
            f"- 情绪提示：{focus_card.get('emotional_note') or '情绪必须贴着动作和对话走。'}",
            f"- 收尾钩子：{focus_card.get('ending_hook') or '结尾要把下一步问题明确抛出。'}",
        ]))

        sections.extend([
            PromptBuilder._bullet_block("【基础层】", list(context_layers.get('foundation') or [])),
            PromptBuilder._bullet_block("【连续层】", list(context_layers.get('continuity') or [])),
            PromptBuilder._bullet_block("【战术层】", list(context_layers.get('tactical') or [])),
        ])

        if micro_beats:
            beat_lines = [
                (
                    f"{item.get('index')}. {item.get('label')} "
                    f"({item.get('focus')} / {item.get('target_words')}字)："
                    f"{item.get('objective')}"
                )
                for item in micro_beats[:5]
            ]
            sections.append("【微节拍】\n" + "\n".join(beat_lines))

        selected_settings = context_payload.get('selected_settings') or []
        if selected_settings:
            sections.append(PromptBuilder._bullet_block(
                "【高相关设定】",
                [
                    f"[{item.get('setting_type')}] {item.get('title')}: {item.get('content')}"
                    for item in selected_settings[:6]
                ],
            ))

        storylines = context_payload.get('storylines') or []
        if storylines:
            sections.append(PromptBuilder._bullet_block(
                "【当前故事线】",
                [
                    f"{item.get('name')}（{item.get('status')}）: {item.get('description')}"
                    for item in storylines[:4]
                ],
            ))

        plot_points = context_payload.get('plot_points') or []
        if plot_points:
            sections.append(PromptBuilder._bullet_block(
                "【临近情节点】",
                [
                    f"章节{item.get('chapter_number')} {item.get('point_type')}: {item.get('description')}"
                    for item in plot_points[:5]
                ],
            ))

        knowledge_facts = context_payload.get('knowledge_facts') or []
        if knowledge_facts:
            sections.append(PromptBuilder._bullet_block(
                "【稳定事实】",
                [
                    f"{item.get('subject')} {item.get('predicate')} {item.get('object')}"
                    for item in knowledge_facts[:8]
                ],
            ))

        foreshadow_items = context_payload.get('foreshadow_items') or []
        if foreshadow_items:
            sections.append(PromptBuilder._bullet_block(
                "【伏笔账本】",
                [
                    f"{item.get('title')}（{item.get('status')}，回收章 {item.get('expected_payoff_chapter')}）: {item.get('description')}"
                    for item in foreshadow_items[:6]
                ],
            ))

        if continuity_alerts:
            sections.append(PromptBuilder._bullet_block(
                "【连续性警报】",
                [
                    f"[{item.get('level')}] {item.get('title')}: {item.get('detail')}"
                    for item in continuity_alerts[:5]
                ],
            ))

        recent_summaries = context_payload.get('recent_summaries') or []
        if recent_summaries:
            sections.append(PromptBuilder._bullet_block(
                "【最近章节摘要】",
                [
                    f"第{item.get('chapter_number')}章：{item.get('summary')}"
                    for item in recent_summaries[:5]
                ],
            ))

        style_lines = [
            style_content,
            f"tone={style_structured.get('tone', '')}" if style_structured.get('tone') else "",
            (
                f"themes={style_structured.get('themes', [])}"
                if style_structured.get('themes')
                else ""
            ),
        ]
        sections.append(PromptBuilder._bullet_block("【风格约束】", [line for line in style_lines if line]))

        sections.append("\n".join([
            "【硬性写作规则】",
            "- 只输出正文，不要输出标题、说明、提纲、分析、标签或自我解释。",
            "- 严格延续既有设定与稳定事实，禁止凭空改写人物关系、能力、地点规则和已发生事件。",
            "- 节奏遵循任务卡与微节拍，每个节拍必须落到可见动作、对话、心理反应或环境细节。",
            "- 不要用大段总结替代场景推进，不要把冲突轻易化解。",
            "- 如果埋新伏笔，必须与已有主线、开放线索或当前冲突直接相关。",
        ]))

        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def build_continue_prompt(current_content: str, continue_length: int) -> str:
        template = PromptBuilder._load_template('continue_template.txt')
        return template.format(
            current_content=current_content,
            continue_length=continue_length
        )
