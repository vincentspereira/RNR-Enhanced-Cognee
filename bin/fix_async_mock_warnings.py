#!/usr/bin/env python
"""
Fix AsyncMock RuntimeWarnings in test files
Replaces incorrect mock_pool.acquire patterns with proper async context managers
"""
import re
from pathlib import Path

def fix_async_context_manager(file_path):
    """Fix async context manager mocking in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Add helper function if not present (at the top after imports)
        if 'def create_mock_acquire_context' not in content:
            # Find the location after imports
            import_end = content.find('\n\n', content.find('from unittest.mock import'))
            if import_end == -1:
                import_end = content.find('\n\n', content.find('import unittest'))
                if import_end == -1:
                    import_end = 0

            helper_function = '''
# Helper for async context manager mocking
def create_mock_acquire_context(mock_conn):
    """Create a proper async context manager for postgres_pool.acquire()"""
    class MockAcquireContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass
    return MockAcquireContext()

'''
            content = content[:import_end + 2] + helper_function + content[import_end + 2:]

        # Fix pattern 1: mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        # Replace with: mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)
        pattern1 = r'mock_pool\.acquire\.return_value\.__aenter__\.return_value = mock_conn'
        replacement1 = 'mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)'
        content = re.sub(pattern1, replacement1, content)

        # Fix pattern 2: server.postgres_pool.acquire.return_value = mock_conn
        pattern2 = r'server\.postgres_pool\.acquire\.return_value = mock_conn'
        replacement2 = 'server.postgres_pool.acquire = lambda: create_mock_acquire_context(mock_conn)'
        content = re.sub(pattern2, replacement2, content)

        # Fix pattern 3: mock_pool.acquire = AsyncMock(return_value=mock_conn)
        pattern3 = r'mock_pool\.acquire = AsyncMock\(return_value=mock_conn\)'
        replacement3 = 'mock_pool.acquire = lambda: create_mock_acquire_context(mock_conn)'
        content = re.sub(pattern3, replacement3, content)

        # Fix pattern 4: pool.acquire.return_value.__aenter__.return_value = mock_conn
        pattern4 = r'pool\.acquire\.return_value\.__aenter__\.return_value = mock_conn'
        replacement4 = 'pool.acquire = lambda: create_mock_acquire_context(mock_conn)'
        content = re.sub(pattern4, replacement4, content)

        # Fix pattern 5: postgres_pool.acquire.return_value.__aenter__.return_value = mock_conn
        pattern5 = r'postgres_pool\.acquire\.return_value\.__aenter__\.return_value = mock_conn'
        replacement5 = 'postgres_pool.acquire = lambda: create_mock_acquire_context(mock_conn)'
        content = re.sub(pattern5, replacement5, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all Python test files"""
    project_root = Path(__file__).parent

    # Files to fix
    files_to_fix = [
        'tests/test_e2e_scenarios.py',
        'tests/test_multi_language_integration.py',
        'tests/test_performance_optimizer.py',
        'tests/test_system_workflows.py',
        'tests/unit/test_memory_management.py',
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            if fix_async_context_manager(full_path):
                print(f"[OK] Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"[SKIP] No changes needed: {file_path}")
        else:
            print(f"[NOT FOUND] {file_path}")

    print(f"\n[COMPLETE] Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
