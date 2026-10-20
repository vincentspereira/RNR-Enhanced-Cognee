"""Operator setup for invented-data qualification inside Ubuntu-Hermes only.

Run from a GitHub checkout in Hermes. This does not configure the everyday
profile, install system services, enable backups, or supply a chat model.
The test service and agent share an OS user; this is not a private-data boundary.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
from urllib.parse import quote
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def private_json(path):
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("Operator files must be owner-only regular files")
    return json.loads(path.read_text(encoding="ascii"))


def root_path(value):
    root = Path(value).expanduser()
    expected = Path.home() / "agent-workspace/enhanced-cognee-test-runtime"
    if root != expected or root != root.resolve(strict=True):
        raise ValueError("Use the dedicated Hermes test runtime without symlinks")
    return root


async def provision(root):
    import asyncpg
    from src.memory_admin import create_config, grant_runtime, upgrade_runtime, issue_token
    from src.memory_service import MemoryService

    secret_dir = root / "secrets"
    secret_dir.mkdir(mode=0o700, exist_ok=True)
    os.chmod(secret_dir, 0o700)
    admin_password = secret_dir / "postgres-admin.password"
    if admin_password.is_symlink() or admin_password.stat().st_mode & 0o077:
        raise ValueError("PostgreSQL recovery credentials must be owner-only")
    prefix = "postgresql://cognee_operator:" + quote(admin_password.read_text().strip(), safe="") + "@127.0.0.1:28434/"
    conn = await asyncpg.connect(prefix + "postgres")
    try:
        exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=$1)", "cognee_hermes_test")
        if not exists:
            await conn.execute("CREATE DATABASE cognee_hermes_test")
    finally:
        await conn.close()
    config_path = secret_dir / "service.json"
    if not config_path.exists():
        create_config(str(config_path))
    config = private_json(config_path)
    pool = await asyncpg.create_pool(prefix + "cognee_hermes_test", min_size=1, max_size=2)
    try:
        await MemoryService.provision(pool)
        runtime_path = secret_dir / "runtime.json"
        if not runtime_path.exists():
            await grant_runtime(pool, role="hermes_memory_runtime", operator_url=prefix + "cognee_hermes_test", output=str(runtime_path))
        else:
            await upgrade_runtime(pool, role="hermes_memory_runtime")
        private_json(runtime_path)
    finally:
        await pool.close()
    token_path = secret_dir / "profile-token.json"
    if not token_path.exists():
        os.environ["ENHANCED_JWT_SECRET"] = config["ENHANCED_JWT_SECRET"]
        issue_token(tenant="qualification", project="hermes_test", subject="hermes_test_operator",
                    agent="hermes_test", output=str(token_path), expires_hours=24)
    private_json(token_path)


def serve(root):
    config = private_json(root / "secrets/service.json")
    config.update(private_json(root / "secrets/runtime.json"))
    env = dict(os.environ, **config, COGNEE_LOG_FILE="false", ENHANCED_LOAD_DOTENV="0")
    settings = root / "embedding.json"
    if settings.exists():
        embedding = json.loads(settings.read_text(encoding="ascii"))
        if set(embedding) != {"ENHANCED_EMBEDDING_MODEL", "ENHANCED_MODEL_CACHE"}:
            raise ValueError("Invalid prepared embedding configuration")
        env.update(embedding)
    os.chdir(REPO)
    os.execve(sys.executable, [sys.executable, "-m", "uvicorn", "src.memory_api:app",
                             "--host", "127.0.0.1", "--port", "28080", "--no-access-log", "--ws", "none",
                             "--limit-concurrency", "20"], env)


def install(root):
    import yaml
    profile = Path.home() / ".hermes/profiles/enhanced-cognee-test"
    if profile != profile.resolve(strict=True):
        raise ValueError("Create the dedicated test profile before installation")
    config_path = profile / "config.yaml"
    if config_path.is_symlink():
        raise ValueError("Test configuration must not be a symlink")
    config = yaml.safe_load(config_path.read_text()) or {}
    memory = config.get("memory") or {}
    if memory.get("provider") not in (None, "enhanced_cognee"):
        raise ValueError("The test profile already uses another memory provider")
    # Preserve the original config before making an additive test-only change.
    backup = profile / "config.before-enhanced-cognee.yaml"
    if not backup.exists():
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(config_path.read_text())
    plugin = profile / "plugins/enhanced_cognee"
    source = REPO / "integrations/hermes/enhanced_cognee"
    if plugin.exists():
        for item in source.iterdir():
            if item.is_file() and (not (plugin / item.name).is_file() or item.read_bytes() != (plugin / item.name).read_bytes()):
                raise ValueError("Installed plugin differs; preserve and review before replacing it")
    else:
        shutil.copytree(source, plugin, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    from src.memory_admin import write_private_json
    settings = profile / "enhanced_cognee.json"
    expected = {"base_url": "http://127.0.0.1:28080", "timeout": 5, "include_shared": True, "capture_policy": "selected"}
    if settings.exists():
        if private_json(settings) != expected:
            raise ValueError("Existing test settings differ; review before changing")
    else:
        write_private_json(str(settings), expected)
    token = private_json(root / "secrets/profile-token.json")["ENHANCED_COGNEE_ACCESS_TOKEN"]
    env_path = profile / ".env"
    if env_path.is_symlink():
        raise ValueError("Profile secret store must not be a symlink")
    old = env_path.read_text() if env_path.exists() else ""
    if "ENHANCED_COGNEE_ACCESS_TOKEN" in old:
        raise ValueError("Profile already has a token; renew explicitly rather than overwrite")
    fd = os.open(env_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("\n# Dedicated synthetic memory qualification\nENHANCED_COGNEE_ACCESS_TOKEN=" + token + "\n")
    config["memory"] = dict(memory, memory_enabled=True, user_profile_enabled=True, provider="enhanced_cognee")
    fd = os.open(config_path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
    with os.fdopen(fd, "w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=False)
    marker = profile / "enhanced-cognee-qualification.json"
    if not marker.exists():
        write_private_json(str(marker), {"synthetic_only": True, "installed_at": datetime.now(timezone.utc).isoformat()})


def local_model(model):
    """Reuse one existing loopback provider in the test profile, never a cloud fallback."""
    import yaml
    from dotenv import dotenv_values
    home = Path.home() / ".hermes"
    profile = home / "profiles/enhanced-cognee-test"
    source = yaml.safe_load((home / "config.yaml").read_text()) or {}
    choices = [p for p in source.get("custom_providers", []) if isinstance(p, dict)
               and urlsplit(p.get("base_url", "")).hostname in {"localhost", "127.0.0.1", "::1"}]
    if len(choices) != 1 or not model:
        raise ValueError("Select an existing unambiguous local provider and model")
    provider = {k: v for k, v in choices[0].items() if k in {"name", "base_url", "key_env", "models", "api_mode"}}
    provider["model"] = model
    variable = provider.get("key_env")
    key = os.environ.get(variable, "") or dotenv_values(home / ".env").get(variable, "") if variable else ""
    env_path = profile / ".env"
    if env_path.is_symlink() or not (profile / "enhanced-cognee-qualification.json").is_file():
        raise ValueError("Install the dedicated test profile first")
    old = env_path.read_text()
    if variable and variable not in old and key:
        # JSON string syntax is accepted by dotenv and avoids line injection.
        if not variable.replace("_", "").isalnum():
            raise ValueError("Invalid local provider credential reference")
        fd = os.open(env_path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write("\n" + variable + "=" + json.dumps(key, ensure_ascii=True) + "\n")
    config_path = profile / "config.yaml"
    if config_path.is_symlink():
        raise ValueError("Test configuration must not be a symlink")
    config = yaml.safe_load(config_path.read_text()) or {}
    config["custom_providers"] = [provider]
    config["model"] = {"default": model, "provider": "custom:" + provider["name"],
                       "base_url": provider["base_url"], "api_mode": provider.get("api_mode", "chat_completions")}
    config["fallback_providers"] = []
    with config_path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=False)


def upgrade_plugin(root):
    """Archive before updating only the installed synthetic provider's files."""
    profile = Path.home() / ".hermes/profiles/enhanced-cognee-test"
    plugin = profile / "plugins/enhanced_cognee"
    if profile != profile.resolve(strict=True) or plugin != plugin.resolve(strict=True):
        raise ValueError("Use the installed dedicated test profile without symlinks")
    if not (profile / "enhanced-cognee-qualification.json").is_file():
        raise ValueError("Install and qualify the synthetic profile first")
    source = REPO / "integrations/hermes/enhanced_cognee"
    files = [p for p in source.iterdir() if p.is_file() and p.suffix != ".pyc"]
    if any(p.is_symlink() or (plugin / p.name).is_symlink() for p in files):
        raise ValueError("Provider files must not be symlinks")
    archive = profile / ("provider-before-upgrade-" + uuid.uuid4().hex)
    archive.mkdir(mode=0o700)
    for item in files:
        target = plugin / item.name
        if target.exists():
            shutil.copy2(target, archive / item.name)
            os.chmod(archive / item.name, 0o600)
        # Preserve all unrelated files and existing profile settings/tokens.
        shutil.copy2(item, target)


def renew_test_token(root):
    """Operator-only renewal; signing material never enters the profile."""
    from src.memory_admin import issue_token
    profile = Path.home() / ".hermes/profiles/enhanced-cognee-test"
    path = profile / ".env"
    if profile != profile.resolve(strict=True) or path.is_symlink() or not (profile / "enhanced-cognee-qualification.json").is_file():
        raise ValueError("Use the installed dedicated test profile")
    old = path.read_text()
    lines = old.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith("ENHANCED_COGNEE_ACCESS_TOKEN=")]
    if len(matches) != 1:
        raise ValueError("Expected exactly one installed synthetic profile token")
    config = private_json(root / "secrets/service.json")
    os.environ["ENHANCED_JWT_SECRET"] = config["ENHANCED_JWT_SECRET"]
    output = root / ("secrets/profile-token-" + uuid.uuid4().hex + ".json")
    issue_token(tenant="qualification", project="hermes_test", subject="hermes_test_operator",
                agent="hermes_test", output=str(output), expires_hours=24)
    backup = profile / ("env-before-token-renewal-" + uuid.uuid4().hex)
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(old)
    lines[matches[0]] = "ENHANCED_COGNEE_ACCESS_TOKEN=" + private_json(output)["ENHANCED_COGNEE_ACCESS_TOKEN"] + "\n"
    # Atomic replacement; the original is retained in the owner-only archive.
    temporary = profile / ("env-renewal-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("".join(lines))
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("provision", "serve", "install", "local-model", "upgrade-plugin", "renew-test-token"))
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        root = root_path(args.runtime_root)
        if args.command == "provision":
            asyncio.run(provision(root))
        elif args.command == "serve":
            serve(root)
        elif args.command == "local-model":
            local_model(args.model)
        elif args.command == "upgrade-plugin":
            upgrade_plugin(root)
        elif args.command == "renew-test-token":
            renew_test_token(root)
        else:
            install(root)
    except Exception:
        parser.exit(1, "Test setup stopped; no secret values were printed. Check private operator logs and existing files.\n")
    print("Dedicated test action completed; no secret values were printed.")


if __name__ == "__main__":
    main()
