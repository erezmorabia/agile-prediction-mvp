#!/usr/bin/env python3
"""
Create a clean zip file for university submission.

This script creates a zip file containing all essential project files,
excluding cache files, virtual environments, and IDE-specific files.
"""
import os
import zipfile
from pathlib import Path
from fnmatch import fnmatch


def should_exclude(file_path: Path, exclude_patterns: list) -> bool:
    """
    Check if a file should be excluded based on patterns.
    
    Args:
        file_path: Path object to check
        exclude_patterns: List of patterns to exclude
        
    Returns:
        True if file should be excluded, False otherwise
    """
    file_str = str(file_path)
    
    # Check each pattern
    for pattern in exclude_patterns:
        # Handle directory patterns (ends with /)
        if pattern.endswith('/'):
            if pattern.rstrip('/') in file_str:
                return True
        # Handle wildcard patterns
        elif '*' in pattern or '?' in pattern:
            if fnmatch(file_path.name, pattern) or fnmatch(file_str, pattern):
                return True
        # Exact match
        else:
            if pattern in file_str or file_path.name == pattern:
                return True
    
    return False


def create_submission_zip():
    """Create a zip file with all project files, excluding unnecessary ones."""
    
    # Files/directories to exclude
    exclude_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        '.git',
        'venv',
        '.venv',
        'env',
        '.env',
        'ENV',
        '.vscode',
        '.idea',
        '*.swp',
        '*.swo',
        '*~',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
        '*.log',
        '*.egg-info',
        'dist',
        'build',
        '.mypy_cache',
        '.dmypy.json',
        'dmypy.json',
        '.ipynb_checkpoints',
        # Exclude the zip file itself if it exists
        'agile-prediction-mvp-submission.zip',
    ]
    
    project_root = Path('.')
    zip_path = project_root / 'agile-prediction-mvp-submission.zip'
    
    # Remove existing zip if present
    if zip_path.exists():
        print(f"Removing existing zip file: {zip_path}")
        zip_path.unlink()
    
    files_added = 0
    files_excluded = 0
    
    print("Creating submission zip file...")
    print("-" * 60)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in the project
        for file_path in project_root.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip if file should be excluded
            if should_exclude(file_path, exclude_patterns):
                files_excluded += 1
                continue
            
            # Add file to zip with relative path
            try:
                arcname = file_path.relative_to(project_root)
                zipf.write(file_path, arcname)
                files_added += 1
                print(f"  ✓ Added: {arcname}")
            except Exception as e:
                print(f"  ✗ Error adding {file_path}: {e}")
    
    print("-" * 60)
    print(f"\n✓ Created: {zip_path}")
    print(f"  Files added: {files_added}")
    print(f"  Files excluded: {files_excluded}")
    print(f"  Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"\nZip file is ready for submission!")


if __name__ == '__main__':
    create_submission_zip()

