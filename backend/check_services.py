#!/usr/bin/env python3
"""
Quick service status checker for TomatoFiction platform
Run this before executing tests to ensure all services are ready
"""

import sys
import requests
from datetime import datetime


def check_service(name, url, timeout=5):
    """Check if a service is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code < 500:
            print(f"✓ {name:20s} - Running (status {response.status_code})")
            return True
        else:
            print(f"✗ {name:20s} - Error (status {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ {name:20s} - Not running (connection refused)")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ {name:20s} - Timeout")
        return False
    except Exception as e:
        print(f"✗ {name:20s} - Error: {str(e)}")
        return False


def main():
    print("=" * 60)
    print("TomatoFiction Service Status Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    services = [
        ("Django Backend", "http://localhost:8000/api/users/login/"),
        ("FastAPI Service", "http://localhost:8001/docs"),
        ("FastAPI Health", "http://localhost:8001/health"),
    ]

    results = []
    for name, url in services:
        results.append(check_service(name, url))

    print()
    print("=" * 60)

    if all(results[:2]):  # Django and FastAPI main endpoints
        print("✓ All critical services are running")
        print("Ready to run tests!")
        return 0
    else:
        print("✗ Some services are not running")
        print()
        print("To start services:")
        print("  Django:  cd backend && python manage.py runserver")
        print("  FastAPI: cd fastapi_service && uvicorn main:app --port 8001")
        return 1


if __name__ == '__main__':
    sys.exit(main())
