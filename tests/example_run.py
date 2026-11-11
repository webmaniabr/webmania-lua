#!/usr/bin/env python3
"""examples/homologacao/run.sh, offline, with stand-ins for luarocks and lua.

Only the private scratch directory the script creates is ever removed: a
WEBMANIA_EXAMPLE_WORK that contains the checkout, or lies inside it, is refused, and an
existing WEBMANIA_EXAMPLE_WORK keeps everything it already had. A WEBMANIA_EXAMPLE_WORK that
does not exist yet is checked on its resolved path before it is created, so a refused one
leaves no directory behind, and one whose existing part cannot be entered is refused, also when
run.sh is started with bash. The scratch tree is removed even when a lane fails. The example runs from
the caller's directory, so relative payload and ledger paths keep their meaning. The C archive is
checked by the content dependency-lock.json pins (the manifest of every file but the README, the
library, worker, metadata and wire-name audit; plain directories and regular files only), not by its
own digest: one that differs only in its README runs and only its verified files are extracted, and
anything else is refused before anything is created.
"""
import contextlib, hashlib, io, json, os, pathlib, shutil, subprocess, sys, tarfile, tempfile

R = pathlib.Path(__file__).resolve().parents[1]
scratch = pathlib.Path(tempfile.mkdtemp(prefix='webmania-lua-example-run-')).resolve()
lanes = 0


def passed(label):
    global lanes
    lanes += 1
    print('run.sh ' + label + ' PASS', flush=True)


# A synthetic C archive and the stand-ins: luarocks records its call, lua records how it was started.
tools = scratch / 'tools'
log = tools / 'calls.log'
archive = tools / 'c-binary.tar.gz'
digest = None
# The archive members whose own digest dependency-lock.json pins, with the key of each.
PINNED = (('lib/libwebmania.a', 'c_library_sha256'), ('libexec/webmania-native-worker', 'worker_sha256'),
          ('share/webmania/api-metadata.json', 'api_metadata_sha256'), ('share/webmania/wire-name-audit.json', 'wire_audit_sha256'))
README = 'share/webmania/README.md'
FILES = {'include/webmania/webmania.h': b'/* synthetic header */\n', 'lib/cmake/Webmania/WebmaniaConfig.cmake': b'# synthetic config\n',
         'lib/libwebmania.a': b'synthetic library\n', 'libexec/webmania-native-worker': b'synthetic worker\n',
         'share/webmania/api-metadata.json': b'{"schema":1}\n', 'share/webmania/wire-name-audit.json': b'{}\n'}
DIRS = [(name, 'dir', b'') for name in ('.', './include', './include/webmania', './lib', './lib/cmake', './lib/cmake/Webmania',
                                         './libexec', './share', './share/webmania')]


def members(content, readme=b'synthetic readme\n'):
    return DIRS + [('./' + name, 'file', data) for name, data in content.items()] + [('./' + README, 'file', readme)]


def without(name):
    return [m for m in members(FILES) if m[0] != name]


def manifest(files):
    """c_archive_manifest_sha256 of {path: bytes}: SHA-256 of the sorted "path<TAB>sha256" lines of every file but the README."""
    lines = ''.join(f'{n}\t{hashlib.sha256(files[n]).hexdigest()}\n' for n in sorted(files) if n != README)
    return hashlib.sha256(lines.encode()).hexdigest()


def write_archive(path, entries):
    """A gzip tar of (name, kind, data) entries, kind 'dir', 'file' (data: the bytes), 'symlink' or 'hardlink'
    (data: the target) or 'fifo'; returns its sha256."""
    with tarfile.open(path, 'w:gz') as tar:
        for name, kind, data in entries:
            info = tarfile.TarInfo(name)
            info.mode = 0o755 if kind == 'dir' or name.endswith('-worker') else 0o644
            if kind == 'file':
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                continue
            info.type = {'dir': tarfile.DIRTYPE, 'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE, 'fifo': tarfile.FIFOTYPE}[kind]
            if kind in ('symlink', 'hardlink'):
                info.linkname = data
            tar.addfile(info)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_lock():
    """The lock of the synthetic archive: its own digest, its manifest and the digests of the pinned files."""
    return {'c_binary_sha256': digest, 'c_archive_manifest_sha256': manifest(FILES),
            **{key: hashlib.sha256(FILES[name]).hexdigest() for name, key in PINNED}}


def stand_ins():
    global digest
    (tools / 'bin').mkdir(parents=True)
    (tools / 'lua' / 'bin').mkdir(parents=True)
    digest = write_archive(archive, members(FILES))
    (tools / 'bin' / 'luarocks').write_text('#!/bin/sh\nprintf \'luarocks %s\\n\' "$(pwd -P)" >> "$STUB_LOG"\n'
                                            'if [ "${STUB_BUILD_FAIL:-}" = 1 ]; then exit 1; fi\n')
    (tools / 'lua' / 'bin' / 'lua').write_text('#!/bin/sh\nprintf \'lua %s\\n\' "$*" >> "$STUB_LOG"\nprintf \'cwd %s\\n\' "$(pwd -P)" >> "$STUB_LOG"\n'
                                               'printf \'worker %s\\n\' "$WEBMANIA_WORKER_PATH" >> "$STUB_LOG"\n'
                                               '[ -f "$WEBMANIA_WORKER_PATH" ] && echo extracted >> "$STUB_LOG"\n'
                                               'if [ -n "${STUB_PREFIX_LOG:-}" ]; then (cd "${WEBMANIA_WORKER_PATH%/libexec/*}" && '
                                               'find . -type f | LC_ALL=C sort && printf \'modes %s %s\\n\' "$(ls -l libexec/webmania-native-worker | cut -c4)" "$(ls -l lib/libwebmania.a | cut -c4)") > "$STUB_PREFIX_LOG"; fi\n'
                                               'exit "${STUB_STATUS:-0}"\n')
    for stub in (tools / 'bin' / 'luarocks', tools / 'lua' / 'bin' / 'lua'):
        stub.chmod(0o755)


def snapshot(root):
    """Every path below root with the digest of each file."""
    out = {}
    for base, dirs, files in os.walk(root):
        for name in dirs:
            out[os.path.relpath(os.path.join(base, name), root)] = 'dir'
        for name in files:
            p = os.path.join(base, name)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out


def layout():
    """area/src/webmania-lua is a synthetic checkout with a sibling project next to it."""
    area = pathlib.Path(tempfile.mkdtemp(prefix='area-', dir=scratch)).resolve()
    checkout = area / 'src' / 'webmania-lua'
    shutil.copytree(R / 'examples/homologacao', checkout / 'examples/homologacao')
    (checkout / 'examples/homologacao/main.lua').write_text('-- synthetic\n')
    (checkout / 'dependency-lock.json').write_text(json.dumps(content_lock()))
    (area / 'src' / 'other-project').mkdir()
    (area / 'src' / 'other-project' / 'important.txt').write_text('synthetic sibling\n')
    return area, checkout


def run_sh(checkout, env, cwd, shell='sh'):
    log.unlink(missing_ok=True)
    full = {k: v for k, v in os.environ.items() if not k.startswith('WEBMANIA_')}
    full.update({'WEBMANIA_LIVE': '1', 'WEBMANIA_C_ARCHIVE': str(archive), 'WEBMANIA_LUA_DIR': str(tools / 'lua'),
                 'PATH': str(tools / 'bin') + os.pathsep + os.environ.get('PATH', ''), 'STUB_LOG': str(log), **env})
    p = subprocess.run([shell, str(checkout / 'examples/homologacao/run.sh')], capture_output=True, timeout=60, env=full, cwd=cwd)
    calls = log.read_text().splitlines() if log.exists() else []
    return p.returncode, p.stdout.decode(), p.stderr.decode(), calls


def main():
    stand_ins()
    overlap = [{'result': 'blocked', 'reason': 'work directory overlaps the checkout'}]
    # The reported case: the checkout lives in $WORK/src and WORK is its ancestor.
    area, checkout = layout()
    before = snapshot(area)
    for work in (area, area / 'src', checkout, checkout / 'examples'):
        code, out, err, calls = run_sh(checkout, {'WEBMANIA_EXAMPLE_WORK': str(work)}, scratch)
        assert code == 77 and [json.loads(x) for x in out.splitlines()] == overlap and not calls, (work, code, out, err, calls)
        assert snapshot(area) == before, (work, 'run.sh changed a directory it does not own')
    passed('work directory overlapping the checkout')

    # An existing directory keeps its own src and c-prefix; only the private directory is used and removed.
    for label, extra, expected in [('success', {}, 0), ('example exit code', {'STUB_STATUS': '3'}, 3), ('failed build', {'STUB_BUILD_FAIL': '1'}, 1)]:
        area, checkout = layout()
        work = area / 'work'
        for child in ('src', 'c-prefix', 'rocks'):
            (work / child).mkdir(parents=True)
            (work / child / 'keep.txt').write_text('belongs to the user\n')
        caller = area / 'caller'
        caller.mkdir()
        before = snapshot(area)
        code, out, err, calls = run_sh(checkout, {'WEBMANIA_EXAMPLE_WORK': str(work), **extra}, caller)
        assert code == expected, (label, code, out, err, calls)
        assert snapshot(area) == before, (label, 'run.sh changed or left files outside its private directory')
        private = pathlib.Path(calls[0].split(' ', 1)[1]).parent
        assert private.parent == work and private.name.startswith('webmania-lua-example.') and calls[0] == 'luarocks ' + str(private / 'src'), (label, calls)
        if label == 'failed build':
            assert calls == calls[:1], (label, calls)
        else:
            assert calls[1:] == ['lua ' + str(checkout / 'examples/homologacao/main.lua'), 'cwd ' + str(caller),
                                 'worker ' + str(private / 'c-prefix/libexec/webmania-native-worker'), 'extracted'], (label, calls)
        passed('existing work directory, ' + label)

    # Without WEBMANIA_EXAMPLE_WORK the private directory is created in TMPDIR and removed.
    area, checkout = layout()
    tmp = area / 'tmp'
    tmp.mkdir()
    before = snapshot(area)
    code, out, err, calls = run_sh(checkout, {'TMPDIR': str(tmp)}, scratch)
    assert code == 0 and snapshot(area) == before and calls[0].startswith('luarocks ' + str(tmp) + '/webmania-lua-example.'), (code, err, calls)
    passed('default scratch directory')

    # The archive digest changes with any documentation file inside it: an archive that differs from the
    # lock only in its README is accepted, only its verified files are extracted, and the example runs.
    area, checkout = layout()
    tmp = area / 'tmp'
    tmp.mkdir()
    readme = tools / 'readme-only.tar.gz'
    assert write_archive(readme, members(FILES, b'edited readme\n')) != digest
    before = snapshot(area)
    prefix_log = tools / 'prefix.log'
    code, out, err, calls = run_sh(checkout, {'WEBMANIA_C_ARCHIVE': str(readme), 'TMPDIR': str(tmp), 'STUB_PREFIX_LOG': str(prefix_log)}, scratch)
    assert code == 0 and snapshot(area) == before and calls[0].startswith('luarocks ' + str(tmp) + '/webmania-lua-example.'), (code, out, err, calls)
    assert calls[-1] == 'extracted', (code, out, err, calls)
    # The owner execute bit as ls -l prints it, not test -x: root, or a Docker Desktop bind mount, passes -x even for 0644.
    assert prefix_log.read_text().splitlines() == ['./' + name for name in sorted(FILES)] + ['modes x -'], prefix_log.read_text()
    passed('archive differing from the lock only in its README')

    # Anything else is refused before anything is created: a lock without the manifest or the content
    # digests, any file changed, missing or added, an extra directory, and every member that is not a
    # plain directory or regular file.
    refused = {'lock without the content digests': (members(FILES), {'c_binary_sha256': digest}),
               'lock without the manifest': (members(FILES), {k: v for k, v in content_lock().items() if k != 'c_archive_manifest_sha256'})}
    for name in FILES:
        refused['modified ' + name] = (members({**FILES, name: FILES[name] + b'modified\n'}), content_lock())
        refused['missing ' + name] = (members({n: d for n, d in FILES.items() if n != name}), content_lock())
    for label, extra in (('extra file', ('./lib/libextra.a', 'file', b'extra\n')),
                         ('extra documentation file', ('./share/webmania/NOTES.md', 'file', b'notes\n')),
                         ('extra empty directory', ('./etc', 'dir', b'')),
                         ('library twice, modified copy last', ('./lib/libwebmania.a', 'file', b'modified\n')),
                         ('hard link', ('./lib/libcopy.a', 'hardlink', './lib/libwebmania.a')), ('fifo', ('./lib/pipe', 'fifo', b'')),
                         ('absolute path', ('/tmp/webmania-absolute', 'file', b'absolute\n')),
                         ('parent directory component', ('./../webmania-escape', 'file', b'escape\n')),
                         ('dot component', ('./lib/./libwebmania.a', 'file', FILES['lib/libwebmania.a']))):
        refused[label] = (members(FILES) + [extra], content_lock())
    refused['worker as a symbolic link'] = (without('./libexec/webmania-native-worker') + [('./libexec/webmania-native-worker', 'symlink', '/bin/sh')], content_lock())
    refused['README as a symbolic link'] = (without('./' + README) + [('./' + README, 'symlink', '/etc/hostname')], content_lock())
    refused['libexec as a symbolic link'] = (without('./libexec') + [('./libexec', 'symlink', '/usr/libexec')], content_lock())
    for index, (label, (entries, lock)) in enumerate(refused.items()):
        area, checkout = layout()
        (checkout / 'dependency-lock.json').write_text(json.dumps(lock))
        variant = tools / f'refused-{index}.tar.gz'
        write_archive(variant, entries)
        before = snapshot(area)
        code, out, err, calls = run_sh(checkout, {'WEBMANIA_C_ARCHIVE': str(variant), 'WEBMANIA_EXAMPLE_WORK': str(area / 'work')}, scratch)
        assert code == 77 and json.loads(out) == {'result': 'blocked', 'reason': 'C archive differs from the lock'} and not calls, (label, code, out, err, calls)
        assert snapshot(area) == before, (label, 'a refused archive left files behind')
    passed('archive refused: ' + str(len(refused)) + ' cases outside the pinned content')

    # c_archive.py in process: a regular member whose data tarfile cannot return (extractfile gives None) is
    # refused with exit 1, which run.sh turns into the 77 above, and nothing is printed (never a traceback).
    sys.dont_write_bytecode = True  # nothing is written into the checkout
    sys.path.insert(0, str(R / 'examples/homologacao'))
    import c_archive
    lock_file = tools / 'content-lock.json'
    lock_file.write_text(json.dumps(content_lock()))
    assert c_archive.main(['verify', str(lock_file), str(archive)]) == 0, 'c_archive.py refuses the synthetic archive in process'
    original = tarfile.TarFile.extractfile
    tarfile.TarFile.extractfile = lambda self, member: None
    try:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = c_archive.main(['verify', str(lock_file), str(archive)])
    finally:
        tarfile.TarFile.extractfile = original
    assert code == 1 and printed.getvalue() == '', ('member without data', code, printed.getvalue())
    passed('c_archive.py member without data refused')

    # A refused WEBMANIA_EXAMPLE_WORK that does not exist yet is checked on its resolved path
    # before anything is created: no directory is left behind in the checkout.
    area, checkout = layout()
    (area / 'into-checkout').symlink_to(checkout)
    before = snapshot(area)
    for work, reason in [(checkout / 'newdir' / 'deeper', 'work directory overlaps the checkout'),
                         (area / 'into-checkout' / 'newdir', 'work directory overlaps the checkout'),
                         (checkout / 'newdir' / '..' / '..' / 'outside', 'work directory is not a directory path'),
                         (checkout / 'dependency-lock.json' / 'x', 'work directory is not a directory path')]:
        code, out, err, calls = run_sh(checkout, {'WEBMANIA_EXAMPLE_WORK': str(work)}, scratch)
        assert code == 77 and json.loads(out) == {'result': 'blocked', 'reason': reason} and not calls, (work, code, out, err, calls)
        assert snapshot(area) == before, (work, 'a refused work directory left directories behind')
    passed('absent work directory refused without creating it')

    # An absent WEBMANIA_EXAMPLE_WORK outside the checkout is created; only the private directory is removed.
    fresh = area / 'fresh' / 'deeper'
    code, out, err, calls = run_sh(checkout, {'WEBMANIA_EXAMPLE_WORK': str(fresh)}, scratch)
    assert code == 0 and calls[0].startswith('luarocks ' + str(fresh) + '/webmania-lua-example.'), (code, out, err, calls)
    assert snapshot(area) == {**before, 'fresh': 'dir', 'fresh/deeper': 'dir'}, 'run.sh left files outside its private directory'
    passed('absent work directory created')

    # An existing part that cannot be entered is refused before anything is created, also under bash,
    # where errexit does not reach a failed cd inside resolve.
    area, checkout = layout()
    locked = area / 'locked'
    locked.mkdir()
    locked.chmod(0o600)
    try:
        try:
            os.stat(locked / 'probe')
            enforced = False
        except PermissionError:
            enforced = True
        except FileNotFoundError:
            enforced = False
        if not enforced:
            print('run.sh work directory that cannot be entered SKIP (permission bits not enforced for this user)', flush=True)
        else:
            before = snapshot(area)
            for shell in [s for s in ('sh', 'bash') if shutil.which(s)]:
                for work in (locked, locked / 'newdir'):
                    code, out, err, calls = run_sh(checkout, {'WEBMANIA_EXAMPLE_WORK': str(work)}, scratch, shell)
                    assert code == 77 and json.loads(out) == {'result': 'blocked', 'reason': 'work directory is not a directory path'} and not calls, (shell, work, code, out, err, calls)
                    assert snapshot(area) == before, (shell, work, 'a refused work directory left directories behind')
            passed('work directory that cannot be entered refused')
    finally:
        locked.chmod(0o700)


try:
    main()
finally:
    # Removed also when a lane fails.
    shutil.rmtree(scratch, ignore_errors=True)
print(str(lanes) + ' run.sh lanes PASS')
