import json
import os
from pathlib import Path

from dotenv import load_dotenv

BOT_NAME = 'tomato_spider'

SPIDER_MODULES = ['tomato_spider.spiders']
NEWSPIDER_MODULE = 'tomato_spider.spiders'

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / '.env')

# Respect frequency limits to reduce anti-crawl risk.
DOWNLOAD_DELAY = 3
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
RANDOMIZE_DOWNLOAD_DELAY = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [403, 408, 429, 500, 502, 503, 504, 522, 524]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 30
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
AUTOTHROTTLE_DEBUG = False

ROBOTSTXT_OBEY = True
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://fanqienovel.com/',
    'Connection': 'keep-alive',
}

DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'tomato_spider.middlewares.ProxyAndUserAgentMiddleware': 400,
}

ITEM_PIPELINES = {
    'tomato_spider.pipelines.MySQLInspirationPipeline': 300,
}

# Proxy pool configuration (comma-separated URLs), example:
# SCRAPY_PROXY_LIST=http://user:pass@1.2.3.4:8080,http://5.6.7.8:3128
PROXY_LIST = [
    proxy.strip()
    for proxy in os.getenv('SCRAPY_PROXY_LIST', '').split(',')
    if proxy.strip()
]
STRICT_PROXY_ENABLED = os.getenv('STRICT_PROXY_ENABLED', '1').lower() not in {
    '0',
    'false',
    'no',
}

# Rank URL map can be overridden with JSON env var SCRAPY_RANK_URL_MAP.
_default_rank_map = {
    'hot': 'https://fanqienovel.com/rank',
    'new': 'https://fanqienovel.com/rank/1_1_1141',
    'rising': 'https://fanqienovel.com/rank/stat0',
}
try:
    RANK_URL_MAP = {
        **_default_rank_map,
        **json.loads(os.getenv('SCRAPY_RANK_URL_MAP', '{}')),
    }
except json.JSONDecodeError:
    RANK_URL_MAP = _default_rank_map

LOG_LEVEL = os.getenv('SCRAPY_LOG_LEVEL', 'INFO')

REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'
