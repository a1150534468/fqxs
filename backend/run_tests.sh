#!/bin/bash
# Quick test runner with service checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "TomatoFiction Workflow Test Runner"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Django is running
echo -n "Checking Django backend (port 8000)... "
if curl -s http://localhost:8000/api/users/login/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    DJANGO_OK=1
else
    echo -e "${RED}✗ Not running${NC}"
    DJANGO_OK=0
fi

# Check if FastAPI is running
echo -n "Checking FastAPI service (port 8001)... "
if curl -s http://localhost:8001/health > /dev/null 2>&1 || curl -s http://localhost:8001/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    FASTAPI_OK=1
else
    echo -e "${YELLOW}⚠ Not running (some tests may fail)${NC}"
    FASTAPI_OK=0
fi

# Check if Celery is running (optional)
echo -n "Checking Celery worker... "
if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    CELERY_OK=1
else
    echo -e "${YELLOW}⚠ Not running (async tests may fail)${NC}"
    CELERY_OK=0
fi

echo ""

# Exit if Django is not running
if [ $DJANGO_OK -eq 0 ]; then
    echo -e "${RED}ERROR: Django backend is not running!${NC}"
    echo ""
    echo "Please start Django backend first:"
    echo "  cd $SCRIPT_DIR"
    echo "  python manage.py runserver"
    echo ""
    exit 1
fi

# Warn if FastAPI is not running
if [ $FASTAPI_OK -eq 0 ]; then
    echo -e "${YELLOW}WARNING: FastAPI service is not running.${NC}"
    echo "Some tests may fail. To start FastAPI:"
    echo "  cd $SCRIPT_DIR/../fastapi_service"
    echo "  uvicorn main:app --host 0.0.0.0 --port 8001"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
echo "=========================================="
echo "Running Tests..."
echo "=========================================="
echo ""

python test_full_workflow.py "$@"

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed.${NC}"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
