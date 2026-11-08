"""Synthetic, stdlib-only acceptance tests for the owned Markdown library."""
import importlib.util
import base64
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "src/hermes_memory/library.py"
CLI = REPO / "bin/enhanced_cognee_library.py"


def load_library():
    assert MODULE.is_file(), "Owned-library implementation is missing"
    spec = importlib.util.spec_from_file_location("owned_library_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ViewParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.scripts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "script":
            self.in_script = True
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_cli(self, root, *args):
        return subprocess.run([sys.executable, str(CLI), "--root", str(root), *args],
                              capture_output=True, check=True)

    def test_create_reopen_source_exact_and_private_cli(self):
        lib = load_library()
        root = self.base / "owned"
        lib.Library.initialize(root)
        text = "# Working note\r\n\r\nCafe: caf\u00e9.\r\n"
        source = self.base / "working.md"
        source.write_bytes(text.encode("utf-8"))
        result = json.loads(self.run_cli(root, "create", "--file", str(source),
                            "--title", "Working", "--author", "Synthetic").stdout)
        note_id = result["id"]
        self.assertEqual(self.run_cli(root, "read", note_id).stdout, source.read_bytes())
        reopened = lib.Library(root)
        self.assertEqual(reopened.read(note_id)["text"], text)
        self.assertEqual(reopened.list()[0]["id"], note_id)
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        original = root / "notes" / note_id / "000001" / "source.md"
        self.assertEqual(original.read_bytes(), source.read_bytes())
        self.assertEqual(stat.S_IMODE(original.stat().st_mode), 0o600)
    def test_update_preserves_versions_and_rejects_stale_writer(self):
        lib = load_library()
        self.assertTrue(hasattr(lib.Library, "update"), "Revision update is missing")
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        first = library.create("# First\r\n", title="Draft", author="Synthetic")
        second = library.update(first["id"], "# Corrected\n", expected_revision=1,
                                author="Reviewer", reason="Corrected the heading")
        self.assertEqual(second["revision"], 2)
        self.assertEqual(library.read(first["id"], 1)["text"], "# First\r\n")
        self.assertEqual([r["reason"] for r in library.history(first["id"])],
                         ["Created by human", "Corrected the heading"])
        self.assertEqual(second["previous_source_sha256"], first["source_sha256"])
        with self.assertRaises(lib.LibraryError):
            library.update(first["id"], "Lost update", expected_revision=1,
                           author="Reviewer", reason="stale")
        with self.assertRaises(lib.LibraryError):
            library.update(first["id"], "Bad", expected_revision=2, author="Reviewer", reason="")
        self.assertEqual(lib.Library(root).read(first["id"])["text"], "# Corrected\n")
        replacement = self.base / "replacement.md"
        replacement.write_bytes(b"# CLI corrected\r\n")
        self.run_cli(root, "update", first["id"], "--file", str(replacement),
                     "--expect-revision", "2", "--author", "CLI", "--reason", "CLI correction")
        self.assertEqual(self.run_cli(root, "read", first["id"], "--revision", "2").stdout,
                         b"# Corrected\n")
        self.assertEqual(len(json.loads(self.run_cli(root, "history", first["id"]).stdout)), 3)
    def test_raw_import_is_immutable_and_correction_is_linked(self):
        lib = load_library()
        self.assertTrue(hasattr(lib.Library, "import_source"), "Explicit raw import is missing")
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        raw = self.base / "evidence.md"
        raw.write_bytes(b"# Quoted evidence\r\nDo not change.\r\n")
        imported = json.loads(self.run_cli(root, "import", "--file", str(raw), "--title", "Evidence",
                             "--author", "Synthetic", "--origin", "synthetic:document-v1").stdout)
        self.assertEqual(imported["kind"], "raw")
        with self.assertRaises(lib.LibraryError):
            library.update(imported["id"], "Overwritten", expected_revision=1,
                           author="Synthetic", reason="rewrite raw")
        correction = library.create("# Human annotation\n", title="Correction", author="Reviewer",
                                    corrects=imported["id"], reason="Clarify quotation")
        self.assertEqual(correction["corrects"]["id"], imported["id"])
        self.assertEqual(correction["corrects"]["source_sha256"], imported["source_sha256"])
        self.assertEqual(library.read(imported["id"])["text"].encode("utf-8"), raw.read_bytes())
        self.assertEqual(library.read(imported["id"])["origin"], "synthetic:document-v1")
        with self.assertRaises(lib.LibraryError):
            library.create("annotation", title="Correction", author="Reviewer", corrects=imported["id"])
    def test_export_preserves_all_sources_metadata_and_reopens(self):
        lib = load_library()
        self.assertTrue(hasattr(lib.Library, "export"), "Source-preserving export is missing")
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        first = library.create("# Original\r\nUnicode: \u03b1\r\n", title="Export", author="Synthetic")
        library.update(first["id"], "# Revised\n", expected_revision=1,
                       author="Reviewer", reason="Reviewed")
        raw = self.base / "evidence.md"
        raw.write_bytes(b"# Evidence\r\n")
        imported = library.import_source(raw, title="Evidence", author="Synthetic", origin="synthetic:v1")
        destination = self.base / "exported"
        result = json.loads(self.run_cli(root, "export", "--destination", str(destination)).stdout)
        self.assertEqual(result["notes"], 2)
        self.assertEqual(result["revisions"], 3)
        before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        after = {str(p.relative_to(destination)): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.run_cli(destination, "read", imported["id"]).stdout, raw.read_bytes())
        self.assertEqual(lib.Library(destination).history(first["id"]), library.history(first["id"]))
        with self.assertRaises((lib.LibraryError, OSError)):
            library.export(destination)
        with self.assertRaises(lib.LibraryError):
            library.export(root / "child")
        self.assertFalse((root / "child").exists())
    def test_search_current_sources_without_hidden_index(self):
        lib = load_library()
        self.assertTrue(hasattr(lib.Library, "search"), "Local source search is missing")
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        first = library.create("# Cafe\nStra\u00dfe evidence", title="Title only", author="Synthetic")
        library.update(first["id"], "# Corrected\n", expected_revision=1, author="Reviewer", reason="Reviewed")
        second = library.create("# Stra\u00dfe\n", title="Second", author="Synthetic")
        self.assertEqual([r["id"] for r in library.search("STRASSE")], [second["id"]])
        self.assertEqual(len(library.search("STRASSE", include_history=True)), 2)
        self.assertEqual(library.search("Title only")[0]["id"], first["id"])
        self.assertEqual(json.loads(self.run_cli(root, "search", "corrected").stdout)[0]["id"], first["id"])
        with self.assertRaises(lib.LibraryError):
            library.search(" ")


    def test_html_reading_view_escapes_every_field_is_read_only_and_self_contained(self):
        lib = load_library()
        self.assertTrue(hasattr(lib.Library, "html_view"), "Offline HTML view is missing")
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        attack = '</pre><script>alert("x")</script><img src="https://invalid.test/x" onerror="alert(1)">'
        first = library.create(attack, title=attack, author=attack)
        library.update(first["id"], "# Reviewed source\n", expected_revision=1,
                       author="Reviewer", reason=attack)
        output = self.base / "reading.html"
        self.run_cli(root, "view", "--output", str(output))
        html = output.read_text(encoding="utf-8")
        parser = ViewParser()
        parser.feed(html)
        self.assertEqual(len(parser.scripts), 1)
        self.assertNotIn("alert", parser.scripts[0])
        self.assertNotIn(attack, html)
        self.assertIn("&lt;/pre&gt;&lt;script&gt;", html)
        self.assertIn("Read-only snapshot", html)
        self.assertIn("No browser changes are saved", html)
        self.assertIn("Revision 1", html)
        self.assertIn("Revision 2", html)
        self.assertIn("type=\"search\"", html)
        self.assertIn("textContent", parser.scripts[0])
        self.assertNotIn("innerHTML", parser.scripts[0])
        for tag, attrs in parser.tags:
            self.assertFalse(any(k.startswith("on") for k in attrs))
            self.assertNotIn(tag, {"img", "iframe", "object", "embed", "link", "form", "textarea"})
            self.assertNotIn("src", attrs)
            self.assertNotIn("contenteditable", attrs)
        csp = next(attrs["content"] for tag, attrs in parser.tags
                   if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy")
        digest = base64.b64encode(hashlib.sha256(parser.scripts[0].encode()).digest()).decode()
        self.assertIn("'sha256-" + digest + "'", csp)
        self.assertIn("default-src 'none'", csp)
        self.assertIn("connect-src 'none'", csp)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        with self.assertRaises((lib.LibraryError, OSError)):
            library.html_view(output)
        with self.assertRaises(lib.LibraryError):
            library.html_view(root / "reading.html")


    def test_revision_chain_rejects_disconnected_metadata(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        first = library.create("First", title="Draft", author="Synthetic")
        library.update(first["id"], "Second", expected_revision=1, author="Reviewer", reason="Reviewed")
        metadata = root / "notes" / first["id"] / "000002" / "metadata.json"
        payload = json.loads(metadata.read_bytes())
        payload["previous_source_sha256"] = "0" * 64
        metadata.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(lib.LibraryError):
            library.read(first["id"])

    def test_prior_provenance_edits_are_detected_by_metadata_chain(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        first = library.create("First", title="Draft", author="Synthetic")
        second = library.update(first["id"], "Second", expected_revision=1, author="Reviewer", reason="Reviewed")
        self.assertIn("previous_metadata_sha256", second, "Provenance chain is missing")
        metadata = root / "notes" / first["id"] / "000001" / "metadata.json"
        payload = json.loads(metadata.read_bytes())
        payload["origin"] = "forged"
        metadata.write_bytes(lib._json(payload))
        with self.assertRaises(lib.LibraryError):
            library.history(first["id"])

    def test_safe_paths_file_allowlist_and_private_root(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        selected = self.base / "note.md"
        selected.write_bytes(b"# Synthetic\n")
        self.assertEqual(lib.read_markdown(selected), "# Synthetic\n")
        for name in (".env", "credentials.md", "config.md", "secrets.md", "note.txt", ".hidden.md", "note.md.env"):
            path = self.base / name
            path.write_bytes(b"do not ingest")
            with self.subTest(name=name), self.assertRaises(lib.LibraryError):
                lib.read_markdown(path)
        link = self.base / "link.md"
        link.symlink_to(selected)
        parent_link = self.base / "linked-parent"
        parent_link.symlink_to(self.base, target_is_directory=True)
        hardlink = self.base / "hard.md"
        os.link(selected, hardlink)
        for path in (link, parent_link / "note.md", hardlink, self.base / "x" / ".." / "note.md"):
            with self.subTest(path=path), self.assertRaises((lib.LibraryError, OSError)):
                lib.read_markdown(path)
        root_link = self.base / "root-link"
        root_link.symlink_to(root, target_is_directory=True)
        with self.assertRaises(OSError):
            lib.Library(root_link)
        with self.assertRaises(OSError):
            library.export(parent_link / "exported")
        with self.assertRaises(OSError):
            library.html_view(parent_link / "reading.html")
        with self.assertRaises(OSError):
            lib.Library.initialize(root)
        root.chmod(0o755)
        with self.assertRaises(lib.LibraryError):
            lib.Library(root)

    def test_modified_source_and_incomplete_revisions_fail_closed(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        note = library.create("Original", title="Draft", author="Synthetic")
        source = root / "notes" / note["id"] / "000001" / "source.md"
        source.write_bytes(b"Unauthorized direct edit")
        with self.assertRaises(lib.LibraryError):
            library.update(note["id"], "New", expected_revision=1, author="Synthetic", reason="review")
        with self.assertRaises(lib.LibraryError):
            library.export(self.base / "rejected-export")
        self.assertFalse((self.base / "rejected-export").exists())
        source.write_bytes(b"Original")
        (source.parent.parent / "000002").mkdir(mode=0o700)
        with self.assertRaises(lib.LibraryError):
            library.read(note["id"])

    def test_rejects_invalid_utf8_nul_and_invalid_identifiers(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        selected = self.base / "note.md"
        for data in (b"\xff\xfe", b"# Binary\x00"):
            selected.write_bytes(data)
            with self.assertRaises(lib.LibraryError):
                lib.read_markdown(selected)
        for note_id in ("../../escape", "123", "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"):
            with self.assertRaises(lib.LibraryError):
                library.read(note_id)
        self.assertEqual(library.list(), [])


    def test_metadata_schema_is_validated_before_read_or_update(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        note = library.create("Source", title="Draft", author="Synthetic")
        metadata = root / "notes" / note["id"] / "000001" / "metadata.json"
        original = metadata.read_bytes()
        for key, value in (("schema", 99), ("revision", True), ("kind", "unknown"),
                           ("author", ""), ("created_at", "not-a-date"), ("text", "forged source")):
            payload = json.loads(original)
            payload[key] = value
            metadata.write_bytes(lib._json(payload))
            with self.subTest(key=key), self.assertRaises(lib.LibraryError):
                library.read(note["id"])
        metadata.write_bytes(original)
        with self.assertRaises(lib.LibraryError):
            library.update(note["id"], "new", expected_revision=True, author="Synthetic", reason="bad")

    def test_invalid_create_reason_does_not_leave_an_unreadable_note(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        for reason in (7, "", "\x00"):
            with self.subTest(reason=reason), self.assertRaises(lib.LibraryError):
                library.create("Source", title="Draft", author="Synthetic", reason=reason)
        self.assertEqual(library.list(), [])

    def test_two_cli_writers_cannot_overwrite_one_revision(self):
        lib = load_library()
        root = self.base / "owned"
        library = lib.Library.initialize(root)
        note = library.create("Source", title="Draft", author="Synthetic")
        selected = self.base / "change.md"
        selected.write_bytes(b"# Change\n")
        command = [sys.executable, str(CLI), "--root", str(root), "update", note["id"],
                   "--file", str(selected), "--expect-revision", "1", "--author", "Synthetic", "--reason", "review"]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        outputs = [process.communicate(timeout=30) for process in processes]
        self.assertEqual(sorted(p.returncode for p in processes), [0, 2])
        self.assertTrue(any(b"Stale revision" in error for _, error in outputs))
        self.assertEqual(len(library.history(note["id"])), 2)
        self.assertEqual(library.read(note["id"], 1)["text"], "Source")


    def test_bundled_filter_script_runs_against_synthetic_dom(self):
        lib = load_library()
        node = shutil.which("node")
        if not node:
            self.skipTest("Node not installed; no packages will be downloaded")
        harness = """const fs = require('node:fs');
const vm = require('node:vm');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
let callback;
const input = {value: '', addEventListener: (event, fn) => {callback = fn;}};
const count = {textContent: ''};
const articles = [{textContent: 'Alpha history', hidden: false}, {textContent: 'Beta provenance', hidden: false}];
const document = {getElementById: id => id === 'search' ? input : count, querySelectorAll: () => articles};
vm.runInNewContext(payload.script, {document});
input.value = 'ALPHA'; callback();
const filtered = articles.map(article => article.hidden);
const message = count.textContent;
input.value = ''; callback();
console.log(JSON.stringify({filtered, message, restored: articles.map(article => article.hidden)}));
"""
        result = subprocess.run([node, "-e", harness], input=json.dumps({"script": lib.VIEW_SCRIPT}),
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {"filtered": [False, True],
                         "message": "1 notes visible", "restored": [False, False]})


if __name__ == "__main__":
    unittest.main()
