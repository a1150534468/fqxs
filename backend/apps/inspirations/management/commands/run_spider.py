import os
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Run the Scrapy tomato rank spider and persist inspirations to MySQL.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Maximum number of records fetched per rank type (default: 5).',
        )
        parser.add_argument(
            '--rank-types',
            default='hot,new,rising',
            help='Comma-separated rank types to crawl (default: hot,new,rising).',
        )
        parser.add_argument(
            '--log-level',
            default='INFO',
            help='Scrapy log level (default: INFO).',
        )
        parser.add_argument(
            '--allow-no-proxy',
            action='store_true',
            help='Disable strict proxy mode for debugging only.',
        )

    def handle(self, *args, **options):
        backend_root = Path(__file__).resolve().parents[4]
        scrapy_root = backend_root / 'scrapy_spiders'

        if not scrapy_root.exists():
            raise CommandError(f'Scrapy project not found: {scrapy_root}')

        env = os.environ.copy()
        existing_pythonpath = env.get('PYTHONPATH', '')
        env['PYTHONPATH'] = (
            f"{backend_root}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(backend_root)
        )

        if options['allow_no_proxy']:
            env['STRICT_PROXY_ENABLED'] = '0'
            self.stdout.write(self.style.WARNING('Running in allow-no-proxy mode (debug only).'))

        command = [
            sys.executable,
            '-m',
            'scrapy',
            'crawl',
            'tomato_rank',
            '-a',
            f"limit={options['limit']}",
            '-a',
            f"rank_types={options['rank_types']}",
            '-s',
            f"LOG_LEVEL={options['log_level']}",
        ]

        self.stdout.write(f'Running command: {" ".join(command)}')
        process = subprocess.run(
            command,
            cwd=scrapy_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        if process.stdout:
            self.stdout.write(process.stdout)
        if process.stderr:
            self.stderr.write(process.stderr)

        combined_output = f'{process.stdout}\n{process.stderr}'
        error_markers = (
            'Error while obtaining start requests',
            'Traceback (most recent call last):',
            'Spider error processing',
        )

        if any(marker in combined_output for marker in error_markers):
            raise CommandError('Spider encountered runtime errors. Check logs above.')

        if process.returncode != 0:
            raise CommandError(f'Spider finished with non-zero exit code: {process.returncode}')

        self.stdout.write(self.style.SUCCESS('Spider run completed successfully.'))
