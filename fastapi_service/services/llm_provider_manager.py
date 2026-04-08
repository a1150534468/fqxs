import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMProviderManager:
    """Manage multiple LLM providers with priority-based selection."""

    def __init__(self):
        self.providers = []
        self.django_api_url = None

    def set_django_api_url(self, url: str):
        """Set Django API URL for fetching provider configurations."""
        self.django_api_url = url

    async def fetch_providers_from_django(self, user_token: str, task_type: str = 'chapter') -> list:
        """Fetch active LLM providers from Django API."""
        if not self.django_api_url:
            logger.warning('Django API URL not configured')
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.django_api_url.rstrip('/')}/api/llm-providers/",
                    headers={'Authorization': f'Bearer {user_token}'},
                    params={'is_active': True, 'task_type': task_type},
                )
                if response.status_code == 200:
                    providers = response.json()
                    # Sort by priority (descending)
                    providers.sort(key=lambda p: p.get('priority', 0), reverse=True)
                    logger.info(f'Fetched {len(providers)} providers for task_type={task_type}')
                    return providers
                else:
                    logger.error(f'Failed to fetch providers: {response.status_code}')
                    return []
        except Exception as e:
            logger.error(f'Error fetching providers from Django: {e}')
            return []

    async def call_llm(
        self,
        system_message: str,
        user_message: str,
        providers: list,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> str:
        """Call LLM with fallback to next provider on failure."""
        if not providers:
            raise ValueError('No LLM providers available')

        last_error = None
        for provider in providers:
            try:
                logger.info(f"Trying provider: {provider['name']} (priority={provider.get('priority', 0)})")
                content = await self._call_single_provider(
                    provider=provider,
                    system_message=system_message,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info(f"Successfully generated content using provider: {provider['name']}")
                return content
            except Exception as e:
                logger.warning(f"Provider {provider['name']} failed: {e}")
                last_error = e
                continue

        # All providers failed
        raise Exception(f'All LLM providers failed. Last error: {last_error}')

    async def _call_single_provider(
        self,
        provider: dict,
        system_message: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call a single LLM provider."""
        api_url = provider['api_url'].rstrip('/')
        api_key = provider['api_key']
        model = provider.get('model', 'gpt-3.5-turbo')

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        body = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': user_message},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f'{api_url}/chat/completions',
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        return data['choices'][0]['message']['content']


llm_provider_manager = LLMProviderManager()
