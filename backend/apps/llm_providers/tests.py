from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.llm_providers.models import LLMProvider

User = get_user_model()


class LLMProviderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='provider-user',
            email='provider@example.com',
            password='testpass123',
        )

    def test_create_llm_provider(self):
        provider = LLMProvider.objects.create(
            user=self.user,
            name='OpenAI Main',
            provider_type='openai',
            api_url='https://api.openai.com/v1',
            api_key='secret-key',
            task_type='chapter_writing',
            priority=10,
        )

        self.assertEqual(provider.user, self.user)
        self.assertEqual(provider.provider_type, 'openai')
        self.assertTrue(provider.is_active)

    def test_llm_provider_str(self):
        provider = LLMProvider.objects.create(
            user=self.user,
            name='Qwen Backup',
            provider_type='qwen',
            api_url='https://dashscope.aliyuncs.com',
            api_key='secret-key',
            task_type='idea_generation',
        )

        self.assertEqual(str(provider), 'Qwen Backup (qwen)')
