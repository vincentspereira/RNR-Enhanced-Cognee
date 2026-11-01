"""Owner-requested local reorganisation; default is inventory only.

Run inside Ubuntu-Hermes. No mounts, cross-distro access or service changes.
Original file contents are never printed. Existing destinations are preserved.
"""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


def signature(root):
    rows = []
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(parent) / name
            info = path.lstat()
            row = [path.relative_to(root).as_posix(), info.st_mode, info.st_uid, info.st_gid]
            if path.is_symlink():
                row.append(os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                with path.open('rb') as handle:
                    row.append(hashlib.file_digest(handle, 'sha256').hexdigest())
            elif not stat.S_ISDIR(info.st_mode):
                raise RuntimeError('Special file in proposed move; review required')
            rows.append(row)
    return sorted(rows)


def busy(root):
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        references = [process / 'cwd']
        try:
            references.extend((process / 'fd').iterdir())
        except (PermissionError, FileNotFoundError):
            pass
        for reference in references:
            try:
                reference.resolve(strict=True).relative_to(root)
            except (ValueError, PermissionError, FileNotFoundError, OSError):
                continue
            return True
    return False


def move(source, destination, apply, journal):
    row = {'source': str(source), 'destination': str(destination), 'state': 'pending'}
    journal.append(row)
    if source.is_symlink():
        row['state'] = 'already_linked' if source.resolve() == destination.resolve() else 'review_existing_link'
        return
    if not source.exists():
        row['state'] = 'source_absent'
        return
    if destination.exists() or destination.is_symlink():
        row['state'] = 'destination_exists_preserved'
        return
    if not source.is_dir() or busy(source):
        row['state'] = 'active_or_unexpected_source_preserved'
        return
    private_archive = source.name.startswith(('hermes-instruction-reconciliation-', 'hermes-instructions-before-'))
    if private_archive and any((parent / '.git').exists() for parent in (destination.parent, *destination.parents)):
        row['state'] = 'private_archive_requires_destination_outside_git'
        return
    if (source / '.git').is_file():
        row['state'] = 'linked_worktree_requires_git_move'
        return
    if (source / '.git').is_dir():
        result = subprocess.run(['git', '-C', str(source), 'worktree', 'list', '--porcelain'],
                                capture_output=True, check=True, text=True)
        row['git_worktrees'] = result.stdout.count('worktree ')
        status = subprocess.run(['git', '-C', str(source), '-c', 'core.fsmonitor=false',
                                 'status', '--porcelain'], env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'),
                                capture_output=True, check=True, text=True)
        row['git_local_changes_preserved'] = bool(status.stdout)
        if row['git_worktrees'] != 1:
            row['state'] = 'multiple_worktrees_require_git_repair'
            return
    row['state'] = 'ready'
    if not apply:
        return
    before = signature(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if private_archive:
        destination.parent.chmod(0o700)
    if source.stat().st_dev != destination.parent.stat().st_dev:
        raise RuntimeError('Cross-filesystem move refused')
    # Atomic exchange means old references always resolve. The destination
    # placeholder points to itself only until the single exchange operation.
    destination.symlink_to(destination, target_is_directory=True)
    libc = ctypes.CDLL(None, use_errno=True)
    code = libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 2)
    if code:
        # Only the newly-created placeholder is removed on syscall failure.
        destination.unlink()
        raise OSError(ctypes.get_errno(), 'Atomic directory exchange failed')
    row['state'] = 'moved_with_compatibility_link'
    row['entries'] = len(before)
    if before != signature(destination):
        row['state'] = 'verification_failed_originals_retained'
        raise RuntimeError('Post-move verification differs; originals retained')
    row['file_bytes_modes_ownership_and_links_verified'] = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--root', type=Path, default=Path.home())
    args = parser.parse_args()
    home = args.root.resolve()
    if args.apply and (home != Path.home() or os.environ.get('WSL_DISTRO_NAME') != 'Ubuntu-Hermes'):
        raise RuntimeError('Apply is limited to the current Ubuntu-Hermes owner home')
    projects = home / 'Projects'
    if projects.is_symlink():
        raise RuntimeError('Projects must be a local directory')
    pairs = [(home / name, projects / 'StanKorp' / name) for name in (
        'company-formation-research-2026-10-14', 'company-location-comparison-2026-10-16')]
    pairs += [(home / name, projects / '_LocalArchives/Hermes-Agent-Instructions' / name) for name in (
        'hermes-instruction-reconciliation-20261020T142603Z', 'hermes-instructions-before-klww4qpa')]
    pairs += [(home / 'RNR-Multi-Agent-AI-System', projects / 'RNR-Multi-Agent-AI-System'),
              (home / 'projects/RNR-Enhanced-Cognee', projects / 'RNR-Enhanced-Cognee')]
    journal = []
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    state = home / '.local/state/rnr-maintenance' / ('hermes-home-' + stamp)
    if args.apply:
        state.mkdir(parents=True, mode=0o700)
        state.chmod(0o700)
    try:
        for source, destination in pairs:
            move(source, destination, args.apply, journal)
        lower = home / 'projects'
        if args.apply and lower.is_dir() and not lower.is_symlink():
            children = list(lower.iterdir())
            expected = lower / 'RNR-Enhanced-Cognee'
            if len(children) == 1 and children[0] == expected and expected.is_symlink() and expected.resolve() == (projects / expected.name).resolve():
                # Remove only our redundant compatibility link, then replace
                # the now empty lower-case root with one compatibility alias.
                expected.unlink()
                lower.rmdir()
                lower.symlink_to(projects, target_is_directory=True)
    finally:
        if args.apply:
            report = state / 'migration.json'
            report.write_text(json.dumps({'moves': journal, 'existing_files_deleted': False}, indent=2))
            report.chmod(0o600)
    pending = sum(row['state'] not in {'moved_with_compatibility_link', 'already_linked',
                                       'source_absent', 'ready'} for row in journal)
    print(json.dumps({'apply': args.apply, 'moves': journal, 'review_required_count': pending,
                      'private_journal': str(state) if args.apply else None}, ensure_ascii=True))


if __name__ == '__main__':
    main()
