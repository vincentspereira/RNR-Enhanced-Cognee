"""Offline stage-only tests. All values and filesystem fixtures are invented."""
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / ("integrations/hermes/deployment/prepare_security_first_cutover.py"
                 if os.environ.get("ENHANCED_CUTOVER_BASELINE_V1") == "1" else
                 "integrations/hermes/deployment/prepare_security_first_cutover_v2.py")


def load_helper():
    if not HELPER.exists():
        return SimpleNamespace()
    spec = importlib.util.spec_from_file_location("security_first_cutover", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


h = load_helper()


def test_phase_a_dropin_and_canonical_hash():
    assert callable(getattr(h, "proposed_dropin", None)), "stage-only helper missing"
    candidate = "/opt/enhanced-cognee-memory/candidates/audit-c14f595c-20261101"
    expected = ("[Service]\nWorkingDirectory=" + candidate + "\nExecStart=\nExecStart="
                + candidate + "/runtime/bin/python -I -B -m src.memory_daemon api\n"
                "LoadCredential=\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n"
                "LoadCredential=index.json:/etc/enhanced-cognee/index.json\n").encode("ascii")
    assert h.proposed_dropin() == expected
    assert b"llm.json" not in expected
    assert b"StateDirectory" not in expected
    assert h.canonical({"z": False, "a": 1}) == b'{"a":1,"z":false}\n'
    assert h.digest(expected) == hashlib.sha256(expected).hexdigest()


def launch_unit(extra=""):
    return ("[Service]\nUser=enhanced-cognee-api\nGroup=enhanced-cognee-api\n"
            "WorkingDirectory=" + h.OLD + "\nExecStart=\nExecStart=" + h.OLD
            + "/runtime/bin/python -m src.memory_daemon api\n" + extra).encode()


def test_launch_unit_is_parsed_without_exposing_environment():
    assert callable(getattr(h, "parse_unit", None)), "unit validation missing"
    parsed = h.parse_unit(launch_unit("Environment=PYTHONDONTWRITEBYTECODE=1\n"), launch=True)
    assert parsed["User"] == ["enhanced-cognee-api"]
    assert parsed["ExecStart"] == ["", h.OLD + "/runtime/bin/python -m src.memory_daemon api"]


@pytest.mark.parametrize("extra", [
    "SetCredential=llm.json:invented-secret\n", "SetCredentialEncrypted=secret\n",
    "LoadCredentialEncrypted=secret\n", "ImportCredential=*\n",
    "LoadCredential=\n", "LoadCredential=api.json:/etc/enhanced-cognee/api.json\n",
    "Environment=ENHANCED_LLM_API_KEY=invented-secret\n", "EnvironmentFile=/invented-secret\n",
    "ExecStartPre=/invented-secret\n", "StateDirectory=invented-secret\n",
    "User=root\n", "Environment=\n", "Unknown=invented-secret\n",
    "Environment=PYTHONDONTWRITEBYTECODE=1\\\n PYTHONUNBUFFERED=1\n",
    "Environment=PYTHONDONTWRITEBYTECODE=\\x31\n", " Environment=PYTHONUNBUFFERED=1\n",
    "[Socket]\nListenStream=1\n", "Environment=PYTHONUNBUFFERED=1\r\n",
    "Environment=PYTHONUNBUFFERED=1\x00\n", "ExecStart=\n",
])
def test_launch_unit_refuses_ambiguous_or_secret_directives(extra):
    assert callable(getattr(h, "parse_unit", None)), "unit validation missing"
    with pytest.raises(h.Refusal) as exc:
        h.parse_unit(launch_unit(extra), launch=True)
    assert "invented-secret" not in str(exc.value)
    assert str(exc.value) == "unit_syntax_or_directive_refused"


def snapshot(monkeypatch):
    raw = {h.SOURCES[0]: b"[Service]\nDynamicUser=yes\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n",
           h.SOURCES[1]: b"[Service]\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n",
           h.SOURCES[2]: launch_unit(),
           h.SOURCES[3]: b"[Service]\nLoadCredential=llm.json:/etc/enhanced-cognee/llm.json\n"}
    monkeypatch.setattr(h, "SOURCE_HASHES", {p: h.digest(b) for p, b in raw.items() if p != h.SOURCES[2]})
    return {"source_bytes": raw, "inventory": list(h.SOURCES), "loaded": dict(h.EXPECTED_LOADED),
            "candidate": h.CANDIDATE, "candidate_hashes": dict(h.MODULE_HASHES),
            "helper_sha256": "1" * 64,
            "startup_interpreter": {"lexical": h.CANDIDATE + "/runtime/bin/python",
                                    "resolved": "/usr/bin/python3.12", "sha256": "2" * 64}}


def test_full_plan_binds_every_field_and_eight_accepted_payload_hashes(monkeypatch):
    assert callable(getattr(h, "plan_from_snapshot", None)), "plan derivation missing"
    snap = snapshot(monkeypatch)
    plan = h.plan_from_snapshot(snap)
    payload = json.loads((ROOT / "integrations/hermes/deployment/audit_backend_payload.json").read_bytes())
    assert h.MODULE_HASHES == {f["path"]: f["new_sha256"] for f in payload["files"]}
    assert len(plan["candidate_hashes"]) == 8
    assert plan == {
        "schema": 1, "phase": "A-stage-only", "bundle": h.BUNDLE,
        "candidate": h.CANDIDATE, "candidate_hashes": h.MODULE_HASHES,
        "source_sha256": {p: h.digest(b) for p, b in snap["source_bytes"].items()},
        "loaded": h.EXPECTED_LOADED, "helper_sha256": "1" * 64,
        "startup_interpreter": snap["startup_interpreter"],
        "dropin_sha256": h.digest(h.proposed_dropin()),
        "retained_credentials": ["api.json", "index.json"], "omitted_credentials": ["llm.json"],
        "activated": False, "services_restarted": False, "ledger_created": False,
        "credentials_issued": 0, "model_analysis_expected_enabled": False,
        "installation_pending": True, "model_usage_reset": False,
        "state_directory_proposed": False,
    }
    assert h.plan_from_snapshot(snap) == plan
    assert b"Environment" not in h.canonical(plan)


@pytest.mark.parametrize("drift", ["missing", "extra", "source-hash", "candidate-path", "candidate-hash",
    "candidate-extra", "reload", "alias", "run-override", "loaded-missing", "credential-duplicate",
    "credential-wildcard", "credential-reset", "launch-syntax"])
def test_plan_refuses_snapshot_drift(monkeypatch, drift):
    assert callable(getattr(h, "plan_from_snapshot", None)), "plan derivation missing"
    snap = snapshot(monkeypatch)
    if drift == "missing":
        del snap["source_bytes"][h.SOURCES[1]]
    elif drift == "extra":
        snap["inventory"].append(h.SOURCE + ".d/99-unexpected.conf")
    elif drift == "source-hash":
        snap["source_bytes"][h.SOURCES[0]] += b"# drift\n"
    elif drift == "candidate-path":
        snap["candidate"] += "-other"
    elif drift == "candidate-hash":
        snap["candidate_hashes"]["src/llm_budget.py"] = "0" * 64
    elif drift == "candidate-extra":
        snap["candidate_hashes"]["other.py"] = "0" * 64
    elif drift == "reload":
        snap["loaded"]["NeedDaemonReload"] = "yes"
    elif drift == "alias":
        snap["loaded"]["Names"] += " unexpected.service"
    elif drift == "run-override":
        snap["loaded"]["FragmentPath"] = "/run/systemd/system/" + h.UNIT
    elif drift == "loaded-missing":
        del snap["loaded"]["StateDirectory"]
    else:
        addition = {"credential-duplicate": "LoadCredential=api.json:/etc/enhanced-cognee/api.json\n",
                    "credential-wildcard": "LoadCredential=*.json:/etc/enhanced-cognee\n",
                    "credential-reset": "LoadCredential=\n", "launch-syntax": "SetCredential=hidden:invented-secret\n"}[drift]
        snap["source_bytes"][h.SOURCES[2]] += addition.encode()
    with pytest.raises(h.Refusal):
        h.plan_from_snapshot(snap)


def root_metadata(path):
    info = os.lstat(path)
    fields = list(info)
    fields[4] = fields[5] = 0
    return os.stat_result(fields)


@pytest.mark.parametrize("problem", ["none", "uid", "gid", "writable-file", "writable-ancestor",
    "ancestor-link", "leaf-link", "hardlink", "fifo", "relative", "dotdot", "private"])
def test_trust_rejects_unsafe_lexical_paths(tmp_path, problem):
    assert callable(getattr(h, "trusted_path", None)), "path trust missing"
    directory = tmp_path / "safe"
    directory.mkdir(mode=0o700)
    target = directory / "file"
    target.write_bytes(b"invented")
    target.chmod(0o600)
    path = str(target)
    def metadata(p):
        info = root_metadata(p)
        fields = list(info)
        # Do not let the synthetic sandbox's /tmp or home permissions control tests.
        if stat.S_ISDIR(info.st_mode):
            fields[0] = stat.S_IFDIR | 0o755
        if problem == "uid" and str(p) == path:
            fields[4] = 1234
        if problem == "gid" and str(p) == path:
            fields[5] = 1234
        if problem == "private" and str(p) == path:
            fields[0] |= 0o044
        if problem == "writable-file" and str(p) == path:
            fields[0] |= 0o020
        if problem == "writable-ancestor" and str(p) == str(directory):
            fields[0] |= 0o002
        return os.stat_result(fields)
    if problem == "ancestor-link":
        link = tmp_path / "alias"
        link.symlink_to(directory, target_is_directory=True)
        path = str(link / "file")
    if problem == "leaf-link":
        link = directory / "alias"
        link.symlink_to(target)
        path = str(link)
    if problem == "hardlink":
        os.link(target, directory / "other")
    if problem == "fifo":
        fifo = directory / "fifo"
        os.mkfifo(fifo)
        path = str(fifo)
    if problem == "relative":
        path = "relative/file"
    if problem == "dotdot":
        path = str(directory) + "/../safe/file"
    if problem == "none":
        assert h.trusted_path(path, stat_fn=metadata) == path
    else:
        with pytest.raises(h.Refusal):
            h.trusted_path(path, private=problem == "private", stat_fn=metadata)


@pytest.mark.parametrize("problem", ["none", "writable-link-parent", "target-owner", "target-hardlink"])
def test_interpreter_alias_checks_both_lexical_and_resolved_chains(tmp_path, problem):
    assert callable(getattr(h, "trusted_path", None)), "path trust missing"
    folder = tmp_path / "bin"
    folder.mkdir()
    target = tmp_path / "python3.12"
    target.write_bytes(b"invented interpreter")
    target.chmod(0o644)
    alias = folder / "python"
    alias.symlink_to("../python3.12")
    if problem == "target-hardlink":
        os.link(target, tmp_path / "another")
    def metadata(p):
        info = root_metadata(p)
        fields = list(info)
        if stat.S_ISDIR(info.st_mode):
            fields[0] = stat.S_IFDIR | 0o755
        if problem == "writable-link-parent" and str(p) == str(folder):
            fields[0] |= 0o020
        if problem == "target-owner" and str(p) == str(target):
            fields[4] = 1234
        return os.stat_result(fields)
    if problem == "none":
        assert h.trusted_path(str(alias), allow_alias=True, stat_fn=metadata) == str(target)
    else:
        with pytest.raises(h.Refusal):
            h.trusted_path(str(alias), allow_alias=True, stat_fn=metadata)


def sandbox_guard(path, *, kind="file", private=False, **kwargs):
    info = os.lstat(path)
    assert not stat.S_ISLNK(info.st_mode)
    assert stat.S_ISDIR(info.st_mode) if kind == "directory" else stat.S_ISREG(info.st_mode)
    if private:
        assert stat.S_IMODE(info.st_mode) == (0o700 if kind == "directory" else 0o600)
    return str(path)


def test_new_private_bundle_and_partial_failure_are_preserved(tmp_path):
    assert callable(getattr(h, "write_bundle", None)), "exclusive writer missing"
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    bundle = parent / "package"
    files = {"40-audit-security-first.conf": b"invented", "manifest.json": b"{}\n",
             "receipt.json": b'{"complete":true}\n'}
    h.write_bundle(str(bundle), files, guard=sandbox_guard)
    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == files
    assert stat.S_IMODE(bundle.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in bundle.iterdir())
    with pytest.raises(FileExistsError):
        h.write_bundle(str(bundle), files, guard=sandbox_guard)
    partial = parent / "partial"
    def fail_second(fd, name, data):
        if name == "manifest.json":
            raise OSError("invented-secret")
        h.write_new(fd, name, data)
    with pytest.raises(OSError):
        h.write_bundle(str(partial), files, guard=sandbox_guard, writer=fail_second)
    assert (partial / "40-audit-security-first.conf").read_bytes() == b"invented"
    assert not (partial / "receipt.json").exists()
    with pytest.raises(FileExistsError):
        h.write_bundle(str(partial), files, guard=sandbox_guard)


def test_snapshot_collection_reads_only_units_helper_modules_interpreter(monkeypatch):
    assert callable(getattr(h, "collect_snapshot", None)), "protected snapshot collection missing"
    snap = snapshot(monkeypatch)
    content = dict(snap["source_bytes"])
    module_bytes = {p: ("invented-" + p).encode() for p in h.MODULE_HASHES}
    monkeypatch.setattr(h, "MODULE_HASHES", {p: h.digest(b) for p, b in module_bytes.items()})
    content.update({h.CANDIDATE + "/runtime/lib/python3.12/site-packages/" + p: b for p, b in module_bytes.items()})
    content[h.INSTALLED_HELPER] = b"invented helper"
    content["/usr/bin/python3.12"] = b"invented interpreter"
    reads, guards = [], []
    def reader(path):
        reads.append(path)
        return content[path]
    def guard(path, **kwargs):
        guards.append((path, kwargs))
        return "/usr/bin/python3.12" if kwargs.get("allow_alias") else path
    result = h.collect_snapshot(reader=reader, guard=guard, inventory=lambda: list(h.SOURCES),
                                loaded=lambda: dict(h.EXPECTED_LOADED))
    assert set(reads) == set(content)
    assert len(reads) == len(content)
    assert result["candidate_hashes"] == h.MODULE_HASHES
    assert result["helper_sha256"] == h.digest(b"invented helper")
    assert result["startup_interpreter"]["sha256"] == h.digest(b"invented interpreter")
    assert (h.CANDIDATE + "/runtime/bin/python", {"allow_alias": True, "executable": True}) in guards


@pytest.mark.parametrize("extra", [None, "99-evil.conf", "run", "prefix", "alias"])
def test_source_inventory_covers_fixed_and_runtime_prefix_overrides(extra):
    assert callable(getattr(h, "inventory_sources", None)), "source inventory missing"
    present = {"/etc/systemd/system", h.SOURCE, h.SOURCE + ".d", *h.SOURCES[1:]}
    entries = {h.SOURCE + ".d": [Path(p).name for p in h.SOURCES[1:]]}
    if extra == "99-evil.conf":
        entries[h.SOURCE + ".d"].append(extra)
    if extra == "run":
        present.update({"/run/systemd/system", "/run/systemd/system/" + h.UNIT})
    if extra == "prefix":
        present.update({"/run/systemd/system", "/run/systemd/system/enhanced-.service.d"})
        entries["/run/systemd/system/enhanced-.service.d"] = ["invented.conf"]
    if extra == "alias":
        present.add("/usr/lib/systemd/system")
    def guard(path, **kwargs):
        if extra == "alias" and path == "/usr/lib/systemd/system":
            raise h.Refusal("unsafe_path_link")
        return path
    call = lambda: h.inventory_sources(roots=h.UNIT_ROOTS, exists=lambda p: p in present,
                                       children=lambda p: entries[p], guard=guard)
    if extra is None:
        assert call() == list(h.SOURCES)
    else:
        with pytest.raises(h.Refusal):
            call()


def test_show_reads_only_selected_properties_and_sanitizes_process_failures():
    assert callable(getattr(h, "read_loaded", None)), "loaded-state inspection missing"
    raw = dict(h.EXPECTED_LOADED)
    command = raw["ExecStart"]
    raw["ExecStart"] = ("{ path=" + h.OLD + "/runtime/bin/python ; argv[]=" + command
                        + " ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }")
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="\n".join(k + "=" + v for k, v in raw.items()).encode())
    assert h.read_loaded(run=run, guard=lambda *a, **k: None) == h.EXPECTED_LOADED
    args, kwargs = calls[0]
    assert args[:5] == ["/usr/bin/systemctl", "--no-pager", "--full", "show", h.UNIT]
    assert set(args[5:]) == {"--property=" + key for key in h.EXPECTED_LOADED}
    assert not kwargs.get("shell")
    assert kwargs["env"] == {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "SYSTEMD_PAGER": "cat"}
    def fail(*a, **k):
        return SimpleNamespace(returncode=1, stdout=b"invented-secret")
    with pytest.raises(h.Refusal) as exc:
        h.read_loaded(run=fail, guard=lambda *a, **k: None)
    assert "invented-secret" not in str(exc.value)


def test_protected_reader_never_follows_link_or_reads_fifo(tmp_path):
    assert callable(getattr(h, "read_protected", None)), "protected reader missing"
    file = tmp_path / "file"
    file.write_bytes(b"invented")
    assert h.read_protected(str(file), guard=sandbox_guard) == b"invented"
    alias = tmp_path / "link"
    alias.symlink_to(file)
    with pytest.raises((h.Refusal, AssertionError, OSError)):
        h.read_protected(str(alias), guard=sandbox_guard)
    with pytest.raises(h.Refusal):
        h.read_protected(str(file), guard=sandbox_guard, limit=3)


@pytest.mark.parametrize("problem", [None, "uid", "gid", "flags", "checkout", "interpreter", "unsafe-helper"])
def test_runtime_guard_requires_root_protected_install_and_isolated_interpreter(problem):
    assert callable(getattr(h, "runtime_guard", None)), "root CLI guard missing"
    calls = []
    def guard(path, **kwargs):
        calls.append((path, kwargs))
        if problem == "unsafe-helper" and path == h.INSTALLED_HELPER:
            raise h.Refusal("unsafe_path_owner")
        return path
    call = lambda: h.runtime_guard(
        euid=lambda: 1234 if problem == "uid" else 0,
        egid=lambda: 1234 if problem == "gid" else 0,
        flags=SimpleNamespace(isolated=problem != "flags", no_site=True, dont_write_bytecode=True, safe_path=True),
        helper=str(HELPER) if problem == "checkout" else h.INSTALLED_HELPER,
        executable="/home/invented/python" if problem == "interpreter" else "/usr/bin/python3", guard=guard)
    if problem is None:
        call()
        assert calls == [(h.INSTALLED_HELPER, {}), ("/usr/bin/python3", {"allow_alias": True})]
    else:
        with pytest.raises(h.Refusal):
            call()


def test_main_full_plan_is_read_only_and_prepare_rechecks_and_writes_exact_bundle(monkeypatch, tmp_path, capsys):
    assert callable(getattr(h, "main", None)), "stage-only CLI missing"
    snap = snapshot(monkeypatch)
    plan = h.plan_from_snapshot(snap)
    approved = h.digest(h.canonical(plan))
    checks, writes = [], []
    def output_guard():
        checks.append("output")
    def collector():
        checks.append("snapshot")
        return snap
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    sandbox = parent / "bundle"
    def writer(path, files):
        assert path == h.BUNDLE
        writes.append(list(files))
        h.write_bundle(str(sandbox), files, guard=sandbox_guard)
    seams = dict(runtime=lambda: checks.append("runtime"), collector=collector,
                 output_guard=output_guard, writer=writer)
    assert h.main(["--plan"], **seams) == 0
    response = json.loads(capsys.readouterr().out)
    assert response == {"plan": plan, "plan_sha256": approved}
    assert writes == [] and list(parent.iterdir()) == []
    checks.clear()
    assert h.main(["--prepare", "--expected-plan-sha256", approved], **seams) == 0
    response = json.loads(capsys.readouterr().out)
    assert checks == ["runtime", "output", "snapshot", "snapshot", "runtime", "output"]
    assert writes == [["40-audit-security-first.conf", "manifest.json", "receipt.json"]]
    assert (sandbox / "manifest.json").read_bytes() == h.canonical(plan)
    assert (sandbox / "40-audit-security-first.conf").read_bytes() == h.proposed_dropin()
    receipt = json.loads((sandbox / "receipt.json").read_bytes())
    assert receipt == response
    assert receipt == {"complete": True, "plan_sha256": approved,
        "artifact_sha256": {"40-audit-security-first.conf": h.digest(h.proposed_dropin()), "manifest.json": approved},
        **{key: plan[key] for key in ("activated", "services_restarted", "ledger_created", "credentials_issued",
            "model_analysis_expected_enabled", "installation_pending", "model_usage_reset")}}


@pytest.mark.parametrize("arguments", [[], ["--activate"], ["--plan", "--prepare"],
    ["--plan", "invented-secret"], ["--prepare"],
    *[["--prepare", "--expected-plan-sha256", value] for value in
      ("a" * 63, "a" * 65, " " + "a" * 64, "a" * 64 + "\n", "A" * 64, "g" * 64, "invented-secret")]])
def test_main_rejects_malformed_arguments_without_normalizing_or_echo(arguments, capsys):
    assert callable(getattr(h, "main", None)), "stage-only CLI missing"
    def forbidden():
        pytest.fail("invalid input reached privileged inspection")
    assert h.main(arguments, runtime=forbidden) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "ERR stage_only_refused\n"


@pytest.mark.parametrize("problem", ["wrong-approval", "toctou", "secret-exception", "unsafe-output"])
def test_prepare_failures_write_nothing_and_do_not_echo_exception(monkeypatch, capsys, problem):
    assert callable(getattr(h, "main", None)), "stage-only CLI missing"
    snap = snapshot(monkeypatch)
    approved = h.digest(h.canonical(h.plan_from_snapshot(snap)))
    count, writes = [], []
    def collector():
        count.append(1)
        if problem == "secret-exception":
            raise RuntimeError("invented-secret full exception")
        if problem == "toctou" and len(count) == 2:
            snap["source_bytes"][h.SOURCES[2]] += b"# drift\n"
        return snap
    def output_guard():
        if problem == "unsafe-output":
            raise h.Refusal("unsafe_private_mode")
    result = h.main(["--prepare", "--expected-plan-sha256", "0" * 64 if problem == "wrong-approval" else approved],
                    runtime=lambda: None, collector=collector, output_guard=output_guard,
                    writer=lambda *args: writes.append(args))
    assert result == 1 and writes == []
    assert capsys.readouterr().err == "ERR stage_only_refused\n"


def test_output_guard_requires_private_existing_parent_and_absent_target(tmp_path):
    assert callable(getattr(h, "check_output", None)), "output preflight missing"
    bundle = tmp_path / "private" / "bundle"
    with pytest.raises(FileNotFoundError):
        h.check_output(str(bundle), guard=sandbox_guard)
    bundle.parent.mkdir(mode=0o700)
    h.check_output(str(bundle), guard=sandbox_guard)
    bundle.mkdir()
    with pytest.raises(h.Refusal):
        h.check_output(str(bundle), guard=sandbox_guard)


def test_bundle_readback_catches_corruption_before_complete_receipt(tmp_path):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    target = parent / "bundle"
    files = {"40-audit-security-first.conf": b"invented", "manifest.json": b"{}\n", "receipt.json": b"{}\n"}
    def corrupt(fd, name, data):
        h.write_new(fd, name, b"wrong bytes" if name == "manifest.json" else data)
    with pytest.raises(h.Refusal):
        h.write_bundle(str(target), files, guard=sandbox_guard, writer=corrupt)
    assert not (target / "receipt.json").exists()
    assert (target / "manifest.json").read_bytes() == b"wrong bytes"


def test_bundle_rejects_extra_files_before_any_write(tmp_path):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    target = parent / "bundle"
    with pytest.raises(h.Refusal):
        h.write_bundle(str(target), {"unexpected": b"invented"}, guard=sandbox_guard)
    assert not target.exists()


@pytest.mark.parametrize("flag", ["isolated", "no_site", "dont_write_bytecode", "safe_path"])
def test_each_required_interpreter_flag_is_independently_required(flag):
    flags = dict(isolated=True, no_site=True, dont_write_bytecode=True, safe_path=True)
    flags[flag] = False
    with pytest.raises(h.Refusal):
        h.runtime_guard(euid=lambda: 0, egid=lambda: 0, flags=SimpleNamespace(**flags),
                        helper=h.INSTALLED_HELPER, executable="/usr/bin/python3", guard=lambda *a, **k: None)


@pytest.mark.parametrize("property_name", list(h.EXPECTED_LOADED))
def test_every_selected_loaded_property_is_bound(monkeypatch, property_name):
    snap = snapshot(monkeypatch)
    snap["loaded"][property_name] = "invented drift"
    with pytest.raises(h.Refusal):
        h.plan_from_snapshot(snap)


def test_known_static_source_hashes_are_exactly_the_owner_supplied_pins():
    assert h.SOURCE_HASHES == {
        h.SOURCES[0]: "af979af033e64fee0dde16a1484ac5eb00ca75282c3478f382599027ec35dba2",
        h.SOURCES[1]: "6ae6c5ebf3ac141c5bd03c8ac6970c308eee4fe5220606b800c2e11f698cee06",
        h.SOURCES[3]: "12f118dd78e34477736a3e4a9db2d5d29bcafb199a77386f58b8cc45b5e60f33"}
    assert h.SOURCES[2] not in h.SOURCE_HASHES


def test_cli_entry_rejects_unprivileged_checkout_without_writes(tmp_path):
    import subprocess
    assert os.geteuid() != 0, "tests must never run as root"
    before = sorted(p.name for p in tmp_path.iterdir())
    for args in (["--plan"], ["--prepare", "--expected-plan-sha256", "0" * 64]):
        result = subprocess.run(["/usr/bin/python3", "-I", "-S", "-B", str(HELPER), *args],
                                cwd=tmp_path, env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=10)
        assert (result.returncode, result.stdout, result.stderr) == (1, b"", b"ERR stage_only_refused\n")
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_no_application_imports_no_ledger_and_only_show_subprocess(tmp_path, monkeypatch):
    import ast
    import builtins
    tree = ast.parse(HELPER.read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            imports.add(node.module)
    assert imports <= {"hashlib", "json", "re", "shlex", "os", "stat", "pathlib", "subprocess", "sys"}
    original = builtins.__import__
    def reject_app(name, *args, **kwargs):
        assert not name.startswith("src"), "application import attempted"
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", reject_app)
    assert load_helper().proposed_dropin() == h.proposed_dropin()
    assert "/var/lib" not in HELPER.read_text()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("problem", ["duplicate", "missing", "command-extra", "unknown-property"])
def test_loaded_process_format_drift_is_refused(problem):
    raw = dict(h.EXPECTED_LOADED)
    raw["ExecStart"] = ("{ path=" + h.OLD + "/runtime/bin/python ; argv[]=" + h.EXPECTED_LOADED["ExecStart"]
        + (" extra" if problem == "command-extra" else "")
        + " ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }")
    if problem == "missing":
        del raw["User"]
    if problem == "unknown-property":
        raw["Environment"] = "invented-secret"
    output = "\n".join(k + "=" + v for k, v in raw.items())
    if problem == "duplicate":
        output += "\nUser=enhanced-cognee-api"
    with pytest.raises(h.Refusal):
        h.read_loaded(run=lambda *a, **k: SimpleNamespace(returncode=0, stdout=output.encode()), guard=lambda *a, **k: None)


def test_writer_rejects_unsafe_parent_before_creation(tmp_path):
    files = {"40-audit-security-first.conf": b"invented", "manifest.json": b"{}", "receipt.json": b"{}"}
    target = tmp_path / "bundle"
    def reject(*args, **kwargs):
        raise h.Refusal("unsafe_path_mode")
    with pytest.raises(h.Refusal):
        h.write_bundle(str(target), files, guard=reject)
    assert not target.exists()


def test_snapshot_never_reads_arbitrary_alias_target(monkeypatch):
    reads = []
    def guard(path, **kwargs):
        return "/etc/enhanced-cognee/api.json" if kwargs.get("allow_alias") else path
    with pytest.raises(h.Refusal):
        h.collect_snapshot(reader=lambda p: reads.append(p) or b"invented", guard=guard,
                           inventory=lambda: list(h.SOURCES), loaded=lambda: dict(h.EXPECTED_LOADED))
    assert reads == []


def test_interpreter_must_have_execute_permission(tmp_path):
    import inspect
    assert "executable" in inspect.signature(h.trusted_path).parameters, "executable trust guard missing"
    target = tmp_path / "python"
    target.write_bytes(b"invented non-executable")
    target.chmod(0o644)
    def metadata(p):
        info = root_metadata(p)
        fields = list(info)
        if stat.S_ISDIR(info.st_mode):
            fields[0] = stat.S_IFDIR | 0o755
        return os.stat_result(fields)
    with pytest.raises(h.Refusal):
        h.trusted_path(str(target), executable=True, stat_fn=metadata)


def test_inventory_refuses_unknown_manager_search_path():
    with pytest.raises(h.Refusal):
        h.inventory_sources(roots=(*h.UNIT_ROOTS, "/home/invented/systemd"))


# New V2 identity contracts; historical safety bodies above remain unchanged.
def owner_launch():
    # Metadata-equivalent invented four-line override, not owner bytes/hash.
    return ("[Service]\nWorkingDirectory=" + h.OLD + "\nExecStart=\nExecStart="
            + h.OLD + "/runtime/bin/python -m src.memory_daemon api\n").encode("ascii")


def owner_snapshot(monkeypatch):
    raw = dict(zip(h.SOURCES, [
        b"[Service]\nDynamicUser=yes\nLoadCredential=api.json:/etc/enhanced-cognee/api.json\n",
        b"[Service]\nLoadCredential=index.json:/etc/enhanced-cognee/index.json\n",
        owner_launch(),
        b"[Service]\nLoadCredential=llm.json:/etc/enhanced-cognee/llm.json\n"]))
    monkeypatch.setattr(h, "SOURCE_HASHES", {p: h.digest(b) for p, b in raw.items() if p != h.SOURCES[2]})
    return {"source_bytes": raw, "inventory": list(h.SOURCES), "loaded": dict(h.EXPECTED_LOADED),
            "candidate": h.CANDIDATE, "candidate_hashes": dict(h.MODULE_HASHES),
            "helper_sha256": "1" * 64, "startup_interpreter": {
                "lexical": h.CANDIDATE + "/runtime/bin/python", "resolved": "/usr/bin/python3.12",
                "sha256": "2" * 64}}


def test_owner_four_line_launch_uses_whole_unit_dynamic_identity(monkeypatch):
    snap = owner_snapshot(monkeypatch)
    assert len(owner_launch().splitlines()) == 4
    assert all(not line.startswith((b"User=", b"Group="))
               for raw in snap["source_bytes"].values() for line in raw.splitlines())
    plan = h.plan_from_snapshot(snap)
    assert plan["loaded"]["DynamicUser"] == "yes"
    assert (plan["loaded"]["User"], plan["loaded"]["Group"]) == ("enhanced-cognee-api",) * 2
    assert plan["activated"] is False and plan["services_restarted"] is False


def repin_invented_sources(monkeypatch, snap):
    # Only invented fixtures bypass real source pins, never production checks.
    monkeypatch.setattr(h, "SOURCE_HASHES", {
        p: h.digest(raw) for p, raw in snap["source_bytes"].items() if p != h.SOURCES[2]})


@pytest.mark.parametrize("source_index", range(4))
@pytest.mark.parametrize("keys", [("User",), ("Group",), ("User", "Group")])
def test_matching_explicit_identity_can_appear_in_any_known_fragment(monkeypatch, source_index, keys):
    snap = owner_snapshot(monkeypatch)
    snap["source_bytes"][h.SOURCES[source_index]] += "".join(
        key + "=enhanced-cognee-api\n" for key in keys).encode("ascii")
    repin_invented_sources(monkeypatch, snap)
    assert h.plan_from_snapshot(snap)["loaded"] == h.EXPECTED_LOADED


def test_repeated_matching_identity_across_fragments_is_consistent(monkeypatch):
    snap = owner_snapshot(monkeypatch)
    for path in h.SOURCES:
        snap["source_bytes"][path] += b"User=enhanced-cognee-api\nGroup=enhanced-cognee-api\n"
    repin_invented_sources(monkeypatch, snap)
    assert h.plan_from_snapshot(snap)["loaded"] == h.EXPECTED_LOADED


@pytest.mark.parametrize("source_index", range(4))
@pytest.mark.parametrize("key", ["User", "Group"])
@pytest.mark.parametrize("value", ["root", "0", "other-account"])
def test_conflicting_identity_anywhere_refused_even_if_overridden(monkeypatch, source_index, key, value):
    snap = owner_snapshot(monkeypatch)
    snap["source_bytes"][h.SOURCES[source_index]] += (key + "=" + value + "\n").encode()
    # When there is a later source, provide a matching override to detect last-wins bypasses.
    if source_index < 3:
        snap["source_bytes"][h.SOURCES[3]] += (key + "=enhanced-cognee-api\n").encode()
    repin_invented_sources(monkeypatch, snap)
    with pytest.raises(h.Refusal, match="^unit_syntax_or_directive_refused$"):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize("replacement", [b"", b"DynamicUser=no\n", b"DynamicUser=false\n",
    b"DynamicUser=0\n", b"DynamicUser=\n", b"DynamicUser=yes\nDynamicUser=no\n"])
def test_source_dynamic_user_must_be_present_and_yes(monkeypatch, replacement):
    snap = owner_snapshot(monkeypatch)
    snap["source_bytes"][h.SOURCES[0]] = snap["source_bytes"][h.SOURCES[0]].replace(
        b"DynamicUser=yes\n", replacement)
    repin_invented_sources(monkeypatch, snap)
    with pytest.raises(h.Refusal):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize("source_index", [1, 3])
@pytest.mark.parametrize("value", ["yes", "no"])
def test_dynamic_user_declarations_across_fragments_must_all_match(monkeypatch, source_index, value):
    snap = owner_snapshot(monkeypatch)
    snap["source_bytes"][h.SOURCES[source_index]] += ("DynamicUser=" + value + "\n").encode()
    repin_invented_sources(monkeypatch, snap)
    if value == "yes":
        assert h.plan_from_snapshot(snap)["loaded"]["DynamicUser"] == "yes"
    else:
        with pytest.raises(h.Refusal, match="^source_identity_drift$"):
            h.plan_from_snapshot(snap)


@pytest.mark.parametrize("unit", ["root.service", "wrong.service", "9invalid.service",
    "bad@instance.service", "enhanced-cognee-api.socket", "a" * 32 + ".service"])
def test_invalid_or_wrong_implicit_unit_identity_is_refused(monkeypatch, unit):
    snap = owner_snapshot(monkeypatch)
    monkeypatch.setattr(h, "UNIT", unit)
    with pytest.raises(h.Refusal, match="^source_identity_drift$"):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize("key,value", [("User", "root"), ("User", "other-account"),
    ("Group", "root"), ("Group", "other-account"), ("DynamicUser", "no"), ("DynamicUser", "")])
def test_default_identity_source_manager_disagreement_is_refused(monkeypatch, key, value):
    snap = owner_snapshot(monkeypatch)
    snap["loaded"][key] = value
    with pytest.raises(h.Refusal, match="^inventory_or_loaded_or_candidate_drift$"):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize("mutation", ["missing-reset", "extra-reset", "missing-command",
    "second-command", "wrong-command", "wrong-directory"])
def test_omitted_identity_does_not_relax_exact_launch_contract(monkeypatch, mutation):
    snap = owner_snapshot(monkeypatch)
    raw = owner_launch()
    command = ("ExecStart=" + h.OLD + "/runtime/bin/python -m src.memory_daemon api\n").encode()
    if mutation == "missing-reset":
        raw = raw.replace(b"ExecStart=\n", b"")
    elif mutation == "extra-reset":
        raw += b"ExecStart=\n"
    elif mutation == "missing-command":
        raw = raw.replace(command, b"")
    elif mutation == "second-command":
        raw += command
    elif mutation == "wrong-command":
        raw = raw.replace(b" -m ", b" -I -m ")
    else:
        raw = raw.replace(("WorkingDirectory=" + h.OLD).encode(), b"WorkingDirectory=/invented")
    snap["source_bytes"][h.SOURCES[2]] = raw
    with pytest.raises(h.Refusal, match="^unit_syntax_or_directive_refused$"):
        h.plan_from_snapshot(snap)


@pytest.mark.parametrize("injection", [b"LoadCredential=\n", b"LoadCredential=llm.json:/invented\n",
    b"SetCredential=hidden:invented-secret\n", b"ImportCredential=*\n",
    b"LoadCredentialEncrypted=hidden:/invented\n", b"EnvironmentFile=/invented\n",
    b"User=\n", b"Group=\n", b"DynamicUser=yes\n"])
def test_four_line_launch_still_rejects_injected_directives(monkeypatch, injection):
    snap = owner_snapshot(monkeypatch)
    snap["source_bytes"][h.SOURCES[2]] += injection
    with pytest.raises(h.Refusal, match="^unit_syntax_or_directive_refused$"):
        h.plan_from_snapshot(snap)


def test_owner_plan_entry_is_read_only_and_binds_v2_paths(monkeypatch, capsys):
    snap = owner_snapshot(monkeypatch)
    writes = []
    assert h.INSTALLED_HELPER == "/opt/enhanced-cognee-memory/security-first-helper-v2/prepare_security_first_cutover_v2.py"
    assert h.BUNDLE == "/opt/enhanced-cognee-memory/cutover/security-first-c14f595c-20261101-v2"
    assert h.main(["--plan"], runtime=lambda: None, output_guard=lambda: None,
                  collector=lambda: snap, writer=lambda *args: writes.append(args)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["plan_sha256"] == h.digest(h.canonical(h.plan_from_snapshot(snap)))
    assert result["plan"]["bundle"] == h.BUNDLE
    assert writes == []
