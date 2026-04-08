#!/usr/bin/env python
"""
System monitoring script for TomatoFiction platform.
Checks health of all services and logs status.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import requests
from redis import Redis

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Service endpoints
SERVICES = {
    'django': 'http://localhost:8000/api/health/',
    'fastapi': 'http://localhost:8001/health',
}

REDIS_URL = 'redis://127.0.0.1:6379/0'


def check_service(name: str, url: str) -> dict:
    """Check if a service is healthy."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return {'status': 'ok', 'response_time_ms': response.elapsed.total_seconds() * 1000}
        else:
            return {'status': 'error', 'code': response.status_code}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        client = Redis.from_url(REDIS_URL)
        client.ping()
        info = client.info('stats')
        return {
            'status': 'ok',
            'total_connections_received': info.get('total_connections_received', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def main():
    """Run health checks on all services."""
    logger.info('Starting system health check...')

    results = {
        'timestamp': datetime.now().isoformat(),
        'services': {},
    }

    # Check HTTP services
    for name, url in SERVICES.items():
        logger.info(f'Checking {name}...')
        results['services'][name] = check_service(name, url)
        status = results['services'][name]['status']
        if status == 'ok':
            logger.info(f'{name}: OK')
        else:
            logger.error(f'{name}: {status}')

    # Check Redis
    logger.info('Checking Redis...')
    results['services']['redis'] = check_redis()
    if results['services']['redis']['status'] == 'ok':
        logger.info('Redis: OK')
    else:
        logger.error(f"Redis: {results['services']['redis']['status']}")

    # Determine overall status
    all_ok = all(s['status'] == 'ok' for s in results['services'].values())
    results['overall_status'] = 'healthy' if all_ok else 'unhealthy'

    # Save results
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'health_check.json'

    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f'Health check completed. Overall status: {results["overall_status"]}')
    logger.info(f'Results saved to {log_file}')

    # Exit with error code if unhealthy
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
