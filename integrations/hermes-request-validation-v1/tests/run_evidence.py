"""Run synthetic suite and preserve immutable step evidence outside the checkout."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path('/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/native-adapter')
label = sys.argv[1]
EVIDENCE.mkdir(parents=True, exist_ok=True)
if (EVIDENCE / (label + '.txt')).exists():
    raise SystemExit('Evidence label already exists; choose a new label')
result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(ROOT / 'integrations/hermes/tests'), '-v'], capture_output=True, text=True)
text = result.stdout + result.stderr + '\nexit_code=' + str(result.returncode) + '\n'
(EVIDENCE / (label + '.txt')).write_text(text)
shutil.copytree(ROOT / 'integrations/hermes', EVIDENCE / (label + '-source'), ignore=shutil.ignore_patterns('__pycache__'), dirs_exist_ok=False)
print(text)
raise SystemExit(result.returncode)
