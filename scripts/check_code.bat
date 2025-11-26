@echo off
REM Cross-platform script to run all code quality checks (Windows version)
REM Usage: scripts\check_code.bat [type-check|lint|format|check-docs|check-all|fix]

setlocal enabledelayedexpansion

REM Get the command (default to check-all)
set CMD=%1
if "%CMD%"=="" set CMD=check-all

if "%CMD%"=="type-check" goto type_check
if "%CMD%"=="lint" goto lint
if "%CMD%"=="format" goto format
if "%CMD%"=="check-docs" goto check_docs
if "%CMD%"=="check-all" goto check_all
if "%CMD%"=="fix" goto fix
goto usage

:type_check
echo [INFO] Running type checking with mypy...
mypy src/ || echo [WARN] Type checking found some issues
goto end

:lint
echo [INFO] Running linting checks...
ruff check src/ || echo [WARN] Ruff found some issues
pylint src/ || echo [WARN] Pylint found some issues
goto end

:format
echo [INFO] Formatting code with ruff...
ruff format src/
echo [INFO] Code formatting complete
goto end

:check_docs
echo [INFO] Checking docstring style with pydocstyle...
pydocstyle src/ || echo [WARN] Docstring check found some issues
goto end

:check_all
echo [INFO] Running all code quality checks...
call %0 type-check || echo.
call %0 lint || echo.
call %0 check-docs || echo.
echo [INFO] All checks complete!
goto end

:fix
echo [INFO] Auto-fixing issues with ruff...
ruff check src/ --fix
ruff format src/
echo [INFO] Auto-fix complete
goto end

:usage
echo [ERROR] Unknown command: %CMD%
echo Usage: %0 [type-check^|lint^|format^|check-docs^|check-all^|fix]
exit /b 1

:end
endlocal

