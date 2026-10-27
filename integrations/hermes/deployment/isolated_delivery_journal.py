"""Private metadata-only, append-only reservations for isolated text delivery.

Every transition is exclusive-create + file fsync + directory fsync. Interrupted
or partial transitions are preserved and block replay. No message, reply, token
or social-platform identity is stored. Digests are not encryption. This journal
is crash evidence under one trusted OS identity, not protection against that
identity altering its own files and not an exactly-once external delivery claim.
"""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from isolated_gateway_transport import envelope, identifier
from isolated_native_text_ingress import native_event, outbound_packet


class JournalError(RuntimeError):
    """Fixed categories only; no private paths, native errors or payloads."""


def require(value, category='delivery_journal_refused'):
    if not value:
        raise JournalError(category)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def io_boundary(function):
    @wraps(function)
    def guarded(*args,**kwargs):
        try:return function(*args,**kwargs)
        except OSError:raise JournalError('journal_io_failed') from None
    return guarded


class DeliveryJournal:
    STAGES = ('reserved','handled','sending','sent')

    @io_boundary
    def __init__(self, directory, *, profile_id, maximum_requests=1024):
        self.directory_fd = self.lock_fd = None
        try:
            require(identifier(profile_id,16) and type(maximum_requests) is int and 0 < maximum_requests <= 1024)
            require(os.getuid() == os.geteuid() > 0, 'unprivileged_journal_owner_required')
            self.uid, self.profile_id, self.maximum_requests = os.geteuid(), profile_id, maximum_requests
            path = Path(directory)
            require(path.is_absolute() and '..' not in path.parts)
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
            try:
                for part in path.parts[1:]:
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = next_fd
                    info = os.fstat(fd)
                    # Root-owned sticky ancestors (e.g. /tmp) cannot let another
                    # UID replace this owner's private child directory.
                    require(info.st_uid in {0,self.uid} and (not info.st_mode & 0o022
                        or info.st_uid == 0 and info.st_mode & stat.S_ISVTX), 'journal_ancestor_refused')
                info = os.fstat(fd)
                require(info.st_uid == self.uid and stat.S_IMODE(info.st_mode) == 0o700,
                    'private_journal_directory_required')
                self.directory_fd = fd; fd = None
            finally:
                if fd is not None:os.close(fd)
            self.lock_fd = os.open('.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600, dir_fd=self.directory_fd)
            self._file_info(self.lock_fd)
            with self._locked():
                binding = dict(version=1,profile_id=profile_id,uid=self.uid,maximum_requests=maximum_requests)
                try:self._write('binding.json',binding)
                except FileExistsError:require(self._read('binding.json') == binding, 'journal_binding_changed')
                self._inventory()
        except BaseException:
            self.close()
            raise

    def _file_info(self, fd):
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == self.uid and info.st_nlink == 1
            and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= 4096, 'private_journal_file_required')
        return info

    @contextmanager
    def _locked(self):
        require(self.directory_fd is not None and self.lock_fd is not None, 'journal_closed')
        require(os.fstat(self.directory_fd).st_uid == self.uid
            and stat.S_IMODE(os.fstat(self.directory_fd).st_mode) == 0o700)
        lock = self._file_info(self.lock_fd)
        named = os.stat('.lock', dir_fd=self.directory_fd, follow_symlinks=False)
        require((lock.st_dev,lock.st_ino) == (named.st_dev,named.st_ino), 'journal_lock_changed')
        try:fcntl.flock(self.lock_fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise JournalError('journal_busy') from None
        try:yield
        finally:fcntl.flock(self.lock_fd,fcntl.LOCK_UN)

    def _write(self, name, value):
        raw = canonical(value)
        require(len(raw) <= 4096)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600, dir_fd=self.directory_fd)
        with os.fdopen(fd,'wb') as stream:
            self._file_info(stream.fileno())
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.fsync(self.directory_fd)

    def _read(self, name):
        fd = os.open(name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=self.directory_fd)
        with os.fdopen(fd,'rb') as stream:
            before = self._file_info(stream.fileno());raw = stream.read(4097)
            after = self._file_info(stream.fileno())
            require(len(raw) == before.st_size and all(getattr(before,key) == getattr(after,key)
                for key in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')))
        try:value = json.loads(raw)
        except (ValueError,UnicodeError):raise JournalError('journal_record_invalid') from None
        require(canonical(value) == raw, 'journal_record_invalid')
        return value

    def _inventory(self):
        names = []
        with os.scandir(self.directory_fd) as entries:
            for entry in entries:
                names.append(entry.name)
                require(len(names) <= self.maximum_requests * 4 + 2, 'journal_capacity_exceeded')
        rows = {}
        for name in names:
            if name in {'binding.json','.lock'}:continue
            match = re.fullmatch(r'([a-f0-9]{32})\.(reserved|handled|sending|sent)\.json',name)
            require(match is not None, 'unexpected_journal_entry')
            rows.setdefault(match[1],set()).add(match[2])
        require(len(rows) <= self.maximum_requests, 'journal_capacity_exceeded')
        for stages in rows.values():
            count = len(stages)
            require(stages == set(self.STAGES[:count]), 'journal_transition_gap')
        return rows

    def _record(self, request_id, stage):
        value = self._read(request_id + '.' + stage + '.json')
        base = {'version','profile_id','request_id','request_digest','stage'}
        fields = base | (set() if stage == 'reserved' else {'response_digest'})
        if stage == 'sent':fields |= {'external_id_digest'}
        require(isinstance(value,dict) and set(value) == fields and type(value.get('version')) is int
            and value['version'] == 1 and value['profile_id'] == self.profile_id
            and value['request_id'] == request_id and value['stage'] == stage
            and all(isinstance(value[key],str) and re.fullmatch('[a-f0-9]{64}',value[key])
                for key in fields if key.endswith('_digest')), 'journal_record_invalid')
        return value

    def _packet(self, packet):
        envelope(packet,self.profile_id)
        require(packet['kind'] == 'message')
        return packet['request_id'],digest(packet)

    @io_boundary
    def reserve(self, packet):
        request, fingerprint = self._packet(packet)
        with self._locked():
            rows = self._inventory()
            if request in rows:
                previous = self._record(request,'reserved')
                require(previous['request_digest'] == fingerprint, 'journal_request_conflict')
                raise JournalError('journal_request_not_replayed')
            require(len(rows) < self.maximum_requests, 'journal_capacity_exceeded')
            self._write(request + '.reserved.json',dict(version=1,profile_id=self.profile_id,
                request_id=request,request_digest=fingerprint,stage='reserved'))

    @io_boundary
    def transition(self, packet, response, stage, *, external_id=None):
        request, fingerprint = self._packet(packet)
        envelope(response,self.profile_id)
        require(response['kind'] == 'response' and response['request_id'] == request
            and stage in {'handled','sending','sent'})
        response_fingerprint = digest(response)
        with self._locked():
            rows = self._inventory()
            index = self.STAGES.index(stage)
            require(rows.get(request) == set(self.STAGES[:index]), 'journal_transition_not_replayed')
            previous = self._record(request,self.STAGES[index-1])
            require(previous['request_digest'] == fingerprint and (index == 1
                or previous['response_digest'] == response_fingerprint), 'journal_transition_conflict')
            value = dict(version=1,profile_id=self.profile_id,request_id=request,
                request_digest=fingerprint,stage=stage,response_digest=response_fingerprint)
            if stage == 'sent':
                require(isinstance(external_id,str) and 0 < len(external_id.encode()) <= 1024)
                value['external_id_digest'] = digest(external_id)
            else:require(external_id is None)
            self._write(request + '.' + stage + '.json',value)

    def close(self):
        for name in ('lock_fd','directory_fd'):
            fd = getattr(self,name,None)
            if fd is not None:os.close(fd);setattr(self,name,None)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class DurableNativeTextIngress:
    """Persist admission; retain native ownership of busy/clarification handling.

    No journal or global turn lock is held across the native await: a pending
    clarification must allow its next input to enter. This remains an ingress
    seam, not a replacement for native adapter/FIFO/session admission.
    """
    def __init__(self, runner, journal):
        self.journal = journal
        self.runner = runner
        self._handler = runner._primary_message_handler()

    async def handle(self, packet):
        # Freeze caller-owned structures before awaiting the dispatch lock.
        packet = json.loads(canonical(packet))
        event = native_event(packet,self.journal.profile_id)
        return await self.handle_native(event)

    async def handle_native(self, event):
        require(self.runner.config.multiplex_profiles is True and not self.runner.config.profile_routes
            and not self.runner._profile_adapters, 'fixed_native_runtime_required')
        packet = outbound_packet(event,profile_id=self.journal.profile_id,request_id=event.message_id)
        self.journal.reserve(packet)
        response = await self._handler(event)
        require(response is None or isinstance(response,str), 'unsupported_native_response')
        wire = envelope(dict(version=1,kind='response',profile_id=self.journal.profile_id,
            request_id=packet['request_id'],text=response or '',completed=bool(response)),self.journal.profile_id)
        self.journal.transition(packet,wire,'handled')
        return wire
