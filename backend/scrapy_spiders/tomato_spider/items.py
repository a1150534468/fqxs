import scrapy


class TomatoRankItem(scrapy.Item):
    """Scraped inspiration payload for Django inspirations table."""

    title = scrapy.Field()
    synopsis = scrapy.Field()
    tags = scrapy.Field()
    hot_score = scrapy.Field()
    rank_type = scrapy.Field()
    source_url = scrapy.Field()
