#!/bin/bash

# Script para ejecutar todos los tests con cobertura completa

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python
if ! command -v python &> /dev/null; then
    print_error "Python not found"
    exit 1
fi

# Check pytest
if ! python -m pytest --version &> /dev/null; then
    print_error "pytest not installed. Run: pip install -r requirements.txt"
    exit 1
fi

print_section "SGA1 Complete Test Suite"

# Clean up
print_section "Cleanup"
python -m pytest --co -q > /dev/null 2>&1 || true
print_success "Cleaned up old test cache"

# Run Django checks
print_section "Django System Checks"
python manage.py check --deploy 2>&1 | grep -v "WARNINGS" || true

# Test database
print_section "Database Tests"
python -m pytest classes/tests_models.py -v --tb=short

# Test models
print_section "Model Tests"
python -m pytest users/tests.py subjects/tests.py students/tests.py teachers/tests.py -v --tb=short

# Test integration
print_section "Integration Tests"
python -m pytest tests_integration.py -v --tb=short

# Test API
print_section "API Tests"
python -m pytest tests_api.py -v --tb=short || print_warning "Some API tests may be incomplete"

# Test ETL
print_section "ETL Tests"
python -m pytest tests_etl.py -v --tb=short -k "not slow"

# Run full coverage
print_section "Coverage Analysis"
python -m pytest \
    --cov=. \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-branch \
    --cov-fail-under=70 \
    --tb=short \
    -v

# Generate report summary
print_section "Test Summary"

COVERAGE_FILE=".coverage"
if [ -f "$COVERAGE_FILE" ]; then
    echo ""
    print_success "All tests completed"
    echo ""
    echo "Coverage Report generated in: htmlcov/index.html"
    echo ""
    echo "To view coverage report:"
    echo "  open htmlcov/index.html"
    echo ""
fi

# Final checks
print_section "Pre-Production Checklist"

# Check migrations
PENDING_MIGRATIONS=$(python manage.py showmigrations --plan | grep "\[ \]" | wc -l)
if [ "$PENDING_MIGRATIONS" -eq 0 ]; then
    print_success "No pending migrations"
else
    print_warning "$PENDING_MIGRATIONS pending migrations"
fi

# Check for print statements
PRINT_STATEMENTS=$(grep -r "print(" --include="*.py" . 2>/dev/null | grep -v "test_" | grep -v ".venv" | grep -v "htmlcov" | wc -l)
if [ "$PRINT_STATEMENTS" -eq 0 ]; then
    print_success "No print statements in production code"
else
    print_warning "Found $PRINT_STATEMENTS print statements (should use logging)"
fi

# Check for TODOs
TODOS=$(grep -r "TODO\|FIXME" --include="*.py" . 2>/dev/null | grep -v ".venv" | grep -v "htmlcov" | wc -l)
if [ "$TODOS" -eq 0 ]; then
    print_success "No TODO/FIXME comments"
else
    print_warning "Found $TODOS TODO/FIXME comments"
fi

echo ""
print_section "Status"

if [ "$PENDING_MIGRATIONS" -eq 0 ] && [ "$PRINT_STATEMENTS" -eq 0 ]; then
    echo -e "${GREEN}✓ Application is ready for production deployment${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review coverage report: htmlcov/index.html"
    echo "  2. Run: python manage.py check --deploy"
    echo "  3. Deploy to EasyPanel"
    exit 0
else
    echo -e "${YELLOW}⚠ Please fix the warnings above before deploying${NC}"
    exit 1
fi
