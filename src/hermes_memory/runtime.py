"""Local vector recall using Enhanced Cognee's existing LanceDB adapter.

SQLite is a revision/control ledger, never a lexical or semantic search backend.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import fcntl
import hashlib
import os
import threading
import json
import math
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import uuid

from src.db_adapters.vector_lancedb import create_client


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._locked():
            return method(self, *args, **kwargs)
    return call


class EnhancedMemoryEngine:
    @contextmanager
    def _locked(self):
        with self._thread_lock:
            if self._pid != os.getpid():
                raise RuntimeError('Open a new engine after fork; inherited engine is unsupported')
            if self._closed:
                raise RuntimeError('Memory engine is closed')
            for name in ('vectors', 'control.sqlite3', 'control.sqlite3-journal'):
                if (self.root / name).is_symlink():
                    raise ValueError(f'Owned memory path must not be a symlink: {name}')
            fd = os.open(self.root / 'writer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    self._secure_files()
                finally:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    finally:
                        os.close(fd)

    def _secure_files(self):
        for name in ('control.sqlite3', 'control.sqlite3-journal', 'writer.lock'):
            path = self.root / name
            if path.exists() and not path.is_symlink():
                path.chmod(0o600)
        vectors = self.root / 'vectors'
        if vectors.exists() and not vectors.is_symlink():
            for directory, dirs, files in os.walk(vectors, followlinks=False):
                Path(directory).chmod(0o700)
                for name in files:
                    path = Path(directory) / name
                    if not path.is_symlink():
                        path.chmod(0o600)

    def __init__(self, root: Path, embedder):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.embedder = embedder
        self._dimension = embedder.dimension
        if type(self._dimension) is not int or self._dimension < 1:
            raise ValueError('Embedding dimension must be a positive integer')
        self._fingerprint = str(getattr(embedder, 'fingerprint',
            f'{type(embedder).__module__}.{type(embedder).__qualname__}:{self._dimension}'))
        self._thread_lock = threading.RLock()
        self._pid = os.getpid()
        self._closed = False
        with self._locked():
            self._initialize()

    def _initialize(self):
        fd = os.open(self.root / 'control.sqlite3', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        (self.root / 'vectors').mkdir(exist_ok=True, mode=0o700)
        self._db = sqlite3.connect(self.root / 'control.sqlite3', check_same_thread=False)
        self._db.execute('PRAGMA synchronous=FULL')
        self._db.row_factory = sqlite3.Row
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS revisions (
                scope TEXT NOT NULL, source_id TEXT NOT NULL, revision INTEGER NOT NULL,
                content_hash TEXT NOT NULL, text TEXT NOT NULL, metadata TEXT NOT NULL,
                vector_id TEXT NOT NULL UNIQUE, PRIMARY KEY(scope,source_id,revision));
            CREATE TABLE IF NOT EXISTS heads (
                scope TEXT NOT NULL, source_id TEXT NOT NULL, revision INTEGER NOT NULL,
                withdrawn INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,source_id));
            CREATE TABLE IF NOT EXISTS configuration (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        expected = json.dumps({'dimension': self._dimension, 'fingerprint': self._fingerprint}, sort_keys=True)
        previous = self._db.execute("SELECT value FROM configuration WHERE key='embedding'").fetchone()
        if previous and previous[0] != expected:
            self._db.close()
            raise ValueError('Embedding identity/dimension differs from this root; use a new root')
        with self._db:
            self._db.execute("INSERT OR IGNORE INTO configuration VALUES ('embedding',?)", (expected,))

    @staticmethod
    def _nonempty(value, name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{name} must be a nonempty string')

    def _vector(self, text, *, query=False):
        hook = getattr(self.embedder, 'embed_query', None)
        if query and callable(hook):
            vector = hook(text)
        else:
            batch = self.embedder.embed([text])
            if len(batch) != 1:
                raise ValueError('Embedder returned incorrect batch size')
            vector = batch[0]
        if len(vector) != self._dimension or any(not math.isfinite(float(x)) for x in vector):
            raise ValueError('Embedding has wrong dimension or nonfinite coordinates')
        vector = [float(x) for x in vector]
        if not sum(x*x for x in vector) > 0:
            raise ValueError('Zero embedding is not searchable')
        return vector

    @staticmethod
    def _matches(hit, vector_id, revision, digest, *, self_search=False):
        return (hit.id == vector_id and isinstance(hit.payload, dict)
                and hit.payload.get('revision') == revision
                and hit.payload.get('content_hash') == digest
                and math.isfinite(hit.score)
                and (not self_search or hit.score >= 0.999))

    def _collection(self, scope):
        return 'scope_' + hashlib.sha256(scope.encode()).hexdigest()

    def _client(self, scope):
        client = create_client(url=str(self.root / 'vectors'))
        client.create_collection(self._collection(scope),
                                 SimpleNamespace(size=self.embedder.dimension, distance='cosine'))
        return client

    @_serialized
    def upsert(self, source_id: str, text: str, scope: str, metadata: dict | None = None) -> dict:
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError('An explicit nonempty trusted scope is required')
        self._nonempty(source_id, 'source_id')
        self._nonempty(text, 'text')
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError('metadata must be a JSON object or None')
        try:
            meta = json.dumps(metadata if metadata is not None else {}, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError('metadata must be a finite JSON object') from exc
        digest = hashlib.sha256(text.encode()).hexdigest()
        old = self._db.execute('''SELECT r.*, h.withdrawn FROM revisions r JOIN heads h
            USING(scope,source_id,revision) WHERE scope=? AND source_id=?''',
                               (scope, source_id)).fetchone()
        if old and not old['withdrawn'] and old['content_hash'] == digest and old['metadata'] == meta:
            client = self._client(scope)
            try:
                hits = client.search(self._collection(scope), self._vector(text),
                                     limit=client.count(self._collection(scope)).count)
                if not any(self._matches(h, old['vector_id'], old['revision'], digest, self_search=True) for h in hits):
                    raise RuntimeError('Active vector is missing; no indexed claim')
            finally:
                client.close()
            return {'source_id': source_id, 'revision': old['revision'],
                    'content_hash': digest, 'indexed': True}
        revision = old['revision'] + 1 if old else 1
        vector_id = uuid.uuid4().hex
        vector = self._vector(text)
        client = self._client(scope)
        try:
            client.upsert(self._collection(scope), [SimpleNamespace(
                id=vector_id, vector=vector, payload={'revision': revision, 'content_hash': digest})])
            hits = client.search(self._collection(scope), vector,
                                 limit=client.count(self._collection(scope)).count)
            if not any(self._matches(h, vector_id, revision, digest, self_search=True) for h in hits):
                raise RuntimeError('Vector write was not verified; source unchanged')
            with self._db:
                self._db.execute('INSERT INTO revisions VALUES (?,?,?,?,?,?,?)',
                                 (scope, source_id, revision, digest, text, meta, vector_id))
                self._db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,0)',
                                 (scope, source_id, revision))
        finally:
            client.close()
        return {'source_id': source_id, 'revision': revision, 'content_hash': digest, 'indexed': True}

    @_serialized
    def search(self, query: str, scope: str, limit: int = 5, min_score: float | None = None) -> list[dict]:
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError('An explicit nonempty trusted scope is required')
        self._nonempty(query, 'query')
        if type(limit) is not int or limit < 0:
            raise ValueError('limit must be a nonnegative integer')
        if min_score is not None and (isinstance(min_score, bool) or
                not isinstance(min_score, (int, float)) or not math.isfinite(min_score)):
            raise ValueError('min_score must be finite or None')
        if limit == 0:
            return []
        rows = self._db.execute('''SELECT r.* FROM revisions r JOIN heads h
            USING(scope,source_id,revision) WHERE h.scope=? AND h.withdrawn=0''', (scope,)).fetchall()
        if not rows:
            return []
        active = {r['vector_id']: r for r in rows}
        client = self._client(scope)
        try:
            hits = client.search(self._collection(scope), self._vector(query, query=True),
                                 limit=client.count(self._collection(scope)).count)
        finally:
            client.close()
        result = []
        for hit in hits:
            row = active.get(hit.id)
            if (row is None or not self._matches(hit, row['vector_id'], row['revision'], row['content_hash'])
                    or (min_score is not None and hit.score < min_score)):
                continue
            result.append({'source_id': row['source_id'], 'text': row['text'],
                           'score': hit.score, 'metadata': json.loads(row['metadata']),
                           'revision': row['revision']})
        return result[:limit]

    @_serialized
    def withdraw(self, source_id: str, scope: str) -> dict:
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError('An explicit nonempty trusted scope is required')
        self._nonempty(source_id, 'source_id')
        with self._db:
            self._db.execute('UPDATE heads SET withdrawn=1 WHERE scope=? AND source_id=?',
                             (scope, source_id))
        row = self._db.execute('SELECT revision,withdrawn FROM heads WHERE scope=? AND source_id=?',
                               (scope, source_id)).fetchone()
        return {'source_id': source_id, 'withdrawn': bool(row and row['withdrawn']),
                'revision': row['revision'] if row else None}

    @_serialized
    def stats(self, scope: str) -> dict:
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError('An explicit nonempty trusted scope is required')
        counts = self._db.execute('''SELECT COUNT(*) AS sources,
            COALESCE(SUM(withdrawn=0),0) AS active,
            COALESCE(SUM(withdrawn=1),0) AS withdrawn FROM heads WHERE scope=?''', (scope,)).fetchone()
        revisions = self._db.execute('SELECT COUNT(*) FROM revisions WHERE scope=?', (scope,)).fetchone()[0]
        return {**dict(counts), 'revisions': revisions, 'dimension': self.embedder.dimension,
                'vector_backend': 'enhanced-cognee-lancedb'}

    def close(self) -> None:
        with self._thread_lock:
            if self._closed:
                return
            with self._locked():
                self._db.close()
                self._closed = True
