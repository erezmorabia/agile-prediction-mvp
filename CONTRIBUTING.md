# Contributing Guide

Thank you for your interest in contributing to the Agile Practice Prediction MVP!

## Development Setup

### 1. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Run Code Quality Checks

Before submitting code, ensure all checks pass:

```bash
# Run all checks
make check-all

# Or individually:
make type-check    # Type checking
make lint          # Linting
make check-docs    # Docstring validation
make format        # Code formatting
```

## Code Quality Standards

### Type Hints

- Add type hints to function signatures where possible
- Use `typing` module for complex types (List, Dict, Optional, etc.)
- Type checking is gradual - not all code needs types initially

### Docstrings

- Use Google-style docstrings (matches current codebase)
- Include: brief description, Args, Returns, Raises, Examples, Notes
- All public functions should have docstrings

### Code Style

- Follow PEP 8 with 120 character line length
- Use `ruff format` to auto-format code
- Run `ruff check` to catch style issues

### Linting

- Fix all critical linting issues (errors)
- Address warnings where reasonable
- Use `ruff check --fix` to auto-fix safe issues

## Pre-Commit Checklist

Before committing code:

- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Type checking passes: `make type-check`
- [ ] Linting passes: `make lint`
- [ ] Docstrings validated: `make check-docs`
- [ ] Code formatted: `make format`
- [ ] No obvious bugs introduced

## Common Issues and Fixes

### Type Checking Errors

**Issue:** `mypy` reports missing type hints
**Fix:** Add type hints gradually - start with public APIs, add more over time

**Issue:** `mypy` can't find third-party imports
**Fix:** Already configured in `mypy.ini` - third-party packages are ignored

### Linting Errors

**Issue:** Line too long (>120 characters)
**Fix:** Run `ruff format` to auto-format, or break line manually

**Issue:** Unused imports
**Fix:** Run `ruff check --fix` to auto-remove, or remove manually

**Issue:** Variable naming (snake_case required)
**Fix:** Rename variables to follow snake_case convention

### Docstring Errors

**Issue:** Missing docstring
**Fix:** Add Google-style docstring with Args/Returns sections

**Issue:** Incorrect docstring format
**Fix:** Follow Google convention - see existing docstrings for examples

## Running Checks Locally

### Quick Check (Non-Blocking)

```bash
# See issues without failing
make type-check || echo "Type check complete (some issues found)"
make lint || echo "Linting complete (some issues found)"
```

### Full Check (Strict)

```bash
# All checks must pass
make check-all
```

### Auto-Fix Issues

```bash
# Auto-fix safe issues
make fix

# Or manually:
ruff check src/ --fix
ruff format src/
```

## CI/CD

GitHub Actions automatically runs checks on:
- Push to main/master/develop branches
- Pull requests

Checks are currently non-blocking (`continue-on-error: true`) to allow gradual adoption. After initial cleanup, they can be made required.

## Adding New Code

When adding new features:

1. **Write tests first** (if applicable)
2. **Add type hints** to function signatures
3. **Add docstrings** following Google convention
4. **Run checks** before committing
5. **Update documentation** if needed

## Documentation

- Code docstrings: Google-style in source files
- User documentation: README.md, QUICK_START.md
- API documentation: Auto-generated from docstrings (FastAPI)

## Questions?

- Check existing code for examples
- Review docstrings in similar modules
- Run `help(function_name)` in Python REPL

## Gradual Adoption

The codebase may have existing issues. That's OK! We're adopting these tools gradually:

1. **Initial**: Run checks to see issues (non-blocking)
2. **Fix Critical**: Address type errors and critical bugs first
3. **Iterative**: Fix issues incrementally over time
4. **Strict**: Enable strict checking after cleanup

Thank you for contributing! 🎉

