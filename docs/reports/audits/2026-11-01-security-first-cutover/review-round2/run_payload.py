"""Reuse the preserved runner with a new explicit payload-only inventory."""
from pathlib import Path
import sys

path = Path(__file__).resolve().parent / 'run_review.py'
source = path.read_text('ascii')
assert source.count("elif mode == 'fresh':") == 1
assert source.count("OUT / 'test_fresh_challenges.py'") == 1
source = source.replace("elif mode == 'fresh':", "elif mode == 'payload':").replace("OUT / 'test_fresh_challenges.py'", "OUT / 'test_payload_reader.py'")
sys.argv = [str(path), 'payload']
exec(compile(source, str(path), 'exec'), dict(__file__=str(path), __name__='__main__'))
