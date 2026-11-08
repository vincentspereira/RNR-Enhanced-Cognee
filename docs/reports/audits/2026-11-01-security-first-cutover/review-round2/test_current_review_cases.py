"""Replay all 50 reviewer logical cases with explicit repaired source bindings.

The copied bodies retain every original assertion. S01 and L02 now require the
specific early refusal instead of reaching their historical false-PASS assertion.
The C01 fixture-only physical mapping change is preserved as a separate patch.
"""
import hashlib as _hashlib
from pathlib import Path as _Path
import os as _os

_root = _Path(__file__).resolve().parents[5]
_review = _root / "docs/reports/audits/2026-11-01-security-first-cutover/review-round1/test_independent_challenges.py"
_copy = _Path(__file__).resolve().parent / "copied-review-cases.py"
_pin = "d9424c108646f4a88a9cb8babad92d7335497b194d9fc80e6b27452e91731f63"
# This opt-in retains the obsolete physical fixture's failure receipt separately.
_old_fixture = _os.environ.get("CUTOVER_REPAIR_OBSOLETE_FIXTURE") == "1"
_input = _review if _old_fixture else _copy
_input_pin = ("549b332ca4b469ed17101f9e4e1fc4341bd49551ce82ab38fd569d53a78af12f"
              if _old_fixture else "834dcdd7fabe479fceb6909e79dcbe446f6af5347df753cf3b6a2dfb70649f39")
_raw = _input.read_bytes()
assert _hashlib.sha256(_raw).hexdigest() == _input_pin
_old_pin = "PIN = 'cba8d2184bc6c05490490b3a67e0bb4f77934378722afdb40284a63a2c96e813'"
_text = _raw.decode("ascii")
assert _text.count(_old_pin) == 1
_text = _text.replace(_old_pin, "PIN = '" + _pin + "'")
# Execute with the original __file__ solely to preserve ROOT's existing binding.
# Redirect evidence before executing any cases; never write to review-round1.
_actual_file = __file__
__file__ = str(_review)
try:
    exec(compile(_text, str(_input), "exec"), globals())
finally:
    __file__ = _actual_file
OUT = _Path(_actual_file).resolve().parent / ("obsolete-review-diagnostics" if _old_fixture else "round2-review-diagnostics")
OUT.mkdir(mode=0o700)

_original_S01 = test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor
_original_L02 = test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules


def test_S01_interpreter_alias_dotdot_must_not_hide_symlink_ancestor(tmp_path, monkeypatch):
    with pytest.raises(h.Refusal, match="^unsafe_path_link$"):
        _original_S01(tmp_path, monkeypatch)


def test_L02_candidate_root_decoys_must_not_substitute_for_runtime_modules(monkeypatch):
    with pytest.raises(h.Refusal, match="^inventory_or_loaded_or_candidate_drift$"):
        _original_L02(monkeypatch)
