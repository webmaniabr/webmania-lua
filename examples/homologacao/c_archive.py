#!/usr/bin/env python3
"""Verifies, and extracts, the C SDK binary archive used by run.sh.

The archive is read once into memory, so what is extracted is exactly what was verified. It is accepted
only when:

* every member is a directory or a regular file (no link, device or other special member), with a
  relative, normalized path (no absolute path, no "." or ".." component, no path twice), and every
  directory is an ancestor of a file;
* c_archive_manifest_sha256 of dependency-lock.json equals the SHA-256 of the sorted lines
  "<path>\\t<sha256 of the file>\\n" of every regular file except the inert documentation in DOCUMENTATION
  (share/webmania/README.md), the only member that may differ;
* the library, the native worker, the API metadata and the wire-name audit (also in that manifest) have the
  c_library_sha256, worker_sha256, api_metadata_sha256 and wire_audit_sha256 of dependency-lock.json.

Usage:
  c_archive.py verify LOCK ARCHIVE         exit 0 when the archive is accepted, 1 otherwise
  c_archive.py extract LOCK ARCHIVE DEST   verifies it, then writes its directories and verified files (not
                                           the documentation in DOCUMENTATION) into the empty directory DEST
  c_archive.py manifest ARCHIVE            prints the manifest digest of a well-formed archive
Nothing else is printed; a refused archive exits 1.
"""
import hashlib
import io
import json
import os
import posixpath
import stat
import sys
import tarfile

DOCUMENTATION = frozenset({'share/webmania/README.md'})
PINNED = {'lib/libwebmania.a': 'c_library_sha256', 'libexec/webmania-native-worker': 'worker_sha256',
          'share/webmania/api-metadata.json': 'api_metadata_sha256',
          'share/webmania/wire-name-audit.json': 'wire_audit_sha256'}
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_CONTENT = 1024 * 1024 * 1024


class Refused(Exception):
    pass


def read(archive_path):
    """Directories and files of the archive: ({path}, {path: (bytes, executable)})."""
    with open(archive_path, 'rb') as stream:
        data = stream.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise Refused('archive too large')
    dirs, files, total = set(), {}, 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive:
            name = member.name
            if name == '.' and member.isdir():
                continue
            if name.startswith('./'):
                name = name[2:]
            parts = name.split('/')
            if not name or name.startswith('/') or posixpath.normpath(name) != name or '..' in parts or '.' in parts:
                raise Refused('member path')
            if name in dirs or name in files:
                raise Refused('member twice')
            if member.isdir():
                dirs.add(name)
            elif member.isreg():
                total += member.size
                if total > MAX_CONTENT:
                    raise Refused('archive content too large')
                stream = archive.extractfile(member)
                if stream is None:  # tarfile has no data for this member: refused, never a traceback
                    raise Refused('member data')
                files[name] = (stream.read(), bool(member.mode & stat.S_IXUSR))
            else:
                raise Refused('member type')
    ancestors = {name.rsplit('/', depth)[0] for name in files for depth in range(1, name.count('/') + 1)}
    if dirs - ancestors or ancestors & set(files):
        raise Refused('directory layout')
    return dirs, files


def manifest(files):
    lines = ''.join(f'{name}\t{hashlib.sha256(files[name][0]).hexdigest()}\n'
                    for name in sorted(files) if name not in DOCUMENTATION)
    return hashlib.sha256(lines.encode('utf-8')).hexdigest()


def verify(lock_path, archive_path):
    with open(lock_path, 'rb') as stream:
        lock = json.load(stream)
    dirs, files = read(archive_path)
    if manifest(files) != lock['c_archive_manifest_sha256']:
        raise Refused('manifest')
    for name, key in PINNED.items():
        if name not in files or hashlib.sha256(files[name][0]).hexdigest() != lock[key]:
            raise Refused(key)
    return dirs, files


def extract(dirs, files, dest):
    if not stat.S_ISDIR(os.lstat(dest).st_mode) or os.listdir(dest):
        raise Refused('destination')
    needed = dirs | {name.rsplit('/', depth)[0] for name in files if name not in DOCUMENTATION
                     for depth in range(1, name.count('/') + 1)}
    for name in sorted(needed, key=lambda path: path.count('/')):
        os.mkdir(os.path.join(dest, name), 0o755)
    for name, (content, executable) in sorted(files.items()):
        if name in DOCUMENTATION:
            continue
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        handle = os.open(os.path.join(dest, name), flags, 0o755 if executable else 0o644)
        with os.fdopen(handle, 'wb') as stream:
            stream.write(content)


def main(argv):
    try:
        if len(argv) == 3 and argv[0] == 'verify':
            verify(argv[1], argv[2])
        elif len(argv) == 4 and argv[0] == 'extract':
            extract(*verify(argv[1], argv[2]), argv[3])
        elif len(argv) == 2 and argv[0] == 'manifest':
            print(manifest(read(argv[1])[1]))
        else:
            return 2
    except Exception:  # fail closed: a malformed lock or archive, or a failed write, refuses the archive
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
