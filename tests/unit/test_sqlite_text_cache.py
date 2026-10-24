"""Text-only persistence and transaction rollback for the filesystem cache."""
import pytest

from src.security.sqlite_text_cache import SqliteTextCache


def test_persistence_expiry_rollback_and_text_only(tmp_path, monkeypatch):
    monkeypatch.setattr("src.security.sqlite_text_cache.time.time", lambda: 100)
    cache = SqliteTextCache(tmp_path / "cache")
    cache.set("fact", '{"content":"fixture"}', expire=5)
    with pytest.raises(TypeError):
        cache.set("unsafe", object())
    with pytest.raises(RuntimeError):
        with cache.transact():
            cache.set("rolled_back", "value")
            raise RuntimeError("fixture failure")
    assert cache.get("rolled_back") is None
    cache.close()
    recovered = SqliteTextCache(tmp_path / "cache")
    assert recovered.get("fact") == '{"content":"fixture"}'
    monkeypatch.setattr("src.security.sqlite_text_cache.time.time", lambda: 106)
    assert recovered.get("fact") is None
    recovered.set("to_remove", "value")
    assert recovered.clear() == 1
    recovered.close()


def test_legacy_cache_is_preserved_without_loading(tmp_path):
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    old = root / "cache.db"
    old.write_bytes(b"historical bytes must remain untouched")
    with pytest.raises(RuntimeError, match="Legacy diskcache"):
        SqliteTextCache(root)
    assert old.read_bytes() == b"historical bytes must remain untouched"
    assert not (root / "text-cache.sqlite3").exists()


def test_public_directory_and_symlink_are_rejected(tmp_path):
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(PermissionError):
        SqliteTextCache(public)
    target = tmp_path / "private"
    target.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(PermissionError):
        SqliteTextCache(alias)
