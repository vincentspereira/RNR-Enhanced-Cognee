"""Source boundaries; candidates are not installed service credentials."""
import importlib.util
from pathlib import Path
import re

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/prepare_launch_credential_rotation.py"
spec = importlib.util.spec_from_file_location("rotation_preparation", SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def test_separate_random_login_candidates_do_not_rotate_data_keys():
    document = helper.replacements()
    assert set(document) == {"postgresql", "arcadedb", "valkey", "qdrant", "application"}
    credentials = []
    for store in ("postgresql", "arcadedb", "valkey"):
        assert set(document[store]) == {"api", "worker", "operator"}
        for row in document[store].values():
            assert re.fullmatch(r"ec_(api|worker|operator)_[a-f0-9]{12}", row["username"])
            assert len(row["password"]) >= 43
            credentials.append(row["password"])
    assert set(document["qdrant"]) == {"readonly", "admin_write"}
    credentials.extend(row["api_key"] for row in document["qdrant"].values())
    credentials.append(document["application"]["issuer"]["jwt_signing_key"])
    assert len(credentials) == len(set(credentials)) == 12
    assert not set(credentials) & {row["password"] for row in helper.replacements()["postgresql"].values()}


def test_unprivileged_operator_stops_before_generation(monkeypatch):
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(helper, "replacements", lambda: pytest.fail("must not generate"))
    with pytest.raises(ValueError, match="local_root_operator_required"):
        helper.main()


def test_private_candidate_write_never_overwrites_existing_evidence(tmp_path):
    path = tmp_path / "invented.private.json"
    helper.write_private(path, b"invented-first")
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        helper.write_private(path, b"invented-second")
    assert path.read_bytes() == b"invented-first"


def test_private_candidate_write_refuses_symlink(tmp_path):
    original = tmp_path / "original"
    original.write_bytes(b"preserve")
    link = tmp_path / "candidate"
    link.symlink_to(original)
    with pytest.raises(FileExistsError):
        helper.write_private(link, b"replacement")
    assert original.read_bytes() == b"preserve"
