import os

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
    def build_continue_prompt(current_content: str, continue_length: int) -> str:
        template = PromptBuilder._load_template('continue_template.txt')
        return template.format(
            current_content=current_content,
            continue_length=continue_length
        )
