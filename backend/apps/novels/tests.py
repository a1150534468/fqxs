from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inspirations.models import Inspiration
from apps.chapters.models import Chapter, ChapterSummary
from apps.novels.models import (
    ForeshadowItem,
    KnowledgeFact,
    NovelDraft,
    NovelProject,
    NovelSetting,
    PlotArcPoint,
    Storyline,
    StyleProfile,
)

User = get_user_model()


class NovelProjectModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='novel-user',
            email='novel@example.com',
            password='testpass123',
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/novel',
            title='Idea Source',
        )

    def test_create_novel_project(self):
        project = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='My Novel',
            genre='Fantasy',
            update_frequency=1,
        )

        self.assertEqual(project.user, self.user)
        self.assertEqual(project.inspiration, self.inspiration)
        self.assertEqual(project.status, 'active')

    def test_novel_project_str(self):
        project = NovelProject.objects.create(
            user=self.user,
            title='String Novel',
            genre='Sci-Fi',
        )

        self.assertEqual(str(project), 'String Novel')


class DraftAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='draft-owner',
            email='draft@example.com',
            password='testpass123',
        )
        response = self.client.post(
            reverse('user-login'),
            {
                'username': 'draft-owner',
                'password': 'testpass123',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_create_draft_persists_style_preference(self):
        response = self.client.post(
            reverse('draft-list'),
            {
                'inspiration': '宗门废柴逆袭成天命剑修',
                'genre': '玄幻',
                'style_preference': '热血升级流',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['style_preference'], '热血升级流')
        draft = NovelDraft.objects.get(pk=response.data['id'])
        self.assertEqual(draft.style_preference, '热血升级流')

    @patch('apps.novels.views.httpx.post')
    def test_generate_titles_returns_cleaned_unique_candidates(self, mock_post):
        draft = NovelDraft.objects.create(
            user=self.user,
            inspiration='末世废土中觉醒时间回溯异能的快递员',
            genre='科幻',
            style_preference='强悬念',
        )
        mock_post.return_value.status_code = status.HTTP_200_OK
        mock_post.return_value.json.return_value = {
            'titles': ['  时间回档快递员  ', '', '时间回档快递员', '废土逆流者', '   ', '废土逆流者']
        }

        response = self.client.post(
            reverse('draft-generate-titles', kwargs={'pk': draft.pk}),
            {'count': 5},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['titles'], ['时间回档快递员', '废土逆流者'])
        self.assertEqual(response.data['style_preference'], '强悬念')

    @patch('apps.novels.views.httpx.post')
    def test_generate_titles_rejects_completed_draft(self, mock_post):
        draft = NovelDraft.objects.create(
            user=self.user,
            inspiration='仙门掌门重生回入门第一天',
            genre='玄幻',
            style_preference='轻松反套路',
            is_completed=True,
        )

        response = self.client.post(
            reverse('draft-generate-titles', kwargs={'pk': draft.pk}),
            {'count': 4},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Draft already completed.')
        mock_post.assert_not_called()

    @patch('apps.novels.views.httpx.post')
    def test_generate_titles_forwards_draft_payload(self, mock_post):
        draft = NovelDraft.objects.create(
            user=self.user,
            inspiration='落魄县令靠断案直播洗白翻红',
            genre='历史',
            style_preference='冷幽默',
        )
        mock_post.return_value.status_code = status.HTTP_200_OK
        mock_post.return_value.json.return_value = {'titles': ['县令翻红记']}

        response = self.client.post(
            reverse('draft-generate-titles', kwargs={'pk': draft.pk}),
            {'count': 4},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['titles'], ['县令翻红记'])
        self.assertEqual(response.data['style_preference'], '冷幽默')
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs['json'],
            {
                'inspiration': '落魄县令靠断案直播洗白翻红',
                'genre': '历史',
                'style_preference': '冷幽默',
                'count': 4,
            },
        )

    @patch('apps.novels.views.httpx.post')
    def test_generate_titles_clamps_requested_count(self, mock_post):
        draft = NovelDraft.objects.create(
            user=self.user,
            inspiration='落魄县令靠断案直播洗白翻红',
            genre='历史',
            style_preference='冷幽默',
        )
        mock_post.return_value.status_code = status.HTTP_200_OK
        mock_post.return_value.json.return_value = {'titles': ['县令翻红记']}

        response = self.client.post(
            reverse('draft-generate-titles', kwargs={'pk': draft.pk}),
            {'count': 99},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['titles'], ['县令翻红记'])
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['count'], 5)


class NovelProjectAPITest(TestCase):
    def setUp(self):
        """Create authenticated clients and seed projects for ownership checks."""
        self.client = APIClient()
        self.other_client = APIClient()
        self.user = User.objects.create_user(
            username='project-owner',
            email='owner@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='other-owner',
            email='other@example.com',
            password='testpass123',
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/api-project',
            title='Project Idea Source',
        )
        self.project = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='Owner Project',
            genre='Fantasy',
            synopsis='Owner synopsis',
            target_chapters=120,
            current_chapter=12,
            update_frequency=1,
        )
        self.paused_project = NovelProject.objects.create(
            user=self.user,
            title='Mystery Casebook',
            genre='Mystery',
            status='paused',
            synopsis='Detective themed project',
            target_chapters=80,
            current_chapter=20,
            update_frequency=1,
        )
        self.completed_project = NovelProject.objects.create(
            user=self.user,
            title='Historical Saga',
            genre='History',
            status='completed',
            target_chapters=60,
            current_chapter=60,
            update_frequency=1,
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other Project',
            genre='Sci-Fi',
        )
        now = timezone.now()
        NovelProject.objects.filter(pk=self.project.pk).update(created_at=now - timedelta(days=7))
        NovelProject.objects.filter(pk=self.paused_project.pk).update(created_at=now - timedelta(days=2))
        NovelProject.objects.filter(pk=self.completed_project.pk).update(created_at=now - timedelta(days=15))
        self.list_url = reverse('novelproject-list')
        self.detail_url = reverse('novelproject-detail', kwargs={'pk': self.project.pk})
        self.other_detail_url = reverse('novelproject-detail', kwargs={'pk': self.other_project.pk})
        self.workbench_url = reverse('workbench-context', kwargs={'project_id': self.project.pk})
        self.generation_context_url = reverse('generation-context', kwargs={'project_id': self.project.pk})
        self.authenticate(self.client, 'project-owner')
        self.authenticate(self.other_client, 'other-owner')

    def authenticate(self, client, username):
        """Authenticate an API client using the JWT login endpoint."""
        response = client.post(
            reverse('user-login'),
            {
                'username': username,
                'password': 'testpass123',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_list_only_returns_current_users_projects(self):
        """It limits the paginated list response to the current user's projects."""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        returned_titles = {item['title'] for item in response.data['results']}
        self.assertSetEqual(returned_titles, {'Owner Project', 'Mystery Casebook', 'Historical Saga'})

    def test_create_project_assigns_authenticated_user(self):
        """It ignores any submitted user value and binds the project to request.user."""
        response = self.client.post(
            self.list_url,
            {
                'user': self.other_user.pk,
                'inspiration': self.inspiration.pk,
                'title': 'New Project',
                'genre': 'Urban',
                'synopsis': 'Generated synopsis',
                'outline': 'Outline',
                'ai_prompt_template': 'Prompt',
                'status': 'active',
                'target_chapters': 50,
                'current_chapter': 0,
                'update_frequency': 1,
                'tomato_book_id': 'book-123',
                'is_deleted': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Project')
        self.assertEqual(response.data['user'], self.user.pk)
        self.assertEqual(NovelProject.objects.get(id=response.data['id']).user, self.user)

    def test_retrieve_project(self):
        """It retrieves a single project owned by the authenticated user."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Owner Project')
        self.assertEqual(response.data['user'], self.user.pk)

    def test_update_project(self):
        """It updates a project owned by the authenticated user."""
        response = self.client.put(
            self.detail_url,
            {
                'inspiration': self.inspiration.pk,
                'title': 'Updated Project',
                'genre': 'Fantasy',
                'synopsis': 'Updated synopsis',
                'outline': 'Updated outline',
                'ai_prompt_template': 'Updated prompt',
                'status': 'paused',
                'target_chapters': 130,
                'current_chapter': 13,
                'update_frequency': 1,
                'tomato_book_id': 'book-456',
                'is_deleted': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Project')
        self.assertEqual(response.data['status'], 'paused')

    def test_partial_update_project(self):
        """It supports partial updates for owned projects."""
        response = self.client.patch(
            self.detail_url,
            {
                'title': 'Patched Project',
                'current_chapter': 15,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Patched Project')
        self.assertEqual(response.data['current_chapter'], 15)

    def test_delete_project_soft_deletes_and_hides_it(self):
        """It soft deletes owned projects and removes them from the visible queryset."""
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_deleted)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_authentication_required(self):
        """It rejects unauthenticated CRUD requests with HTTP 401."""
        unauthenticated_client = APIClient()

        cases = (
            ('get', self.list_url, None),
            ('post', self.list_url, {'title': 'Blocked', 'genre': 'Fantasy', 'target_chapters': 10, 'current_chapter': 0, 'update_frequency': 1}),
            ('get', self.detail_url, None),
            ('patch', self.detail_url, {'title': 'Blocked'}),
            ('delete', self.detail_url, None),
        )

        for method, url, payload in cases:
            with self.subTest(method=method, url=url):
                response = getattr(unauthenticated_client, method)(url, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_access_another_users_project(self):
        """It returns 404 when a user tries to access someone else's project."""
        response = self.client.get(self.other_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workbench_context_returns_aggregated_payload(self):
        """It returns a single payload for the workbench UI."""
        NovelSetting.objects.create(
            project=self.project,
            setting_type='worldview',
            title='世界观',
            content='云海城邦与地底遗迹并存。',
            structured_data={'time_setting': '近未来'},
            source='wizard',
            order=0,
        )
        Storyline.objects.create(
            project=self.project,
            name='主线',
            storyline_type='main',
            status='active',
            description='主角探索云海禁区的真相。',
            priority=100,
        )
        chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=1,
            title='第一章',
            raw_content='云海翻涌，主角踏入禁区。秘密仍未揭晓？',
            final_content='云海翻涌，主角踏入禁区。秘密仍未揭晓？',
            word_count=20,
            status='draft',
            summary='主角进入禁区并发现新的异常。',
            open_threads=['禁区深处究竟藏着什么？'],
        )
        ChapterSummary.objects.create(
            project=self.project,
            chapter=chapter,
            summary='主角进入禁区并发现新的异常。',
            key_events=['进入禁区', '发现异常'],
            open_threads=['禁区深处究竟藏着什么？'],
        )
        KnowledgeFact.objects.create(
            project=self.project,
            subject='云海城邦',
            predicate='时代设定',
            object='近未来',
            source_excerpt='云海城邦与地底遗迹并存。',
        )
        ForeshadowItem.objects.create(
            project=self.project,
            title='禁区深处究竟藏着什么？',
            description='开篇留下的核心悬念',
        )
        StyleProfile.objects.create(
            project=self.project,
            profile_type='project',
            content='冷峻、快节奏、悬疑推进',
            structured_data={'tone': '冷峻'},
        )

        response = self.client.get(self.workbench_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project']['id'], self.project.id)
        self.assertEqual(response.data['stats']['total_words'], 20)
        self.assertEqual(len(response.data['chapters']), 1)
        self.assertEqual(len(response.data['settings']), 1)
        self.assertEqual(len(response.data['chapter_summaries']), 1)
        self.assertEqual(len(response.data['storylines']), 1)
        self.assertEqual(len(response.data['knowledge_facts']), 1)
        self.assertEqual(len(response.data['foreshadow_items']), 1)
        self.assertEqual(len(response.data['style_profiles']), 1)
        self.assertIn('workbench_highlights', response.data)
        self.assertIn('focus_card', response.data['workbench_highlights'])
        self.assertIn('continuity_alerts', response.data['workbench_highlights'])
        self.assertIn('knowledge_graph', response.data)

    def test_workbench_context_rejects_other_users_project(self):
        """It hides another user's workbench context."""
        response = self.client.get(
            reverse('workbench-context', kwargs={'project_id': self.other_project.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generation_context_returns_structured_payload(self):
        NovelSetting.objects.create(
            project=self.project,
            setting_type='storyline',
            title='主线',
            content='主角调查旧王朝的失落档案。',
            structured_data={
                'premise': '调查失落档案',
                'central_conflict': '档案牵出更大的权力斗争',
                'themes': ['真相', '牺牲'],
                'stakes': '若失败则城市沦陷',
            },
            source='wizard',
            order=3,
        )
        Storyline.objects.create(
            project=self.project,
            name='主线',
            storyline_type='main',
            status='active',
            description='主角调查旧王朝的失落档案。',
            priority=100,
        )
        PlotArcPoint.objects.create(
            project=self.project,
            chapter_number=3,
            point_type='turning',
            tension_level=80,
            description='发现档案缺失的真相',
        )
        response = self.client.get(self.generation_context_url, {'chapter_number': 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chapter_number'], 3)
        self.assertIn('selected_settings', response.data)
        self.assertIn('storylines', response.data)
        self.assertIn('plot_points', response.data)
        self.assertIn('chapter_goal', response.data)
        self.assertIn('context_layers', response.data)
        self.assertIn('focus_card', response.data)
        self.assertIn('micro_beats', response.data)
        self.assertIn('continuity_alerts', response.data)

    def test_generation_context_prioritizes_relevant_assets(self):
        NovelSetting.objects.create(
            project=self.project,
            setting_type='storyline',
            title='档案主线',
            content='主角调查旧王朝档案失踪背后的真相。',
            structured_data={'premise': '旧王朝档案失踪'},
            source='wizard',
            order=1,
        )
        NovelSetting.objects.create(
            project=self.project,
            setting_type='map',
            title='海港地图',
            content='港口集市商贩云集，与档案无关。',
            structured_data={'regions': [{'name': '海港集市'}]},
            source='wizard',
            order=2,
        )
        Storyline.objects.create(
            project=self.project,
            name='档案主线',
            storyline_type='main',
            status='active',
            description='围绕旧王朝档案缺失展开调查。',
            priority=100,
        )
        Storyline.objects.create(
            project=self.project,
            name='海港支线',
            storyline_type='subplot',
            status='active',
            description='描述港口商会竞争。',
            priority=20,
        )
        PlotArcPoint.objects.create(
            project=self.project,
            chapter_number=6,
            point_type='turning',
            tension_level=90,
            description='主角发现档案被人为删改的真相',
        )
        KnowledgeFact.objects.create(
            project=self.project,
            subject='旧王朝档案',
            predicate='存放地点',
            object='地下书库',
            source_excerpt='档案被藏入地下书库深处。',
        )
        KnowledgeFact.objects.create(
            project=self.project,
            subject='海港商会',
            predicate='主营',
            object='香料贸易',
            source_excerpt='海港商会近期扩大香料生意。',
        )
        ForeshadowItem.objects.create(
            project=self.project,
            title='档案缺页的真相',
            description='缺失页面将揭开旧王朝覆灭内幕。',
            expected_payoff_chapter=6,
            status='open',
        )
        ForeshadowItem.objects.create(
            project=self.project,
            title='集市里的黑猫',
            description='一只黑猫在海港集市穿行。',
            expected_payoff_chapter=20,
            status='open',
        )

        response = self.client.get(self.generation_context_url, {'chapter_number': 6})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selected_settings'][0]['setting_type'], 'storyline')
        self.assertEqual(response.data['storylines'][0]['name'], '档案主线')
        self.assertEqual(response.data['knowledge_facts'][0]['subject'], '旧王朝档案')
        self.assertEqual(response.data['foreshadow_items'][0]['title'], '档案缺页的真相')

    def test_create_project_rejects_invalid_chapter_counts(self):
        """It validates chapter-related numeric constraints."""
        response = self.client.post(
            self.list_url,
            {
                'title': 'Invalid Project',
                'genre': 'Fantasy',
                'target_chapters': 5,
                'current_chapter': 6,
                'update_frequency': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_chapter', response.data)

    def test_list_filters_by_status(self):
        """It filters projects by one or more status values."""
        response = self.client.get(self.list_url, {'status': 'paused,completed'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_titles = {item['title'] for item in response.data['results']}
        self.assertSetEqual(returned_titles, {'Mystery Casebook', 'Historical Saga'})

    def test_list_filters_by_type_alias(self):
        """It treats `type` as a genre filter for compatibility."""
        response = self.client.get(self.list_url, {'type': 'mystery'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_supports_keyword_search(self):
        """It searches title, genre, synopsis, and outline fields."""
        response = self.client.get(self.list_url, {'search': 'detective'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_filters_by_created_time_range(self):
        """It filters by created_after and created_before query params."""
        start = (timezone.now() - timedelta(days=3)).isoformat()
        end = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.client.get(
            self.list_url,
            {'created_after': start, 'created_before': end},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_rejects_invalid_created_time(self):
        """It returns HTTP 400 when created time params are malformed."""
        response = self.client.get(self.list_url, {'created_after': 'not-a-date'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('created_after', response.data)
