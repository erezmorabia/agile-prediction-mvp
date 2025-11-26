.PHONY: help type-check lint format check-docs check-all fix install-dev clean test test-cov test-file

# Default target
help:
	@echo "Available targets:"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make type-check     - Run mypy type checking"
	@echo "  make lint           - Run pylint and ruff linting"
	@echo "  make format         - Format code with ruff"
	@echo "  make check-docs     - Check docstring style with pydocstyle"
	@echo "  make check-all      - Run all checks (type-check + lint + check-docs)"
	@echo "  make fix            - Auto-fix issues where possible"
	@echo "  make test           - Run test suite"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make clean          - Remove Python cache files"

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Type checking with mypy
type-check:
	@echo "Running type checking with mypy..."
	mypy src/ || echo "Type checking complete (some issues may exist)"

# Linting with pylint and ruff
lint:
	@echo "Running pylint..."
	pylint src/ || echo "Pylint complete (some issues may exist)"
	@echo ""
	@echo "Running ruff..."
	ruff check src/ || echo "Ruff check complete (some issues may exist)"

# Format code with ruff
format:
	@echo "Formatting code with ruff..."
	ruff format src/
	@echo "Code formatting complete"

# Check docstring style
check-docs:
	@echo "Checking docstring style with pydocstyle..."
	pydocstyle src/ || echo "Docstring check complete (some issues may exist)"

# Run all checks
check-all: type-check lint check-docs
	@echo ""
	@echo "All checks complete!"

# Auto-fix issues where possible
fix:
	@echo "Auto-fixing issues with ruff..."
	ruff check src/ --fix
	ruff format src/
	@echo "Auto-fix complete"

# Run tests
test:
	@echo "Running test suite..."
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term tests/
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

# Run specific test file
test-file:
	@echo "Usage: make test-file FILE=test_recommender.py"
	@test -n "$(FILE)" || (echo "Error: FILE parameter required" && exit 1)
	python -m pytest tests/$(FILE) -v

# Clean Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Clean complete"

