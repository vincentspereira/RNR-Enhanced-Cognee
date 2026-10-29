"""Owned, source-first UTF-8 Markdown library (Ubuntu, Python stdlib only).

No runtime/AI/database imports. Revisions are original Markdown plus JSON
provenance, never rewritten by this API. Directory-fd I/O forbids symlinks.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

MARKER = b'{"format": "enhanced-cognee-owned-library", "version": 1}\n'
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
MAX_SOURCE = 8 * 1024 * 1024
VIEW_SCRIPT = """'use strict';
const input = document.getElementById('search');
const articles = Array.from(document.querySelectorAll('article'));
const count = document.getElementById('count');
input.addEventListener('input', () => {
  const query = input.value.toLowerCase();
  let visible = 0;
  articles.forEach(article => {
    article.hidden = !article.textContent.toLowerCase().includes(query);
    if (!article.hidden) visible += 1;
  });
  count.textContent = visible + ' notes visible';
});
"""
VIEW_STYLE = """body { max-width: 70rem; margin: 2rem auto; padding: 1rem;
font-family: system-ui, sans-serif; color: #18212a; background: #fafafa; }
article { border: 1px solid #aab4bd; padding: 1rem; margin: 1rem 0; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #eef1f4; padding: 1rem; }
input { width: 90%; padding: .7rem; } summary { cursor: pointer; padding: .7rem; }
"""


class LibraryError(ValueError):
    """Invalid selection, unsafe path, damaged source, or rejected operation."""


def _path(value):
    path = Path(value)
    if ".." in path.parts:
        raise LibraryError("Parent traversal is not allowed")
    return Path(os.path.abspath(path))


@contextmanager
def _directory(path):
    """Walk from / with O_NOFOLLOW on every component (no resolve race)."""
    path = _path(path)
    fd = os.open("/", DIR_FLAGS)
    try:
        for component in path.parts[1:]:
            child = os.open(component, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _child(parent, name):
    fd = os.open(name, DIR_FLAGS, dir_fd=parent)
    try:
        yield fd
    finally:
        os.close(fd)


def _read(fd, name, limit=MAX_SOURCE):
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        info = os.fstat(handle)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise LibraryError("Only regular, non-hardlinked files are allowed")
        if info.st_size > limit:
            raise LibraryError("File exceeds size limit")
        with os.fdopen(handle, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise LibraryError("File exceeds size limit")
        return data
    finally:
        os.close(handle)


def _write(fd, name, data):
    handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=fd)
    try:
        os.fchmod(handle, 0o600)
        with os.fdopen(handle, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(handle)
    finally:
        os.close(handle)
    os.fsync(fd)


def _mkdir(fd, name):
    os.mkdir(name, 0o700, dir_fd=fd)
    with _child(fd, name) as child:
        os.fchmod(child, 0o700)
    os.fsync(fd)


def _json(data):
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _text(text):
    if not isinstance(text, str) or "\x00" in text:
        raise LibraryError("Source must be UTF-8 text without NUL")
    data = text.encode("utf-8")
    if len(data) > MAX_SOURCE:
        raise LibraryError("Source exceeds size limit")
    return data


def _label(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or "\x00" in value:
        raise LibraryError("Invalid " + name)
    return value


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value):
        raise LibraryError("Expected a canonical lowercase UUID")
    return value


def _metadata(meta):
    required = {"schema", "id", "revision", "title", "author", "kind", "origin", "reason", "created_at", "source_sha256"}
    optional = {"corrects", "previous_source_sha256", "previous_metadata_sha256"}
    if (not isinstance(meta, dict) or not required <= meta.keys()
            or set(meta) - required - optional or type(meta["schema"]) is not int or meta["schema"] != 1
            or type(meta["revision"]) is not int or meta["revision"] < 1 or meta["kind"] not in ("raw", "working")):
        raise LibraryError("Invalid revision metadata schema")
    _id(meta["id"])
    for key in ("title", "author", "origin", "reason", "created_at"):
        _label(meta[key], key)
    try:
        if datetime.fromisoformat(meta["created_at"]).tzinfo is None:
            raise ValueError("Timezone missing")
    except ValueError as exc:
        raise LibraryError("Invalid revision timestamp") from exc
    for key in ("source_sha256", "previous_source_sha256", "previous_metadata_sha256"):
        if key in meta and (not isinstance(meta[key], str) or not re.fullmatch(r"[0-9a-f]{64}", meta[key])):
            raise LibraryError("Invalid provenance hash")
    if "corrects" in meta:
        target = meta["corrects"]
        if not isinstance(target, dict) or set(target) != {"id", "revision", "source_sha256"}:
            raise LibraryError("Invalid correction link")
        _id(target["id"])
        if (type(target["revision"]) is not int or target["revision"] < 1
                or not isinstance(target["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", target["source_sha256"])):
            raise LibraryError("Invalid correction reference")


def read_markdown(path):
    """Explicit one-file selection, not directory ingestion or config access."""
    path = _path(path)
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]*\.md", path.name)
            or re.search(r"(?:^|[ _.-])(env|config|secret[s]?|credential[s]?|password[s]?|token[s]?)(?:[ _.-]|$)", path.stem, re.I)):
        raise LibraryError("Select a non-hidden Markdown note, not a config or secret file")
    with _directory(path.parent) as fd:
        data = _read(fd, path.name)
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise LibraryError("Source must be UTF-8") from exc
    _text(text)
    return text


class Library:
    def __init__(self, root):
        self.root = _path(root)
        with self._locked():
            pass

    @classmethod
    def initialize(cls, root):
        """Claim only a new directory; never adopt an existing vault."""
        root = _path(root)
        with _directory(root.parent) as parent:
            _mkdir(parent, root.name)
            with _child(parent, root.name) as fd:
                _write(fd, "library.json", MARKER)
                _mkdir(fd, "notes")
        return cls(root)

    @contextmanager
    def _locked(self):
        with _directory(self.root) as fd:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise LibraryError("Owned root must belong to you and have mode 0700")
            fcntl.flock(fd, fcntl.LOCK_EX)
            if _read(fd, "library.json") != MARKER:
                raise LibraryError("Not an owned library; refuse arbitrary roots")
            if set(os.listdir(fd)) != {"library.json", "notes"}:
                raise LibraryError("Unexpected files in library root")
            with _child(fd, "notes") as notes:
                yield fd, notes

    def _history(self, notes, note_id):
        _id(note_id)
        records = []
        previous_metadata = None
        with _child(notes, note_id) as note:
            names = sorted(os.listdir(note))
            if not names or names != [f"{i:06d}" for i in range(1, len(names) + 1)]:
                raise LibraryError("Non-contiguous or incomplete revision history")
            for number, name in enumerate(names, 1):
                with _child(note, name) as revision:
                    if set(os.listdir(revision)) != {"source.md", "metadata.json"}:
                        raise LibraryError("Unexpected or incomplete revision files")
                    data = _read(revision, "source.md")
                    raw_meta = _read(revision, "metadata.json")
                    meta = json.loads(raw_meta)
                    _metadata(meta)
                    if raw_meta != _json(meta):
                        raise LibraryError("Metadata must retain its original canonical encoding")
                    if meta["id"] != note_id or meta["revision"] != number or meta["source_sha256"] != _sha(data):
                        raise LibraryError("Source identity/checksum mismatch; refuse silent edits")
                    previous = records[-1] if records else None
                    if (meta.get("previous_metadata_sha256") != previous_metadata
                            or meta.get("previous_source_sha256") != (previous["source_sha256"] if previous else None)):
                        raise LibraryError("Revision provenance chain mismatch")
                    if previous and (previous["kind"] == "raw" or any(meta[k] != previous[k] for k in ("kind", "origin", "title"))
                                     or meta.get("corrects") != previous.get("corrects")):
                        raise LibraryError("Revision cannot change original provenance")
                    records.append({**meta, "text": data.decode("utf-8")})
                    previous_metadata = _sha(raw_meta)
        return records

    def _append(self, notes, meta, text):
        with _child(notes, meta["id"]) as note:
            name = f'{meta["revision"]:06d}'
            _mkdir(note, name)
            with _child(note, name) as revision:
                _write(revision, "source.md", _text(text))
                _write(revision, "metadata.json", _json(meta))
        return {**meta, "text": text}

    def create(self, text, *, title, author, corrects=None, reason=None):
        return self._create(text, title=title, author=author, kind="working",
                            origin="human-created", corrects=corrects, reason=reason)

    def import_source(self, path, *, title, author, origin):
        return self._create(read_markdown(path), title=title, author=author, kind="raw",
                            origin=_label(origin, "origin"), corrects=None,
                            reason="Imported evidence; source is immutable")

    def _create(self, text, *, title, author, kind, origin, corrects, reason):
        data = _text(text)
        meta = {"schema": 1, "id": str(uuid.uuid4()), "revision": 1,
                "title": _label(title, "title"), "author": _label(author, "author"),
                "kind": kind, "origin": origin,
                "reason": "Created by human" if reason is None else _label(reason, "reason"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_sha256": _sha(data)}
        with self._locked() as (_, notes):
            if corrects is not None:
                meta["reason"] = _label(reason, "correction reason")
                target = self._history(notes, corrects)[-1]
                meta["corrects"] = {k: target[k] for k in ("id", "revision", "source_sha256")}
            _mkdir(notes, meta["id"])
            return self._append(notes, meta, text)

    def history(self, note_id):
        with self._locked() as (_, notes):
            return self._history(notes, note_id)

    def update(self, note_id, text, *, expected_revision, author, reason):
        if type(expected_revision) is not int or expected_revision < 1:
            raise LibraryError("Expected revision must be a positive integer")
        data = _text(text)
        author = _label(author, "author")
        reason = _label(reason, "reason")
        with self._locked() as (_, notes):
            previous = self._history(notes, note_id)[-1]
            if previous["kind"] == "raw":
                raise LibraryError("Raw imported evidence is immutable; create a linked correction")
            if previous["revision"] != expected_revision:
                raise LibraryError("Stale revision; read again before updating")
            meta = {k: v for k, v in previous.items() if k != "text"}
            meta.update(revision=expected_revision + 1, author=author, reason=reason,
                        created_at=datetime.now(timezone.utc).isoformat(),
                        source_sha256=_sha(data),
                        previous_source_sha256=previous["source_sha256"],
                        previous_metadata_sha256=_sha(_json({k: v for k, v in previous.items() if k != "text"})))
            return self._append(notes, meta, text)

    def read(self, note_id, revision=None):
        with self._locked() as (_, notes):
            records = self._history(notes, note_id)
            if revision is None:
                return records[-1]
            if not isinstance(revision, int) or revision < 1 or revision > len(records):
                raise LibraryError("Unknown revision")
            return records[revision - 1]

    def export(self, destination):
        """New offline library copy, exact source and metadata bytes, all revisions."""
        destination = _path(destination)
        if destination == self.root or self.root in destination.parents:
            raise LibraryError("Export must be outside the source library")
        snapshot = []
        with self._locked() as (_, notes):
            for note_id in sorted(os.listdir(notes)):
                records = self._history(notes, note_id)
                with _child(notes, note_id) as note:
                    for record in records:
                        name = f'{record["revision"]:06d}'
                        with _child(note, name) as revision:
                            snapshot.append((note_id, name, _read(revision, "source.md"),
                                             _read(revision, "metadata.json")))
        target = Library.initialize(destination)
        with target._locked() as (_, notes):
            seen = set()
            for note_id, name, source, metadata in snapshot:
                if note_id not in seen:
                    _mkdir(notes, note_id)
                    seen.add(note_id)
                with _child(notes, note_id) as note:
                    _mkdir(note, name)
                    with _child(note, name) as revision:
                        _write(revision, "source.md", source)
                        _write(revision, "metadata.json", metadata)
        return {"destination": str(destination), "notes": len(seen), "revisions": len(snapshot)}

    def html_view(self, output):
        """Escaped read-only snapshot, all versions, fixed offline search script."""
        output = _path(output)
        if self.root in output.parents or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]*\.html", output.name):
            raise LibraryError("Select a new .html output outside the source library")
        articles = []
        with self._locked() as (_, notes):
            for note_id in sorted(os.listdir(notes)):
                records = self._history(notes, note_id)
                versions = []
                for record in records:
                    metadata = {k: v for k, v in record.items() if k != "text"}
                    opened = " open" if record is records[-1] else ""
                    versions.append(f'<details{opened}><summary>Revision {record["revision"]}</summary>'
                                    + '<pre>' + escape(_json(metadata).decode("ascii")) + '</pre>'
                                    + '<pre>' + escape(record["text"]) + '</pre></details>')
                articles.append('<article><h2>' + escape(records[-1]["title"]) + '</h2>'
                                + '<p>ID: ' + note_id + '</p>' + ''.join(versions) + '</article>')
        def digest(text):
            return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")
        csp = ("default-src 'none'; script-src 'sha256-" + digest(VIEW_SCRIPT)
               + "'; style-src 'sha256-" + digest(VIEW_STYLE)
               + "'; connect-src 'none'; base-uri 'none'; form-action 'none'")
        html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                + '<meta http-equiv="Content-Security-Policy" content="' + escape(csp, quote=True) + '">'
                + '<meta name="viewport" content="width=device-width, initial-scale=1">'
                + '<title>Enhanced Cognee owned library</title><style>' + VIEW_STYLE + '</style></head><body>'
                + '<h1>Owned library - Read-only snapshot</h1>'
                + '<p>No browser changes are saved. Edit working notes with the CLI. '
                + 'This reading view is not full Obsidian GUI parity.</p>'
                + '<p>Generated: ' + escape(datetime.now(timezone.utc).isoformat()) + '</p>'
                + '<label for="search">Search displayed notes, provenance and revision history</label>'
                + '<input type="search" id="search" autocomplete="off">'
                + f'<p id="count" role="status">{len(articles)} notes visible</p>'
                + '<noscript>Search needs the bundled offline script; browser Find still works.</noscript>'
                + ''.join(articles) + '<script>' + VIEW_SCRIPT + '</script></body></html>')
        with _directory(output.parent) as fd:
            _write(fd, output.name, html.encode("utf-8"))
        return {"output": str(output), "notes": len(articles), "read_only": True}

    def search(self, query, *, include_history=False):
        query = _label(query, "search query").casefold()
        results = []
        with self._locked() as (_, notes):
            for note_id in sorted(os.listdir(notes)):
                records = self._history(notes, note_id)
                for record in records if include_history else records[-1:]:
                    if query in (record["title"] + "\n" + record["text"]).casefold():
                        results.append(record)
        return results

    def list(self):
        with self._locked() as (_, notes):
            return [{k: v for k, v in self._history(notes, note_id)[-1].items() if k != "text"}
                    for note_id in sorted(os.listdir(notes))]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Owned Markdown library; no Obsidian, AI, database, or service")
    parser.add_argument("--root", required=True, help="Explicit owned root (never the Brain vault)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create a new private owned root")
    commands.add_parser("list")
    read = commands.add_parser("read")
    read.add_argument("id")
    read.add_argument("--revision", type=int)
    create = commands.add_parser("create")
    create.add_argument("--file", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--author", required=True)
    create.add_argument("--corrects", help="ID of evidence/note being annotated (does not change it)")
    create.add_argument("--reason", help="Required for a linked correction")
    imported = commands.add_parser("import", help="Copy one deliberately selected immutable Markdown source")
    imported.add_argument("--file", required=True)
    imported.add_argument("--title", required=True)
    imported.add_argument("--author", required=True)
    imported.add_argument("--origin", required=True, help="Human-supplied provenance, not fetched")
    history = commands.add_parser("history")
    history.add_argument("id")
    update = commands.add_parser("update")
    update.add_argument("id")
    update.add_argument("--file", required=True)
    update.add_argument("--expect-revision", type=int, required=True)
    update.add_argument("--author", required=True)
    update.add_argument("--reason", required=True)
    export = commands.add_parser("export", help="Exact all-revision copy to a new root, not a second live authority")
    export.add_argument("--destination", required=True)
    search = commands.add_parser("search", help="Case-insensitive literal title/source search (no index)")
    search.add_argument("query")
    search.add_argument("--history", action="store_true")
    view = commands.add_parser("view", help="New self-contained HTML reading/search snapshot; no browser editing")
    view.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            Library.initialize(args.root)
            result = {"root": str(_path(args.root)), "initialized": True}
        else:
            library = Library(args.root)
            if args.command == "read":
                sys.stdout.buffer.write(library.read(args.id, args.revision)["text"].encode("utf-8"))
                return 0
            if args.command == "list":
                result = library.list()
            elif args.command == "history":
                result = library.history(args.id)
            elif args.command == "update":
                result = library.update(args.id, read_markdown(args.file),
                                        expected_revision=args.expect_revision,
                                        author=args.author, reason=args.reason)
            elif args.command == "import":
                result = library.import_source(args.file, title=args.title, author=args.author,
                                               origin=args.origin)
            elif args.command == "export":
                result = library.export(args.destination)
            elif args.command == "search":
                result = library.search(args.query, include_history=args.history)
            elif args.command == "view":
                result = library.html_view(args.output)
            else:
                result = library.create(read_markdown(args.file), title=args.title, author=args.author,
                                        corrects=args.corrects, reason=args.reason)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (LibraryError, OSError, UnicodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("Library error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
