#!/usr/bin/env python
"""
Test script for inspiration generation and project creation APIs.
Run this after starting both Django and FastAPI services.
"""
import json
import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
from apps.inspirations.models import Inspiration
from apps.users.models import User


def get_auth_token():
    """Get JWT token for testing."""
    # Create or get test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")

    # Get token
    response = requests.post(
        'http://localhost:8000/api/auth/token/',
        json={'username': 'testuser', 'password': 'testpass123'}
    )
    if response.status_code == 200:
        return response.json()['access']
    else:
        print(f"Failed to get token: {response.text}")
        return None


def test_generate_inspiration():
    """Test inspiration generation from trending books."""
    print("\n=== Testing Inspiration Generation ===")

    token = get_auth_token()
    if not token:
        return

    # Prepare test data
    trending_books = [
        {
            "title": "都市修仙传",
            "synopsis": "现代都市中的修仙故事，主角获得神秘传承",
            "tags": ["都市", "修仙", "爽文"],
            "hot_score": 95.5
        },
        {
            "title": "重生之商业帝国",
            "synopsis": "重生回到过去，利用先知优势建立商业帝国",
            "tags": ["都市", "重生", "商战"],
            "hot_score": 88.0
        },
        {
            "title": "玄幻大陆之巅",
            "synopsis": "异世界冒险，主角从弱小到强大的成长之路",
            "tags": ["玄幻", "冒险", "热血"],
            "hot_score": 92.3
        }
    ]

    response = requests.post(
        'http://localhost:8000/api/inspirations/generate-from-trends/',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'trending_books': trending_books,
            'genre_preference': '都市'
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Generated {len(data.get('inspirations', []))} inspirations")
        print(f"Analysis: {data.get('analysis_summary', '')[:100]}...")
        for i, insp in enumerate(data.get('inspirations', []), 1):
            print(f"\n{i}. {insp.get('title')}")
            print(f"   Genre: {insp.get('genre')}")
            print(f"   Popularity: {insp.get('estimated_popularity')}")
    else:
        print(f"Error: {response.text}")


def test_start_project():
    """Test starting a project from inspiration."""
    print("\n=== Testing Project Creation ===")

    token = get_auth_token()
    if not token:
        return

    # Create a test inspiration
    inspiration = Inspiration.objects.create(
        source_url='http://test.com',
        title='测试创意：都市修仙',
        synopsis='一个关于都市修仙的创新故事',
        tags=['都市', '修仙'],
        hot_score=85.0,
        is_used=False
    )
    print(f"Created test inspiration: {inspiration.id}")

    response = requests.post(
        f'http://localhost:8000/api/inspirations/{inspiration.id}/start-project/',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'title': '都市修仙传说',
            'genre': '都市',
            'target_chapters': 50,
            'first_chapter_title': '第一章：觉醒'
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Project created: {data.get('project_id')}")
        print(f"Title: {data.get('title')}")
        print(f"Genre: {data.get('genre')}")
        print(f"First chapter: {data.get('first_chapter', {}).get('title')}")
        print(f"Word count: {data.get('first_chapter', {}).get('word_count')}")
        print(f"Status: {data.get('first_chapter', {}).get('status')}")
    else:
        print(f"Error: {response.text}")


if __name__ == '__main__':
    print("Starting API tests...")
    print("Make sure Django (port 8000) and FastAPI (port 8001) are running!")

    test_generate_inspiration()
    test_start_project()

    print("\n=== Tests completed ===")
