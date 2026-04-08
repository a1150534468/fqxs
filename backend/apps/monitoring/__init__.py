import logging
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views import View
from redis import Redis

logger = logging.getLogger('apps')


class HealthCheckView(View):
    """Health check endpoint for monitoring system status."""

    def get(self, request):
        health_status = {
            'status': 'healthy',
            'checks': {},
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            logger.error(f'Database health check failed: {e}')
            health_status['checks']['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check Redis
        try:
            redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            health_status['checks']['redis'] = 'ok'
        except Exception as e:
            logger.error(f'Redis health check failed: {e}')
            health_status['checks']['redis'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check FastAPI service
        try:
            import requests
            response = requests.get(f"{settings.FASTAPI_URL.rstrip('/')}/health", timeout=5)
            if response.status_code == 200:
                health_status['checks']['fastapi'] = 'ok'
            else:
                health_status['checks']['fastapi'] = f'status_code: {response.status_code}'
                health_status['status'] = 'degraded'
        except Exception as e:
            logger.error(f'FastAPI health check failed: {e}')
            health_status['checks']['fastapi'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return JsonResponse(health_status, status=status_code)
