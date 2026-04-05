import random
from typing import List

from fake_useragent import UserAgent
from scrapy import signals
from scrapy.exceptions import IgnoreRequest


FALLBACK_USER_AGENTS = [
    # Desktop
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    # Mobile
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
]


class TomatoSpiderSpiderMiddleware:
    """Default spider middleware placeholder with open logging."""

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for item in result:
            yield item

    def process_spider_exception(self, response, exception, spider):
        return None

    def process_start_requests(self, start_requests, spider):
        for request in start_requests:
            yield request

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s', spider.name)


class ProxyAndUserAgentMiddleware:
    """Rotate proxy IP and user agent for each outgoing request."""

    def __init__(self, proxy_list: List[str], strict_proxy_enabled: bool):
        self.proxy_list = proxy_list
        self.strict_proxy_enabled = strict_proxy_enabled
        try:
            self.ua_provider = UserAgent()
            self.use_fake_user_agent = True
        except Exception:
            self.ua_provider = None
            self.use_fake_user_agent = False

    @classmethod
    def from_crawler(cls, crawler):
        proxy_list = crawler.settings.getlist('PROXY_LIST')
        strict_proxy_enabled = crawler.settings.getbool('STRICT_PROXY_ENABLED', True)

        middleware = cls(
            proxy_list=proxy_list,
            strict_proxy_enabled=strict_proxy_enabled,
        )
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        spider.logger.info(
            'Proxy middleware initialized. strict_proxy_enabled=%s, proxies=%s',
            self.strict_proxy_enabled,
            len(self.proxy_list),
        )

    def _random_user_agent(self):
        if self.use_fake_user_agent and self.ua_provider is not None:
            try:
                return self.ua_provider.random
            except Exception:
                pass
        return random.choice(FALLBACK_USER_AGENTS)

    def process_request(self, request, spider):
        request.headers.setdefault('User-Agent', self._random_user_agent())
        request.headers.setdefault(
            'Accept',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        )
        request.headers.setdefault('Accept-Language', 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7')
        request.headers.setdefault('Referer', 'https://fanqienovel.com/')
        request.headers.setdefault('Connection', 'keep-alive')

        if self.proxy_list:
            request.meta['proxy'] = random.choice(self.proxy_list)
            return None

        if self.strict_proxy_enabled:
            raise IgnoreRequest(
                'Request blocked because no proxies are configured and strict proxy mode is enabled.'
            )
        return None


class TomatoSpiderDownloaderMiddleware:
    """Default downloader middleware placeholder."""

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None

    def spider_opened(self, spider):
        spider.logger.info('Downloader middleware active: %s', spider.name)
