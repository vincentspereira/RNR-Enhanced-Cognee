#!/usr/bin/env python
"""
Fix datetime.utcnow() deprecation warnings
Replaces datetime.utcnow() with datetime.now(datetime.UTC)
"""
import re
from pathlib import Path

def fix_datetime_utcnow(file_path):
    """Fix datetime.utcnow() in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Check if datetime is imported and add UTC if needed
        if 'from datetime import' in content and 'datetime.utcnow()' in content:
            # Add UTC to imports if not already present
            if ' UTC' not in content and 'timezone' not in content:
                # Find the datetime import line
                import_pattern = r'(from datetime import [^\n]+)'
                matches = list(re.finditer(import_pattern, content))

                for match in reversed(matches):  # Process in reverse to maintain positions
                    import_line = match.group(1)
                    if 'datetime' in import_line and 'UTC' not in import_line:
                        # Add UTC to the import
                        new_import_line = import_line.replace('from datetime import ', 'from datetime import UTC, ') if import_line == 'from datetime import datetime' else import_line.rstrip() + ', UTC'
                        content = content[:match.start()] + new_import_line + content[match.end():]

        # Replace datetime.utcnow() with datetime.now(UTC)
        content = content.replace('datetime.utcnow()', 'datetime.now(UTC)')

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all Python files"""
    project_root = Path(__file__).parent

    # Files to fix
    files_to_fix = [
        # Test files
        'tests/e2e/test_complete_workflows.py',
        'tests/integration/test_database_integration.py',

        # Source files
        'src/agents/ats/algorithmic_trading_system.py',
        'src/agents/ats/ats_memory_wrapper.py',
        'src/agents/ats/risk_management.py',
        'src/agents/oma/code_reviewer.py',
        'src/agents/smc/context_manager.py',
        'src/agents/smc/smc_memory_wrapper.py',
        'src/coordination/coordination_api.py',
        'src/coordination/distributed_decision.py',
        'src/coordination/sub_agent_coordinator.py',
        'src/coordination/task_orchestration.py',
        'src/integration/sdlc_integration.py',
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        full_path = project_root / file_path
        if full_path.exists():
            if fix_datetime_utcnow(full_path):
                print(f"[OK] Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"[SKIP] No changes needed: {file_path}")
        else:
            print(f"[NOT FOUND] {file_path}")

    print(f"\n[COMPLETE] Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
