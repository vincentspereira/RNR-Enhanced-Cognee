"""Stage an exact protected candidate without changing any service or profile.

Operator only. Existing runtimes, units, configuration and backups are retained.
All public input bytes are hash checked before creating a new candidate. Never
retry over an existing candidate directory; preserve failed attempts for review.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


REVISION = "21abf4857ca8dce8e0a3aafc725266c8d3754529"
ROOT = Path(__file__).absolute().parents[3]
DESTINATION = Path("/opt/enhanced-cognee-memory/candidates") / REVISION
PYTHON = Path("/opt/enhanced-cognee-memory/python/bin/python3.12")
PUBLIC_FILES = {
    "requirements-build.lock": "8bdb8b9902832693b4ffd153ff5efd36d29e9ed7a965b04663eb2bc24ba65f23",
    "requirements-index.lock": "89a9279aa8bd0b5f0227efa235a939658d33cf707a376db2c639832aeedc9e58",
    "requirements-memory-mcp.lock": "c1bfc3d48e5696afa7802e55f2be8c89bef656c0a2ea50913413817e112683be",
    "packaging/memory/dist/rnr_enhanced_cognee_memory-1.2.0-py3-none-any.whl":
        "9ba46a58f32adf29c378690041beaa96ff2f545d432df1265d62617caf5ba7d5",
}
MODEL_FILES = {
    "model_optimized.onnx": (66465124, "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"),
    "tokenizer.json": (711396, "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"),
    "tokenizer_config.json": (1242, "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53"),
    "special_tokens_map.json": (695, "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a"),
    "config.json": (706, "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd"),
}
OLD_MODEL = Path("/opt/enhanced-cognee-memory/model-cache/models--Qdrant--bge-small-en-v1.5-onnx-Q/snapshots/aa8f8b060edb00e03bfdd08813a2949946c8ba55")


def checked_bytes(path, expected, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ValueError("public_artifact_type_or_size")
        raw = stream.read(limit + 1)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("public_artifact_hash")
    return raw


def protected(path):
    """Fixed operator paths must have root-owned, non-writable ancestors."""
    for item in [path, *path.parents]:
        info = item.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode):
            raise ValueError("protected_path_required")


def write_new(path, raw, mode=0o644):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def stage():
    if os.geteuid() != 0:
        raise ValueError("operator_authentication_required")
    protected(PYTHON)
    protected(OLD_MODEL)
    protected(DESTINATION.parent.parent)
    public = {name: checked_bytes(ROOT / name, digest, 4194304) for name, digest in PUBLIC_FILES.items()}
    model = {name: checked_bytes(OLD_MODEL / name, digest, size)
             for name, (size, digest) in MODEL_FILES.items()}
    # Refuse this adapter for any other installed model. Configuration remains
    # in this root process and is never copied into the new artifact tree/logs.
    configuration = Path("/etc/enhanced-cognee/api.json")
    protected(configuration)
    info = configuration.stat()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 65536:
        raise ValueError("api_config_protection")
    with configuration.open() as stream:
        selected_model = json.load(stream).get("ENHANCED_EMBEDDING_MODEL")
    if selected_model != "BAAI/bge-small-en-v1.5":
        raise ValueError("installed_model_not_admitted")
    os.umask(0o022)
    DESTINATION.parent.mkdir(mode=0o755, exist_ok=True)
    protected(DESTINATION.parent)
    DESTINATION.mkdir(mode=0o755, exist_ok=False)
    evidence = DESTINATION / "operator-evidence"
    evidence.mkdir(mode=0o700)
    artifacts = DESTINATION / "artifacts"
    artifacts.mkdir(mode=0o755)
    for name, raw in public.items():
        write_new(artifacts / Path(name).name, raw)
    cache = DESTINATION / "model-cache"
    cache.mkdir(mode=0o755)
    for name, raw in model.items():
        write_new(cache / name, raw)
    runtime = DESTINATION / "runtime"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(evidence), "LANG": "C.UTF-8",
           "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    commands = [[str(PYTHON), "-I", "-m", "venv", "--copies", str(runtime)],
                [str(runtime / "bin/python"), "-I", "-m", "pip", "--isolated", "install",
                 "--no-cache-dir", "--require-hashes", "-r", str(artifacts / "requirements-build.lock")],
                [str(runtime / "bin/python"), "-I", "-m", "pip", "--isolated", "install",
                 "--no-cache-dir", "--require-hashes", "-r", str(artifacts / "requirements-index.lock"),
                 "-r", str(artifacts / "requirements-memory-mcp.lock")],
                [str(runtime / "bin/python"), "-I", "-m", "pip", "--isolated", "install", "--no-deps",
                 str(artifacts / "rnr_enhanced_cognee_memory-1.2.0-py3-none-any.whl")],
                [str(runtime / "bin/python"), "-I", "-m", "pip", "check"]]
    for number, command in enumerate(commands):
        with (evidence / (str(number) + ".log")).open("xb") as output:
            process = subprocess.run(command, cwd=evidence, env=env, stdout=output, stderr=output,
                                     check=False, timeout=600)
        if process.returncode:
            raise ValueError("staging_command_failed_" + str(number))
    result = {"complete": True, "source_revision": REVISION, "candidate": str(DESTINATION),
              "public_artifact_sha256": PUBLIC_FILES, "installed_model_verified": True,
              "exact_hashed_locks_installed": True, "pip_check_passed": True,
              "service_changed": False, "profiles_changed": False,
              "recovery_qualified": False, "fleet_launch_approved": False}
    write_new(evidence / "summary.json", (json.dumps(result, indent=2) + "\n").encode(), mode=0o600)
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(stage()))
    except Exception as error:
        category = str(error) if type(error) is ValueError else type(error).__name__
        # No subprocess output or exception details containing private state.
        allowed = {"operator_authentication_required", "protected_path_required", "public_artifact_type_or_size",
                   "public_artifact_hash", "api_config_protection", "installed_model_not_admitted"}
        if category not in allowed and category not in {"staging_command_failed_" + str(i) for i in range(5)}:
            category = "operator_staging_failed_see_retained_evidence"
        print(json.dumps({"complete": False, "category": category, "service_changed": False,
                          "candidate": str(DESTINATION), "fleet_launch_approved": False}))
        sys.exit(1)
