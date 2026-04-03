from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        """Test creating a user with email and password"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_user_str_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'testuser')


class UserAuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='testpass123',
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            '/api/users/login/',
            {
                'username': 'apiuser',
                'password': 'testpass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'apiuser')

    def test_refresh_returns_new_access_token(self):
        login_response = self.client.post(
            '/api/users/login/',
            {
                'username': 'apiuser',
                'password': 'testpass123',
            },
            format='json',
        )
        refresh_token = login_response.data['refresh']

        response = self.client.post(
            '/api/users/refresh/',
            {'refresh': refresh_token},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
