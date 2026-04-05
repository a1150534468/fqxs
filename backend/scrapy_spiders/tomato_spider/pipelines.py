import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import MySQLdb
from dotenv import load_dotenv
from itemadapter import ItemAdapter


class MySQLInspirationPipeline:
    """Persist scraped inspirations into Django's MySQL table with dedup."""

    def __init__(self):
        self.connection = None
        self.cursor = None
        self.inserted_count = 0
        self.duplicate_count = 0

    def open_spider(self, spider):
        backend_root = Path(__file__).resolve().parents[2]
        env_file = backend_root / '.env'
        load_dotenv(env_file)

        host = os.getenv('MYSQL_HOST', 'mysql')
        port = int(os.getenv('MYSQL_PORT', '3306'))
        user = os.getenv('MYSQL_USER', 'fqxs_user')
        password = os.getenv('MYSQL_PASSWORD', 'fqxs_password')
        database = os.getenv('MYSQL_DATABASE', 'fqxs')

        self.connection = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            db=database,
            charset='utf8mb4',
            autocommit=False,
        )
        self.cursor = self.connection.cursor()
        spider.logger.info('MySQL pipeline connected to %s:%s/%s', host, port, database)

    def close_spider(self, spider):
        spider.logger.info(
            'MySQL pipeline completed. inserted=%s, duplicates=%s',
            self.inserted_count,
            self.duplicate_count,
        )
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def _to_hot_score(self, value):
        try:
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal('0.00')

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        source_url = adapter.get('source_url')
        if not source_url:
            spider.logger.warning('Skipping item without source_url: %s', adapter.asdict())
            return item

        self.cursor.execute(
            'SELECT id FROM inspiration WHERE source_url = %s LIMIT 1',
            (source_url,),
        )
        existing_row = self.cursor.fetchone()
        if existing_row:
            self.duplicate_count += 1
            return item

        title = adapter.get('title') or ''
        synopsis = adapter.get('synopsis') or ''
        rank_type = adapter.get('rank_type') or ''
        tags = adapter.get('tags') or []
        hot_score = self._to_hot_score(adapter.get('hot_score'))

        self.cursor.execute(
            """
            INSERT INTO inspiration (
                source_url,
                title,
                synopsis,
                tags,
                hot_score,
                rank_type,
                collected_at,
                is_used,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, NOW(), NOW())
            """,
            (
                source_url,
                title,
                synopsis,
                json.dumps(tags, ensure_ascii=False),
                hot_score,
                rank_type,
                False,
            ),
        )
        self.connection.commit()
        self.inserted_count += 1
        return item
