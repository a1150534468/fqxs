import json
import re
from typing import Dict, Iterable, List
from urllib.parse import urljoin

import scrapy

from tomato_spider.items import TomatoRankItem

SPECIAL_CHAR_PATTERN = re.compile(r'[\u0000-\u001f\u007f-\u009f\ue000-\uf8ff]')
SPACE_PATTERN = re.compile(r'\s+')
TAG_SPLIT_PATTERN = re.compile(r'[,|/、]')


class TomatoRankSpider(scrapy.Spider):
    name = 'tomato_rank'
    allowed_domains = ['fanqienovel.com']
    handle_httpstatus_list = [403, 404, 429]

    def __init__(self, limit='5', rank_types='hot,new,rising', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit = max(int(limit), 1)
        self.rank_types = [part.strip() for part in rank_types.split(',') if part.strip()]
        if not self.rank_types:
            self.rank_types = ['hot']

    def start_requests(self) -> Iterable[scrapy.Request]:
        settings = self.crawler.settings
        proxy_list = settings.getlist('PROXY_LIST')
        strict_proxy_enabled = settings.getbool('STRICT_PROXY_ENABLED', True)

        if strict_proxy_enabled and not proxy_list:
            raise RuntimeError(
                'strict_proxy_enabled=True but proxy list is empty. Configure SCRAPY_PROXY_LIST.'
            )

        rank_url_map: Dict[str, str] = settings.getdict('RANK_URL_MAP')

        for rank_type in self.rank_types:
            rank_url = rank_url_map.get(rank_type)
            if not rank_url:
                self.logger.warning('No URL configured for rank_type=%s. Skipping.', rank_type)
                continue

            yield scrapy.Request(
                url=rank_url,
                callback=self.parse,
                dont_filter=True,
                meta={'rank_type': rank_type},
            )

    def _clean_text(self, value: str) -> str:
        if value is None:
            return ''
        if not isinstance(value, str):
            value = str(value)

        value = SPECIAL_CHAR_PATTERN.sub('', value)
        value = SPACE_PATTERN.sub(' ', value).strip()
        return value

    def _clean_tags(self, raw_tags: List[str]) -> List[str]:
        tags: List[str] = []
        for raw_tag in raw_tags:
            cleaned = self._clean_text(raw_tag)
            if not cleaned:
                continue
            for part in TAG_SPLIT_PATTERN.split(cleaned):
                normalized = self._clean_text(part)
                if normalized and normalized not in tags:
                    tags.append(normalized)
        return tags

    def _to_hot_score(self, book: dict) -> float:
        candidate_fields = ('read_count', 'readCount', 'hot_score', 'currentPos')
        for field in candidate_fields:
            value = book.get(field)
            if value is None:
                continue
            value_str = self._clean_text(str(value)).replace(',', '')
            try:
                return round(float(value_str), 2)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _extract_initial_state(self, html: str) -> dict:
        marker = 'window.__INITIAL_STATE__='
        marker_index = html.find(marker)
        if marker_index < 0:
            return {}

        start_index = html.find('{', marker_index)
        if start_index < 0:
            return {}

        depth = 0
        in_string = False
        escape = False
        end_index = None

        for index in range(start_index, len(html)):
            char = html[index]

            if in_string:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end_index = index + 1
                    break

        if end_index is None:
            return {}

        raw_json = html[start_index:end_index]
        sanitized_json = raw_json.replace(':undefined', ':null')

        try:
            return json.loads(sanitized_json)
        except json.JSONDecodeError as exc:
            self.logger.warning('Failed to parse initial state JSON: %s', exc)
            return {}

    def parse(self, response):
        rank_type = response.meta.get('rank_type', 'hot')
        if response.status in {403, 404, 429}:
            if not response.meta.get('fallback_used'):
                self.logger.warning(
                    'Received %s for %s, retrying fallback rank URL.',
                    response.status,
                    response.url,
                )
                yield scrapy.Request(
                    url='https://fanqienovel.com/rank',
                    callback=self.parse,
                    dont_filter=True,
                    meta={
                        'rank_type': rank_type,
                        'fallback_used': True,
                    },
                )
            else:
                self.logger.warning(
                    'Fallback request also failed (status=%s) for rank_type=%s',
                    response.status,
                    rank_type,
                )
            return

        initial_state = self._extract_initial_state(response.text)

        rank_payload = initial_state.get('rank', {})
        book_list = (
            rank_payload.get('book_list')
            or rank_payload.get('readRankList')
            or rank_payload.get('newRankList')
            or []
        )

        if not isinstance(book_list, list) or not book_list:
            self.logger.warning('No books extracted for rank_type=%s url=%s', rank_type, response.url)
            return

        for book in book_list[: self.limit]:
            book_id = self._clean_text(book.get('bookId'))
            title = self._clean_text(book.get('bookName'))
            synopsis = self._clean_text(book.get('abstract'))
            tags = self._clean_tags([
                book.get('category', ''),
                book.get('categoryV2', ''),
            ])

            if not title:
                continue

            if book_id:
                source_url = urljoin(response.url, f'/page/{book_id}')
            else:
                source_url = response.url

            yield TomatoRankItem(
                title=title,
                synopsis=synopsis,
                tags=tags,
                hot_score=self._to_hot_score(book),
                rank_type=rank_type,
                source_url=source_url,
            )
