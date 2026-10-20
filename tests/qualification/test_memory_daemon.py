"""Credential admission tests; actual OS-user separation needs deployment proof."""
import json
import os

import pytest

from src.memory_daemon import credential_environment


def write(path, value):
    path.write_text(json.dumps(value))
    path.chmod(0o600)


def test_service_environment_never_inherits_agent_or_operator_authority(tmp_path, monkeypatch):
    monkeypatch.setenv("ENHANCED_API_KEY", "synthetic-ambient-operator-key")
    monkeypatch.setenv("ENHANCED_BACKUP_SIGNING_KEY", "synthetic-ambient-backup-key")
    monkeypatch.setenv("LD_PRELOAD", "/synthetic/untrusted.so")
    settings = {"ENHANCED_MEMORY_DATABASE_URL": "postgresql://fixture.invalid/synthetic", "ENCRYPTION_MASTER_KEY": "synthetic-key",
                "ENHANCED_JWT_SECRET": "synthetic-verifier-key"}
    write(tmp_path / "api.json", settings)
    env = credential_environment("api", str(tmp_path))
    assert env["ENHANCED_ENV"] == "production" and env["HF_HUB_OFFLINE"] == "1"
    assert not {"ENHANCED_API_KEY", "ENHANCED_BACKUP_SIGNING_KEY", "LD_PRELOAD"} & env.keys()
    write(tmp_path / "api.json", settings | {"INDEX_VALKEY_URL": "redis://localhost:6379/0"})
    with pytest.raises(ValueError, match="Unexpected"):
        credential_environment("api", str(tmp_path))
    worker = {"ENHANCED_INDEX_DATABASE_URL": "postgresql://fixture.invalid/synthetic", "ENCRYPTION_MASTER_KEY": "synthetic-key",
              "ENHANCED_INDEX_CONFIG": "/etc/enhanced-cognee/index.json", "ENHANCED_INDEX_KEY": "synthetic-index-key"}
    write(tmp_path / "worker.json", worker)
    assert "ENHANCED_JWT_SECRET" not in credential_environment("worker", str(tmp_path))
    write(tmp_path / "worker.json", worker | {"ENHANCED_JWT_SECRET": "synthetic-forbidden-key"})
    with pytest.raises(ValueError, match="Unexpected"):
        credential_environment("worker", str(tmp_path))


def test_public_symlink_duplicate_or_oversized_credentials_are_refused(tmp_path):
    path = tmp_path / "api.json"
    write(path, {})
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        credential_environment("api", str(tmp_path))
    path.chmod(0o600)
    path.write_text('{"ENHANCED_JWT_SECRET":"first","ENHANCED_JWT_SECRET":"second"}')
    with pytest.raises(ValueError, match="Duplicate"):
        credential_environment("api", str(tmp_path))
    path.write_text("x"*65537)
    with pytest.raises(ValueError, match="size limit"):
        credential_environment("api", str(tmp_path))
    path.rename(tmp_path / "original.json")
    path.symlink_to(tmp_path / "original.json")
    with pytest.raises(OSError):
        credential_environment("api", str(tmp_path))
    fifo = tmp_path / "fifo"
    fifo.mkdir()
    os.mkfifo(fifo / "api.json", 0o600)
    with pytest.raises(ValueError, match="regular file"):
        credential_environment("api", str(fifo))


def test_scheduled_backup_excludes_decryption_keys_and_destination_overrides(tmp_path, monkeypatch):
    from src import memory_daemon
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "synthetic-ambient-decryption-key")
    monkeypatch.setenv("ENHANCED_BACKUP_DIRECTORY", "/synthetic/cloud-sync")
    monkeypatch.setenv("ENHANCED_JWT_SECRET", "synthetic-ambient-verifier")
    settings = {"ENHANCED_MEMORY_DATABASE_URL": "postgresql://fixture.invalid/synthetic",
                "ENHANCED_BACKUP_SIGNING_KEY": "synthetic-backup-signing-key-at-least-32-bytes",
                "ENHANCED_BACKUP_RECIPIENT": "age1syntheticpublicrecipientfixtureonly"}
    write(tmp_path / "backup.json", settings)
    environment = credential_environment("backup", str(tmp_path))
    assert not {"ENCRYPTION_MASTER_KEY", "ENHANCED_JWT_SECRET", "ENHANCED_BACKUP_DIRECTORY"} & environment.keys()
    assert environment["ENHANCED_BACKUP_RECIPIENT"] == settings["ENHANCED_BACKUP_RECIPIENT"]
    for field in ("ENCRYPTION_MASTER_KEY", "AGE_SECRET_KEY", "ENHANCED_BACKUP_DIRECTORY"):
        write(tmp_path / "backup.json", settings | {field: "synthetic-unapproved-value"})
        with pytest.raises(ValueError, match="Unexpected"):
            credential_environment("backup", str(tmp_path))
    write(tmp_path / "backup.json", settings)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["memory_daemon", "backup"])

    class Executed(BaseException):
        pass

    def capture(executable, arguments, env):
        assert arguments[1:4] == ["-m", "src.memory_backup", "create"]
        assert arguments[arguments.index("--directory")+1] == "/var/backups/enhanced-cognee"
        assert "ENCRYPTION_MASTER_KEY" not in env and "ENHANCED_BACKUP_DIRECTORY" not in env
        raise Executed

    monkeypatch.setattr(os, "execve", capture)
    with pytest.raises(Executed):
        memory_daemon.main()
