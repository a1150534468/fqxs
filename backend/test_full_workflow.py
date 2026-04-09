#!/usr/bin/env python
"""
Full Workflow Automated Test Script
Tests the complete TomatoFiction platform workflow from inspiration to publishing.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import django
import requests

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject
from apps.chapters.models import Chapter
from apps.tasks.models import Task

User = get_user_model()


class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str = "", details: Dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()


class WorkflowTester:
    """Full workflow test runner"""

    def __init__(self, base_url: str = "http://localhost:8000", fastapi_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.fastapi_url = fastapi_url.rstrip('/')
        self.token = None
        self.user = None
        self.results: List[TestResult] = []

        # Test data storage
        self.test_inspiration_id = None
        self.test_project_id = None
        self.test_chapter_id = None
        self.test_task_id = None

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def add_result(self, name: str, passed: bool, message: str = "", details: Dict = None):
        """Add test result"""
        result = TestResult(name, passed, message, details)
        self.results.append(result)
        status = "✓ PASS" if passed else "✗ FAIL"
        self.log(f"{status}: {name} - {message}", "PASS" if passed else "FAIL")

    def setup_test_user(self):
        """Create or get test user"""
        self.log("Setting up test user...")
        try:
            self.user, created = User.objects.get_or_create(
                username='test_workflow_user',
                defaults={
                    'email': 'test_workflow@example.com',
                }
            )
            if created:
                self.user.set_password('test_password_123')
                self.user.save()
                self.log("Created new test user")
            else:
                self.log("Using existing test user")
            return True
        except Exception as e:
            self.log(f"Failed to setup test user: {e}", "ERROR")
            return False

    def login(self):
        """Login and get JWT token"""
        self.log("Logging in...")
        try:
            response = requests.post(
                f"{self.base_url}/api/users/login/",
                json={
                    'username': 'test_workflow_user',
                    'password': 'test_password_123'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access')
                self.add_result(
                    "User Login",
                    True,
                    "Successfully logged in and obtained JWT token",
                    {'token_length': len(self.token) if self.token else 0}
                )
                return True
            else:
                self.add_result(
                    "User Login",
                    False,
                    f"Login failed with status {response.status_code}",
                    {'response': response.text}
                )
                return False
        except Exception as e:
            self.add_result("User Login", False, f"Login error: {str(e)}")
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    # ========== Test 1: Inspiration Generation ==========

    def test_create_sample_inspirations(self):
        """Create sample inspirations for testing"""
        self.log("Creating sample inspirations...")
        try:
            # Create trending book inspirations
            sample_books = [
                {
                    'title': '都市修仙传',
                    'synopsis': '一个普通大学生意外获得修仙传承，在都市中开启修仙之路',
                    'tags': ['都市', '修仙', '热血'],
                    'hot_score': 9500,
                    'rank_type': 'trending'
                },
                {
                    'title': '重生之商业帝国',
                    'synopsis': '金融大佬重生回到2000年，利用先知优势打造商业帝国',
                    'tags': ['都市', '重生', '商战'],
                    'hot_score': 8800,
                    'rank_type': 'trending'
                },
                {
                    'title': '星际争霸之虫族崛起',
                    'synopsis': '穿越成为虫族主宰，带领虫族征服星辰大海',
                    'tags': ['科幻', '星际', '争霸'],
                    'hot_score': 7600,
                    'rank_type': 'trending'
                }
            ]

            created_count = 0
            for book in sample_books:
                insp, created = Inspiration.objects.get_or_create(
                    title=book['title'],
                    defaults={
                        'synopsis': book['synopsis'],
                        'tags': book['tags'],
                        'hot_score': book['hot_score'],
                        'rank_type': book['rank_type'],
                        'is_used': False
                    }
                )
                if created:
                    created_count += 1

            self.add_result(
                "Create Sample Inspirations",
                True,
                f"Created {created_count} new inspirations, total available: {Inspiration.objects.filter(is_used=False).count()}",
                {'created': created_count}
            )
            return True
        except Exception as e:
            self.add_result("Create Sample Inspirations", False, f"Error: {str(e)}")
            return False

    def test_generate_inspiration_from_trends(self):
        """Test AI-generated inspiration from trending books"""
        self.log("Testing AI inspiration generation from trends...")
        try:
            response = requests.post(
                f"{self.base_url}/api/inspirations/generate-from-trends/",
                json={'genre_preference': '都市'},
                headers=self.get_headers(),
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                created_count = data.get('created_count', 0)
                self.add_result(
                    "Generate Inspiration from Trends",
                    created_count > 0,
                    f"Generated {created_count} AI inspirations",
                    {'created_count': created_count, 'inspirations': data.get('inspirations', [])}
                )
                return created_count > 0
            else:
                self.add_result(
                    "Generate Inspiration from Trends",
                    False,
                    f"Failed with status {response.status_code}",
                    {'response': response.text}
                )
                return False
        except Exception as e:
            self.add_result("Generate Inspiration from Trends", False, f"Error: {str(e)}")
            return False

    def test_list_inspirations(self):
        """Test listing inspirations"""
        self.log("Testing inspiration list API...")
        try:
            response = requests.get(
                f"{self.base_url}/api/inspirations/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                inspirations = data if isinstance(data, list) else data.get('results', [])
                if inspirations:
                    self.test_inspiration_id = inspirations[0]['id']
                self.add_result(
                    "List Inspirations",
                    len(inspirations) > 0,
                    f"Retrieved {len(inspirations)} inspirations",
                    {'count': len(inspirations), 'first_id': self.test_inspiration_id}
                )
                return len(inspirations) > 0
            else:
                self.add_result(
                    "List Inspirations",
                    False,
                    f"Failed with status {response.status_code}"
                )
                return False
        except Exception as e:
            self.add_result("List Inspirations", False, f"Error: {str(e)}")
            return False

    # ========== Test 2: Project Startup ==========

    def test_start_project_from_inspiration(self):
        """Test starting a complete project from inspiration"""
        self.log("Testing project startup from inspiration...")

        if not self.test_inspiration_id:
            self.add_result(
                "Start Project from Inspiration",
                False,
                "No inspiration ID available"
            )
            return False

        try:
            response = requests.post(
                f"{self.base_url}/api/inspirations/{self.test_inspiration_id}/start-project/",
                json={
                    'title': '测试小说项目',
                    'genre': '都市',
                    'target_chapters': 50,
                    'first_chapter_title': '第一章：觉醒'
                },
                headers=self.get_headers(),
                timeout=300
            )

            if response.status_code == 201:
                data = response.json()
                self.test_project_id = data.get('project_id')
                first_chapter = data.get('first_chapter', {})
                self.test_chapter_id = first_chapter.get('id')

                self.add_result(
                    "Start Project from Inspiration",
                    True,
                    f"Project created with ID {self.test_project_id}, first chapter ID {self.test_chapter_id}",
                    {
                        'project_id': self.test_project_id,
                        'title': data.get('title'),
                        'outline_length': len(data.get('outline', '')),
                        'first_chapter': first_chapter
                    }
                )
                return True
            else:
                self.add_result(
                    "Start Project from Inspiration",
                    False,
                    f"Failed with status {response.status_code}",
                    {'response': response.text}
                )
                return False
        except Exception as e:
            self.add_result("Start Project from Inspiration", False, f"Error: {str(e)}")
            return False

    def test_verify_project_creation(self):
        """Verify project was created correctly in database"""
        self.log("Verifying project creation in database...")

        if not self.test_project_id:
            self.add_result("Verify Project Creation", False, "No project ID available")
            return False

        try:
            project = NovelProject.objects.get(id=self.test_project_id)
            chapter = Chapter.objects.filter(project=project, chapter_number=1).first()

            checks = {
                'project_exists': project is not None,
                'project_status': project.status == 'active',
                'has_outline': bool(project.outline),
                'current_chapter': project.current_chapter == 1,
                'chapter_exists': chapter is not None,
                'chapter_status': chapter.status == 'pending_review' if chapter else False,
                'has_content': bool(chapter.raw_content) if chapter else False
            }

            all_passed = all(checks.values())
            self.add_result(
                "Verify Project Creation",
                all_passed,
                f"Database verification: {sum(checks.values())}/{len(checks)} checks passed",
                checks
            )
            return all_passed
        except Exception as e:
            self.add_result("Verify Project Creation", False, f"Error: {str(e)}")
            return False

    # ========== Test 3: Automatic Chapter Generation ==========

    def test_generate_next_chapter_async(self):
        """Test async chapter generation"""
        self.log("Testing async chapter generation...")

        if not self.test_project_id:
            self.add_result("Generate Next Chapter Async", False, "No project ID available")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/api/chapters/generate-async/",
                json={
                    'project_id': self.test_project_id,
                    'chapter_number': 2,
                    'chapter_title': '第二章：初试身手'
                },
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 202:
                data = response.json()
                self.test_task_id = data.get('task_id')
                task_record_id = data.get('task_record_id')

                self.add_result(
                    "Generate Next Chapter Async",
                    True,
                    f"Task submitted with ID {self.test_task_id}",
                    {
                        'task_id': self.test_task_id,
                        'task_record_id': task_record_id,
                        'status': data.get('status')
                    }
                )
                return True
            else:
                self.add_result(
                    "Generate Next Chapter Async",
                    False,
                    f"Failed with status {response.status_code}",
                    {'response': response.text}
                )
                return False
        except Exception as e:
            self.add_result("Generate Next Chapter Async", False, f"Error: {str(e)}")
            return False

    def test_check_task_status(self):
        """Test task status checking"""
        self.log("Testing task status API...")

        if not self.test_task_id:
            self.add_result("Check Task Status", False, "No task ID available")
            return False

        try:
            # Wait a bit for task to process
            time.sleep(2)

            response = requests.get(
                f"{self.base_url}/api/tasks/{self.test_task_id}/status/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                task_status = data.get('status')
                task_record = data.get('task_record', {})

                self.add_result(
                    "Check Task Status",
                    True,
                    f"Task status: {task_status}",
                    {
                        'celery_status': task_status,
                        'task_record': task_record
                    }
                )
                return True
            else:
                self.add_result(
                    "Check Task Status",
                    False,
                    f"Failed with status {response.status_code}"
                )
                return False
        except Exception as e:
            self.add_result("Check Task Status", False, f"Error: {str(e)}")
            return False

    def test_verify_chapter_generation(self):
        """Verify chapter was generated successfully"""
        self.log("Verifying chapter generation...")

        if not self.test_project_id:
            self.add_result("Verify Chapter Generation", False, "No project ID available")
            return False

        try:
            # Wait for generation to complete (mock mode should be fast)
            max_wait = 30
            waited = 0
            chapter = None

            while waited < max_wait:
                chapter = Chapter.objects.filter(
                    project_id=self.test_project_id,
                    chapter_number=2
                ).first()

                if chapter and chapter.status != 'generating':
                    break

                time.sleep(2)
                waited += 2

            if chapter:
                success = chapter.status in ['pending_review', 'approved']
                self.add_result(
                    "Verify Chapter Generation",
                    success,
                    f"Chapter 2 status: {chapter.status}, word count: {chapter.word_count}",
                    {
                        'chapter_id': chapter.id,
                        'status': chapter.status,
                        'word_count': chapter.word_count,
                        'has_content': bool(chapter.raw_content)
                    }
                )
                return success
            else:
                self.add_result(
                    "Verify Chapter Generation",
                    False,
                    "Chapter 2 not found after waiting"
                )
                return False
        except Exception as e:
            self.add_result("Verify Chapter Generation", False, f"Error: {str(e)}")
            return False

    # ========== Test 4: Chapter Editing ==========

    def test_get_chapter_detail(self):
        """Test retrieving chapter details"""
        self.log("Testing chapter detail API...")

        if not self.test_chapter_id:
            self.add_result("Get Chapter Detail", False, "No chapter ID available")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/chapters/{self.test_chapter_id}/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.add_result(
                    "Get Chapter Detail",
                    True,
                    f"Retrieved chapter: {data.get('title')}",
                    {
                        'id': data.get('id'),
                        'title': data.get('title'),
                        'status': data.get('status'),
                        'word_count': data.get('word_count')
                    }
                )
                return True
            else:
                self.add_result(
                    "Get Chapter Detail",
                    False,
                    f"Failed with status {response.status_code}"
                )
                return False
        except Exception as e:
            self.add_result("Get Chapter Detail", False, f"Error: {str(e)}")
            return False

    def test_edit_chapter_content(self):
        """Test editing chapter content"""
        self.log("Testing chapter editing...")

        if not self.test_chapter_id:
            self.add_result("Edit Chapter Content", False, "No chapter ID available")
            return False

        try:
            # Get current chapter
            chapter = Chapter.objects.get(id=self.test_chapter_id)
            original_content = chapter.final_content or chapter.raw_content

            # Modify content (simulate manual editing)
            modified_content = original_content + "\n\n【人工修改】这是经过人工审核和修改的内容。"

            response = requests.patch(
                f"{self.base_url}/api/chapters/{self.test_chapter_id}/",
                json={
                    'final_content': modified_content,
                    'status': 'approved'
                },
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.add_result(
                    "Edit Chapter Content",
                    data.get('status') == 'approved',
                    f"Chapter updated to status: {data.get('status')}",
                    {
                        'id': data.get('id'),
                        'status': data.get('status'),
                        'content_modified': len(modified_content) > len(original_content)
                    }
                )
                return True
            else:
                self.add_result(
                    "Edit Chapter Content",
                    False,
                    f"Failed with status {response.status_code}",
                    {'response': response.text}
                )
                return False
        except Exception as e:
            self.add_result("Edit Chapter Content", False, f"Error: {str(e)}")
            return False

    # ========== Test 5: Publishing (Simulated) ==========

    def test_publish_chapter_simulation(self):
        """Test chapter publishing (simulated)"""
        self.log("Testing chapter publishing simulation...")

        if not self.test_chapter_id:
            self.add_result("Publish Chapter Simulation", False, "No chapter ID available")
            return False

        try:
            # In real scenario, this would trigger browser automation
            # For testing, we just update the status
            chapter = Chapter.objects.get(id=self.test_chapter_id)

            if chapter.status != 'approved':
                self.add_result(
                    "Publish Chapter Simulation",
                    False,
                    f"Chapter must be approved before publishing, current status: {chapter.status}"
                )
                return False

            # Simulate publishing
            chapter.status = 'published'
            chapter.published_at = datetime.now()
            chapter.tomato_chapter_id = f"mock_chapter_{chapter.id}"
            chapter.save()

            self.add_result(
                "Publish Chapter Simulation",
                True,
                f"Chapter marked as published with mock ID: {chapter.tomato_chapter_id}",
                {
                    'chapter_id': chapter.id,
                    'status': chapter.status,
                    'published_at': chapter.published_at.isoformat(),
                    'tomato_chapter_id': chapter.tomato_chapter_id
                }
            )
            return True
        except Exception as e:
            self.add_result("Publish Chapter Simulation", False, f"Error: {str(e)}")
            return False

    def test_verify_publish_status(self):
        """Verify publishing status update"""
        self.log("Verifying publish status...")

        if not self.test_chapter_id:
            self.add_result("Verify Publish Status", False, "No chapter ID available")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/chapters/{self.test_chapter_id}/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                is_published = data.get('status') == 'published'
                has_publish_time = bool(data.get('published_at'))
                has_tomato_id = bool(data.get('tomato_chapter_id'))

                all_checks = is_published and has_publish_time and has_tomato_id

                self.add_result(
                    "Verify Publish Status",
                    all_checks,
                    f"Published: {is_published}, Has timestamp: {has_publish_time}, Has tomato ID: {has_tomato_id}",
                    {
                        'status': data.get('status'),
                        'published_at': data.get('published_at'),
                        'tomato_chapter_id': data.get('tomato_chapter_id')
                    }
                )
                return all_checks
            else:
                self.add_result("Verify Publish Status", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("Verify Publish Status", False, f"Error: {str(e)}")
            return False

    # ========== Test 6: Task Monitoring ==========

    def test_list_tasks(self):
        """Test task list API"""
        self.log("Testing task list API...")

        try:
            response = requests.get(
                f"{self.base_url}/api/tasks/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                self.add_result(
                    "List Tasks",
                    len(results) > 0,
                    f"Retrieved {len(results)} tasks",
                    {
                        'count': data.get('count', 0),
                        'results_count': len(results)
                    }
                )
                return len(results) > 0
            else:
                self.add_result("List Tasks", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("List Tasks", False, f"Error: {str(e)}")
            return False

    def test_filter_tasks_by_status(self):
        """Test filtering tasks by status"""
        self.log("Testing task filtering by status...")

        try:
            response = requests.get(
                f"{self.base_url}/api/tasks/?status=success",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                all_success = all(task.get('status') == 'success' for task in results)

                self.add_result(
                    "Filter Tasks by Status",
                    True,
                    f"Retrieved {len(results)} tasks with status filter",
                    {
                        'count': len(results),
                        'all_match_filter': all_success
                    }
                )
                return True
            else:
                self.add_result("Filter Tasks by Status", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("Filter Tasks by Status", False, f"Error: {str(e)}")
            return False

    def test_filter_tasks_by_type(self):
        """Test filtering tasks by type"""
        self.log("Testing task filtering by type...")

        try:
            response = requests.get(
                f"{self.base_url}/api/tasks/?task_type=generate_chapter",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                all_match = all(task.get('task_type') == 'generate_chapter' for task in results)

                self.add_result(
                    "Filter Tasks by Type",
                    True,
                    f"Retrieved {len(results)} generate_chapter tasks",
                    {
                        'count': len(results),
                        'all_match_filter': all_match
                    }
                )
                return True
            else:
                self.add_result("Filter Tasks by Type", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("Filter Tasks by Type", False, f"Error: {str(e)}")
            return False

    # ========== Test 7: Additional API Tests ==========

    def test_list_projects(self):
        """Test project list API"""
        self.log("Testing project list API...")

        try:
            response = requests.get(
                f"{self.base_url}/api/novels/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', []) if isinstance(data, dict) else data
                self.add_result(
                    "List Projects",
                    len(results) > 0,
                    f"Retrieved {len(results)} projects",
                    {'count': len(results)}
                )
                return len(results) > 0
            else:
                self.add_result("List Projects", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("List Projects", False, f"Error: {str(e)}")
            return False

    def test_list_chapters(self):
        """Test chapter list API"""
        self.log("Testing chapter list API...")

        try:
            response = requests.get(
                f"{self.base_url}/api/chapters/?project_id={self.test_project_id}",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', []) if isinstance(data, dict) else data
                self.add_result(
                    "List Chapters",
                    len(results) > 0,
                    f"Retrieved {len(results)} chapters for project {self.test_project_id}",
                    {'count': len(results)}
                )
                return len(results) > 0
            else:
                self.add_result("List Chapters", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("List Chapters", False, f"Error: {str(e)}")
            return False

    def test_user_stats(self):
        """Test user statistics API"""
        self.log("Testing user stats API...")

        try:
            response = requests.get(
                f"{self.base_url}/api/users/stats/",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.add_result(
                    "User Stats",
                    True,
                    f"Projects: {data.get('project_count')}, Chapters: {data.get('chapter_count')}, Words: {data.get('total_word_count')}",
                    data
                )
                return True
            else:
                self.add_result("User Stats", False, f"Failed with status {response.status_code}")
                return False
        except Exception as e:
            self.add_result("User Stats", False, f"Error: {str(e)}")
            return False

    # ========== Test Runner ==========

    def run_all_tests(self):
        """Run all workflow tests"""
        self.log("=" * 80)
        self.log("Starting Full Workflow Test Suite")
        self.log("=" * 80)

        # Setup
        if not self.setup_test_user():
            self.log("Failed to setup test user, aborting", "ERROR")
            return False

        if not self.login():
            self.log("Failed to login, aborting", "ERROR")
            return False

        # Test 1: Inspiration Generation
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 1: Inspiration Generation")
        self.log("=" * 80)
        self.test_create_sample_inspirations()
        self.test_generate_inspiration_from_trends()
        self.test_list_inspirations()

        # Test 2: Project Startup
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 2: Project Startup")
        self.log("=" * 80)
        self.test_start_project_from_inspiration()
        self.test_verify_project_creation()

        # Test 3: Automatic Chapter Generation
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 3: Automatic Chapter Generation")
        self.log("=" * 80)
        self.test_generate_next_chapter_async()
        self.test_check_task_status()
        self.test_verify_chapter_generation()

        # Test 4: Chapter Editing
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 4: Chapter Editing")
        self.log("=" * 80)
        self.test_get_chapter_detail()
        self.test_edit_chapter_content()

        # Test 5: Publishing
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 5: Publishing (Simulated)")
        self.log("=" * 80)
        self.test_publish_chapter_simulation()
        self.test_verify_publish_status()

        # Test 6: Task Monitoring
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 6: Task Monitoring")
        self.log("=" * 80)
        self.test_list_tasks()
        self.test_filter_tasks_by_status()
        self.test_filter_tasks_by_type()

        # Test 7: Additional APIs
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE 7: Additional API Tests")
        self.log("=" * 80)
        self.test_list_projects()
        self.test_list_chapters()
        self.test_user_stats()

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate test report"""
        self.log("\n" + "=" * 80)
        self.log("TEST REPORT")
        self.log("=" * 80)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        self.log(f"\nTotal Tests: {total}")
        self.log(f"Passed: {passed} ({passed/total*100:.1f}%)")
        self.log(f"Failed: {failed} ({failed/total*100:.1f}%)")

        if failed > 0:
            self.log("\n" + "-" * 80)
            self.log("FAILED TESTS:")
            self.log("-" * 80)
            for result in self.results:
                if not result.passed:
                    self.log(f"✗ {result.name}: {result.message}")

        self.log("\n" + "-" * 80)
        self.log("DETAILED RESULTS:")
        self.log("-" * 80)

        for result in self.results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            self.log(f"{status} | {result.name}")
            self.log(f"       {result.message}")
            if result.details:
                self.log(f"       Details: {json.dumps(result.details, indent=8, ensure_ascii=False)}")

        # Save report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{passed/total*100:.1f}%"
            },
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'details': r.details,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self.log(f"\nDetailed report saved to: {report_file}")
        self.log("=" * 80)

        return passed == total


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='TomatoFiction Full Workflow Test')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Django backend URL')
    parser.add_argument('--fastapi-url', default='http://localhost:8001', help='FastAPI service URL')
    args = parser.parse_args()

    tester = WorkflowTester(base_url=args.base_url, fastapi_url=args.fastapi_url)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

