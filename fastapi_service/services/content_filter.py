import re

class ContentFilter:
    SENSITIVE_WORDS = ["暴力", "色情", "违禁"]

    @staticmethod
    def count_words(content: str) -> int:
        """Count non-whitespace characters."""
        if not content:
            return 0
        return len(re.findall(r'\S', content))

    @staticmethod
    def filter_sensitive_words(content: str) -> str:
        """Replace sensitive words with ***."""
        filtered_content = content
        for word in ContentFilter.SENSITIVE_WORDS:
            filtered_content = filtered_content.replace(word, "***")
        return filtered_content

    @staticmethod
    def format_content(content: str) -> str:
        """Basic formatting like stripping extra newlines."""
        # Replace 3 or more newlines with 2 newlines
        formatted = re.sub(r'\n{3,}', '\n\n', content)
        return formatted.strip()

    @staticmethod
    def process(content: str) -> str:
        filtered = ContentFilter.filter_sensitive_words(content)
        formatted = ContentFilter.format_content(filtered)
        return formatted
