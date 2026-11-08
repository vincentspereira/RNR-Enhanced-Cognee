"""Collect the 123 copied cases without changing their source-root calculation."""
import hashlib as _hashlib
from pathlib import Path as _Path

_root = _Path(__file__).resolve().parents[5]
_original = _root / "tests/unit/test_security_first_cutover.py"
_copy = _Path(__file__).resolve().parent / "copied-original-cases.py"
assert _hashlib.sha256(_copy.read_bytes()).hexdigest() == "1d32c2528b1f860f5ae495f3606e7496c720fba463f5ae617345b23f65c1f213"
_actual_file = __file__
__file__ = str(_original)
try:
    exec(compile(_copy.read_text("ascii"), str(_copy), "exec"), globals())
finally:
    __file__ = _actual_file
assert _hashlib.sha256(HELPER.read_bytes()).hexdigest() == "d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
