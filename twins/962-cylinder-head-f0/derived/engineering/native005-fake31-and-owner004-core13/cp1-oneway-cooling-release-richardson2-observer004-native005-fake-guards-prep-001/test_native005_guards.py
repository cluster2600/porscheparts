"""HELD/UNRUN. Exact native005 definitions under explicit in-memory providers."""
import ast
import builtins
import errno
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace
import unittest


SOURCE_ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-prep-005')
SOURCE_PINS = {
    'owner': ('run_root_once.py', '34826ad993e4d874455adb40777df545f76cf611a6f23ae021a49302dc0dd649', 61563),
    'caller': ('run_native_capture.py', 'a04276da60fe09d9af26d32c7661fb421105b7c93724d43c728025dd1fd51aa5', 45810),
    'wrapper': ('stopped_exec_wrapper.py', 'a81328f9e07bded2120d8f908f8831bdafead07132ae09a1af4ccfcc4bf50e17', 5295),
}
TARGET_BUILTINS = ('__build_class__', 'super', 'BaseException', 'Exception', 'ValueError',
    'OSError', 'ChildProcessError', 'BlockingIOError', 'ProcessLookupError', 'RuntimeError', 'type', 'str',
    'int', 'bool', 'dict', 'list', 'set', 'tuple', 'bytes', 'bytearray', 'len',
    'all', 'any', 'sum', 'min', 'max', 'sorted', 'hasattr', 'getattr', 'isinstance',
    'enumerate', 'range', 'zip', 'repr', 'locals', 'print')
T0 = 1_000_000_000
LEADER, NATIVE = 5001, 6001
UNITS = {}


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()


class ExecHandoff(BaseException):
    pass


class Clock:
    def __init__(self):
        self.now = 2_000_000_000
    def monotonic_ns(self):
        self.now += 1000
        return self.now
    def sleep(self, seconds):
        if seconds < 0:
            raise AssertionError('Negative fake sleep')
        self.now += max(1, int(seconds * 1_000_000_000))


class MemoryText:
    def __init__(self, world, name):
        self.world, self.name, self.parts = world, name, []
    def write(self, text):
        if type(text) is not str:
            raise AssertionError('Text stream requires str')
        self.parts.append(text)
        self.world.trace.append(('text-write', self.name, text))
        return len(text)
    def flush(self):
        self.world.trace.append(('text-flush', self.name))


class MemoryHandle:
    def __init__(self, world, key, mode):
        self.world, self.key, self.mode, self.offset = world, key, mode, 0
        self.closed = False
    def read(self, count=-1):
        data = bytes(self.world.files[self.key])
        value = data[self.offset:] if count < 0 else data[self.offset:self.offset+count]
        self.offset += len(value)
        return value
    def write(self, value):
        if type(value) is not bytes or self.mode != 'xb':
            raise AssertionError('Unexpected memory write')
        self.world.files[self.key].extend(value)
        self.world.trace.append(('file-write', self.key, len(value)))
        return len(value)
    def flush(self):
        self.world.trace.append(('file-flush', self.key))
    def close(self):
        if not self.closed:
            self.closed = True
            self.world.trace.append(('file-close', self.key))
            if self.mode == 'xb' and self.key == '/mem/D/closed-result.json':
                self.world.postwrite = True
                self.world.closed_bytes = bytes(self.world.files[self.key])
                if self.world.mode == 'postwrite_stop':
                    self.world.ns['_STOP_REQUESTS'].append({'synthetic': 'postwrite stop'})


class MemoryPath:
    """No __fspath__: it cannot silently fall through to a real filesystem API."""
    def __init__(self, world, value):
        self.world = world
        self.key = value.key if isinstance(value, MemoryPath) else str(PurePosixPath(str(value)))
    def __str__(self):
        return self.key
    def __repr__(self):
        return 'MemoryPath(' + repr(self.key) + ')'
    def __hash__(self):
        return hash(self.key)
    def __eq__(self, other):
        return isinstance(other, MemoryPath) and self.world is other.world and self.key == other.key
    def __lt__(self, other):
        return self.key < other.key
    def __truediv__(self, value):
        return MemoryPath(self.world, str(PurePosixPath(self.key) / str(value)))
    @property
    def name(self):
        return PurePosixPath(self.key).name
    @property
    def parent(self):
        return MemoryPath(self.world, str(PurePosixPath(self.key).parent))
    @property
    def parts(self):
        return PurePosixPath(self.key).parts
    def is_absolute(self):
        return PurePosixPath(self.key).is_absolute()
    def is_relative_to(self, parent):
        return PurePosixPath(self.key).is_relative_to(PurePosixPath(str(parent)))
    def relative_to(self, parent):
        return MemoryPath(self.world, str(PurePosixPath(self.key).relative_to(PurePosixPath(str(parent)))))
    def resolve(self, strict=False):
        if strict and not self.exists():
            raise FileNotFoundError(self.key)
        return self
    def is_symlink(self):
        return False
    def is_file(self):
        return self.key in self.world.files
    def is_dir(self):
        return self.key in self.world.dirs
    def exists(self):
        return self.is_file() or self.is_dir()
    def stat(self):
        if not self.is_file():
            raise FileNotFoundError(self.key)
        return SimpleNamespace(st_size=self.world.virtual_sizes.get(self.key, len(self.world.files[self.key])))
    def read_bytes(self):
        self.world.trace.append(('file-read', self.key))
        return bytes(self.world.files[self.key])
    def open(self, mode):
        if mode == 'xb':
            if self.exists():
                raise FileExistsError(self.key)
            self.world.put(self.key, b'')
        elif mode != 'rb' or not self.is_file():
            raise AssertionError('Unexpected fake open: ' + self.key + '/' + mode)
        self.world.trace.append(('file-open', self.key, mode))
        return MemoryHandle(self.world, self.key, mode)
    def mkdir(self, parents=False, exist_ok=False):
        if self.exists() and not exist_ok:
            raise FileExistsError(self.key)
        self.world.directory(self.key)
    def iterdir(self):
        prefix = self.key.rstrip('/') + '/'
        keys = set(self.world.files) | self.world.dirs
        return iter(sorted(MemoryPath(self.world, key) for key in keys
            if key.startswith(prefix) and '/' not in key[len(prefix):] and key != self.key))
    def rglob(self, pattern):
        if pattern != '*':
            raise AssertionError('Only the literal fake walk is supported')
        prefix = self.key.rstrip('/') + '/'
        return iter(sorted(MemoryPath(self.world, key) for key in set(self.world.files) | self.world.dirs
            if key.startswith(prefix)))


class Pipe:
    def __init__(self, world, fd):
        self.world, self.fd = world, fd
    def fileno(self):
        return self.fd
    def close(self):
        self.world.trace.append(('pipe-close', self.fd))


class World:
    """All target API boundaries are fake; only pinned source loading is real."""
    def __init__(self, role='owner', mode='normal'):
        self.role, self.mode = role, mode
        self.clock, self.trace = Clock(), []
        self.files, self.dirs, self.virtual_sizes = {}, set(), {}
        self.handles, self.fd_chunks, self.query_number = {}, {}, 0
        self.postwrite, self.closed_bytes, self.ns = False, None, None
        self.wait_counts = {}
        self.sig = SimpleNamespace(SIGTERM=15, SIGINT=2, SIGCHLD=20, SIG_DFL=0,
            SIGSTOP=17, SIGCONT=19, SIGKILL=9, SIG_IGN=1)
        self.sig.Signals = lambda number: SimpleNamespace(name='FAKE_SIGNAL_' + str(number))
        self.sig.getsignal = lambda number: 1 if self.mode == 'nondefault_chld' and number == 20 else 0
        self.sig.signal = self.signal
        self.stdout, self.stderr = MemoryText(self, 'stdout'), MemoryText(self, 'stderr')
        self.setup()

    def path(self, value):
        return MemoryPath(self, value)
    def directory(self, value):
        p = PurePosixPath(str(value))
        self.dirs.add(str(p))
        self.dirs.update(str(parent) for parent in p.parents)
    def put(self, name, value):
        self.directory(str(PurePosixPath(str(name)).parent))
        self.files[str(name)] = bytearray(value)
    def descriptor(self, path):
        p = self.path(path)
        value = bytes(self.files[p.key])
        return {'path': str(p.relative_to('/mem')), 'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
    def signal(self, number, handler):
        self.trace.append(('handler', number))
        if number == self.sig.SIGCHLD:
            raise AssertionError('SIGCHLD reset/restore is forbidden')
        if number not in (self.sig.SIGTERM, self.sig.SIGINT):
            raise AssertionError('Unexpected fake handler')
        return 0
    def unexpected(self, name):
        def fail(*args, **kwargs):
            self.trace.append(('unexpected', name))
            raise AssertionError('Unexpected real-provider seam: ' + name)
        return fail

    def setup(self):
        for name in ('run_root_once.py', 'run_native_capture.py', 'stopped_exec_wrapper.py', 'METHOD.md', 'index.json', 'bindings.json'):
            self.put('/mem/S/' + name, ('FAKE SOURCE ' + name).encode())
        self.put('/mem/python', b'FAKE IDENTITY PLACEHOLDER, NEVER INSTALLED CODE')
        self.put('/mem/staging.json', b'FAKE staging metadata')
        self.put('/mem/history.json', encoded({'outputs': {}}))
        self.put('/mem/physics.json', b'FAKE physics identity only')
        self.put('/mem/card.json', b'FAKE material identity only')
        self.put('/mem/api.json', b'FAKE source-evidence identity only')
        self.put('/mem/transfer/transfer-manifest.json', b'FAKE manifest')
        staged = {}
        for name in ('old-end.grid', 'born-end.grid', 'born-begin80.grid', 'transfer-manifest.json'):
            self.put('/mem/O/' + name, b'FAKE STAGED TEXT')
            staged[name] = self.descriptor('/mem/O/' + name)
        py = dict(path='/mem/python', resolved_path='/mem/python', sha256='a'*64, bytes=1)
        resources = dict(wall_seconds=100, sampled_RSS_stop_bytes=2147483648, sampled_output_stop_bytes=536870912)
        roles = ('actual', 'caller', 'root_controller', 'wrapper', 'staging_receipt')
        self.actual = dict(schema='962-observer004-native-measurement-actual/v1',
            authority_at_freeze='HELD_ROOT_ADMISSION_REQUIRED', native_execution_authorized=False,
            resources=resources, owned_phase_seconds=dict(normal=95, TERM=105, KILL_reap=110, closure=115),
            future_root_direct_roles=list(roles), source=self.descriptor('/mem/S/run_native_capture.py'),
            outer_python={'path': '/mem/python'}, outer_environment={'FAKE_THREADS': '1'},
            expected_host_records={}, expected_provider_paths={}, outer_python_observed_metadata=py,
            runtime_sha256s={}, runtime_symlinks={}, solver_profile={'FAKE': 'unqualified'}, input_sha256={},
            staged_inputs=staged, historical_native_closed={'path': 'history.json'}, inclusive_external_records={})
        self.put('/mem/P/actual-contract.json', encoded(self.actual))
        parent = dict(self.actual)
        self.parent_key = '/mem/E/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-003/actual-contract.json'
        self.put(self.parent_key, encoded(parent))
        self.auth = dict(schema='962-observer004-owned-native-root-admission/v2',
            resources=resources, outer_wall_seconds=115, root_TERM_grace_seconds=10,
            owned_phase_seconds=self.actual['owned_phase_seconds'],
            argv_prefix=['/mem/python', '-B', '-I', '-S', '/mem/S/stopped_exec_wrapper.py'],
            direct_roles={'actual': self.descriptor('/mem/P/actual-contract.json'),
                'caller': self.descriptor('/mem/S/run_native_capture.py'),
                'root_controller': self.descriptor('/mem/S/run_root_once.py'),
                'wrapper': self.descriptor('/mem/S/stopped_exec_wrapper.py'),
                'staging_receipt': self.descriptor('/mem/staging.json')})
        for key in ('native_once_authorized', 'independent_exact_child_complete', 'root_source_review_complete', 'freshness_and_staging_complete'):
            self.auth[key] = True
        for key in ('automatic_retry', 'assessment_execution_authorized', 'solver_change_authorized', 'head_execution_authorized',
                    'engineering_accepted', 'physics_qualified', 'material_qualified', 'process_calibrated', 'manufacturing_authorized'):
            self.auth[key] = False
        self.put('/mem/D/authorization.json', encoded(self.auth))
        self.admission_sha = self.descriptor('/mem/D/authorization.json')['sha256']
        self.caller_contract = dict(self.actual)
        preparation = {str(self.path('/mem/S/' + name).relative_to('/mem')): self.descriptor('/mem/S/' + name)
            for name in ('run_root_once.py', 'run_native_capture.py', 'stopped_exec_wrapper.py', 'METHOD.md', 'index.json', 'bindings.json')}
        self.caller_contract.update(argv=['FAKE-native'], environment={'FAKE_THREADS': '1'}, source_preparation_records=preparation,
            input_sha256={name: pin['sha256'] for name, pin in preparation.items()})

    def hello(self):
        return dict(schema='962-observer004-owned-native-wrapper-hello/v1', status='ABOUT_TO_STOP',
            owner_start_ns=str(T0), root_admission_sha256=self.admission_sha,
            PID=LEADER, PGID=LEADER, SID=LEADER, wrapper_source=self.auth['direct_roles']['wrapper'],
            caller_source=self.actual['source'], caller_actual=self.auth['direct_roles']['actual'])

    def materialize_caller_evidence(self):
        query = dict(role='NATIVE_IDENTITY', constructor_attempted=True, PID=7000, error=None, stop_actions=[],
            stdout_complete=True, stderr_complete=True, partial_capture=False,
            exit=dict(status='reaped', raw_returncode=0))
        clock = dict(owner_start_ns=str(T0), caller_entry_ns=str(T0+10000), normal_until_ns=str(T0+95_000_000_000),
            native_spawn_ns=str(T0+20000), receipt_encoding_started_ns=str(T0+30000))
        if self.mode == 'bad_deadline':
            clock['normal_until_ns'] = str(T0+95_000_000_000-1)
        if self.mode == 'future_observed':
            clock['native_spawn_ns'] = str(self.clock.now+1_000_000_000)
        receipt = dict(schema='962-observer004-owned-native-caller-receipt/v2', status='COMPLETE_CANDIDATE', prefinal_candidate=True,
            root_admission_sha256=self.admission_sha, actual=self.auth['direct_roles']['actual'], source=self.actual['source'], clock=clock,
            caller_identity=dict(PID=LEADER, PGID=LEADER, SID=LEADER),
            native=dict(spawn_attempted=True, PID=NATIVE, start_new_session=False, preexec_fn_used=False,
                identity_observation=dict(PID=NATIVE, PPID=LEADER, PGID=LEADER, query_record=query),
                exit=dict(status='reaped', raw_returncode=0, wait_status=0)), query_records=[query],
            native_signal_actions=[], group_absence_scope='OUTER_ONLY_NOT_OBSERVED_BY_CALLER',
            primary_refusal=None, secondary_errors=[], stop_requests=[], automatic_retry=False,
            science_or_physical_qualification=False, opaque_native_containment_accepted=False,
            inputs_and_outputs=dict(inputs_unchanged=True, binary_and_runtime_unchanged=True,
                complete_stream_map_or_field_association_proved=False))
        if self.mode == 'bad_schema':
            receipt['schema'] = 'FAKE-invalid-schema'
        self.put('/mem/O/native-execution.json', b'{' if self.mode=='partial_receipt' else encoded(receipt))
        self.put('/mem/O/native.log', b'FAKE loaded trace, no native body')
        terminal = dict(schema='962-observer004-owned-native-caller-terminal/v1', owner_start_ns=str(T0),
            caller_PID=LEADER, root_admission_sha256=self.admission_sha,
            caller_receipt=self.descriptor('/mem/O/native-execution.json'),
            caller_receipt_saved_ns=str(T0+40000), caller_receipt_hashed_ns=str(T0+50000), prefinal_candidate=True)
        if self.mode == 'bad_echo':
            terminal['owner_start_ns'] = str(T0+1)
        if self.mode == 'missing_receipt':
            del self.files['/mem/O/native-execution.json']
        data = encoded(self.hello()) + encoded(terminal)
        if self.mode == 'extra_stdout':
            data += b'{}\n'
        self.put('/mem/D/adapter.stdout.log', data)

    def make_namespace(self):
        world = self
        class FakeBasePopen:
            def __init__(handle, argv, **kwargs):
                world.construct(handle, argv, kwargs)
            def __del__(handle):
                world.unexpected('base-Popen-destructor')()
            poll = wait = communicate = send_signal = terminate = kill = __enter__ = __exit__ = lambda *a, **k: world.unexpected('competing-Popen-method')()
        fake_os = SimpleNamespace(WNOHANG=1, WUNTRACED=2, waitpid=self.waitpid,
            WIFEXITED=lambda status: status in (0, 256), WIFSIGNALED=lambda status: False,
            WIFSTOPPED=lambda status: status == 4479, WSTOPSIG=lambda status: self.sig.SIGSTOP,
            waitstatus_to_exitcode=lambda status: status // 256,
            getpid=lambda: LEADER, getpgrp=lambda: LEADER,
            getpgid=lambda pid: LEADER+1 if self.mode == 'bad_pgid' else LEADER,
            getsid=lambda pid: LEADER, kill=self.kill, killpg=self.killpg,
            read=self.read, set_blocking=lambda fd, value: self.trace.append(('set-blocking', fd, value)),
            path=SimpleNamespace(realpath=lambda value: value), execv=self.execv,
            readlink=self.unexpected('readlink'))
        fake_select = SimpleNamespace(kqueue=self.queue, kevent=lambda *a, **k: SimpleNamespace(), select=self.select,
            KQ_FILTER_PROC=401, KQ_NOTE_EXIT=16, KQ_EV_ADD=1, KQ_EV_ENABLE=2, KQ_EV_ONESHOT=4, KQ_EV_ERROR=8)
        ns = dict(__name__='held_native005_' + self.role,
            __builtins__={name: getattr(builtins, name) for name in TARGET_BUILTINS},
            __file__='/mem/S/' + SOURCE_PINS[self.role][0],
            time=SimpleNamespace(monotonic_ns=self.clock.monotonic_ns, sleep=self.clock.sleep),
            errno=errno, hashlib=hashlib, json=json, math=math, re=re, os=fake_os, signal=self.sig,
            select=fake_select, subprocess=SimpleNamespace(Popen=FakeBasePopen, DEVNULL=-1, PIPE=-2, STDOUT=-3),
            traceback=SimpleNamespace(format_exc=lambda: 'FAKE_TRACEBACK: current injected/source error'),
            Path=self.path, sys=SimpleNamespace(argv=['FAKE-owner', self.admission_sha], executable='/mem/python',
                version_info=(3,12,11), flags=SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1, optimize=0),
                modules={}, stdout=self.stdout, stderr=self.stderr),
            START_NS=T0, ENTRY_NS=T0, _OWNER_START_NS=T0, _UNTIL_NS=T0+95_000_000_000,
            _PHASE='normal95', _NORMAL=True, _RETAINED=[], _QUERY_RECORDS=[], _STOP_REQUESTS=[], _ERRORS=[],
            _EXTERNAL={}, _BASELINE={}, QUERY_ROLE='GROUP_ROWS' if self.role=='owner' else 'NATIVE_IDENTITY')
        for name, key in dict(ROOT='/mem', R='/mem', E='/mem/E', S='/mem/S', SOURCE_PREP='/mem/S',
                P='/mem/P', ROOT_EXECUTION='/mem/D', OUTPUT='/mem/O', D='/mem/D', PREFIX='/mem/prefix',
                CASE='/mem/case', PREP='/mem/case', TRANSFER='/mem/transfer', PHYSICS='/mem/physics.json',
                CARD='/mem/card.json', PRIMARY_API='/mem/api.json', HELD='/mem/held.json', EXECUTABLE='/mem/FAKE-native').items():
            ns[name] = self.path(key)
        ns.update(QUERY_ROOT=ns['ROOT_EXECUTION'] if self.role=='owner' else ns['OUTPUT'],
            PY='/mem/python', RESOLVED='/mem/python', FEATURES=(), TRANSFER_FILES=(),
            argparse=SimpleNamespace(ArgumentParser=self.unexpected('argument-parser')),
            shutil=SimpleNamespace(copyfile=self.copyfile))
        # Future invocation only: the selected exact definitions are not rewritten.
        module = ast.Module(body=[node for node in UNITS[self.role].body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))], type_ignores=[])
        builtins.exec(builtins.compile(module, str(SOURCE_ROOT/SOURCE_PINS[self.role][0]), 'exec'), ns)
        self.ns = ns
        if self.role == 'owner':
            actual_sha = ns['sha']
            ns['sha'] = lambda path: '85a9195ed1a217eef6bad44518390f1b2dfdb879c9cdfc072b6e1465461a5198' if str(path)==self.parent_key else actual_sha(path)
            ns['input_map'] = self.input_observation
            ns['runtime_map'] = lambda c: {'files': {}, 'links': {}}
            ns['check'] = lambda rows: {'count': 0, 'observed_sha256': 'a'*64, 'changed': {}}
            ns['provider_links'] = lambda paths: dict(paths)
            ns['python_record'] = lambda c: dict(self.actual['outer_python_observed_metadata'])
            plugin = str(ns['E']/'cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-004/build-001/libcoupon_end181_observer-opt.dylib')
            ns['loaded_trace'] = lambda *a: {'rows': [{'resolved': plugin}]}
        elif self.role == 'caller':
            ns['checked_contract'] = lambda *a: (self.caller_contract, ns['OUTPUT'], self.auth, {})
            ns['runtime_unchanged'] = lambda c: True
            actual_identity = ns['native_identity']
            def identity_with_boundary_injection(*args):
                value = actual_identity(*args)
                self.trace.append(('identity-return',))
                if self.mode == 'identity_stop':
                    ns['_STOP_REQUESTS'].append({'synthetic': 'after actual identity return'})
                if self.mode == 'identity_equal':
                    self.clock.now = T0+95_000_000_000
                return value
            ns['native_identity'] = identity_with_boundary_injection
        else:
            ns['sys'].argv = ['FAKE-wrapper', self.admission_sha, '--owner-start-ns', str(T0)]
        return ns

    def input_observation(self, actual):
        self.trace.append(('identity-inputs', self.postwrite))
        if self.postwrite:
            if self.mode == 'postwrite_mismatch':
                return {'synthetic_mutation': True}
            if self.mode == 'postwrite_error':
                raise OSError('Injected postwrite identity read error')
            if self.mode == 'postwrite_late':
                self.clock.now = T0+115_000_000_000
        return {}

    def copyfile(self, source, destination):
        self.trace.append(('copy', str(source), str(destination)))
        self.put(str(destination), bytes(self.files[str(source)]))

    def construct(self, handle, argv, kwargs):
        role = 'query' if argv[0] == '/bin/ps' else 'native' if argv[0] == 'FAKE-native' else 'leader'
        self.trace.append(('construct', role, tuple(argv), dict(kwargs)))
        if (self.mode == 'owner_constructor_unknown' and role=='leader') or (self.mode=='caller_constructor_unknown' and role=='native'):
            raise OSError('Injected constructor without reliable returned PID')
        handle.pid = LEADER if role=='leader' else NATIVE if role=='native' else 7000+self.query_number
        handle.returncode, handle.role, handle.killed = None, role, False
        self.handles[handle.pid] = handle
        if role == 'leader':
            if kwargs.get('start_new_session') is not True:
                raise AssertionError('Leader session configuration changed')
            self.put('/mem/D/adapter.stdout.log', encoded(self.hello()))
        elif role == 'native':
            if kwargs.get('start_new_session') is not False or 'preexec_fn' in kwargs:
                raise AssertionError('Native inheritance configuration changed')
        else:
            self.query_number += 1
            handle.number = self.query_number
            group_form = ['/bin/ps', '-axo', 'pid=,pgid=,rss=,stat=']
            identity_form = ['/bin/ps', '-o', 'pid=,ppid=,pgid=', '-p', str(NATIVE)]
            if argv not in (group_form, identity_form) or kwargs.get('start_new_session') is not False:
                raise AssertionError('Unexpected query command or detachment')
            if argv == group_form:
                payload = f'{LEADER} {LEADER} 0 Z\n'.encode()
                if self.mode == 'query_malformed' and handle.number == 1:
                    payload = f'{LEADER} {LEADER} bad Z\n'.encode()
                if self.mode == 'cont_nonanchor':
                    payload += f'{NATIVE} {LEADER} 1 Z\n'.encode()
            else:
                parent = LEADER+1 if self.mode=='wrong_identity' else LEADER
                observed_pid = NATIVE+1 if self.mode=='wrong_native_pid' else NATIVE
                group = LEADER+1 if self.mode=='wrong_native_pgid' else LEADER
                payload = f'{observed_pid} {parent} {group}\n'.encode()
                if self.mode=='identity_missing':
                    payload = b''
            fd = 100+handle.number*2
            handle.stdout, handle.stderr = Pipe(self, fd), Pipe(self, fd+1)
            half = max(1, len(payload)//2)
            self.fd_chunks[fd] = [payload[:half], payload[half:], b'']
            self.fd_chunks[fd+1] = [b'FAKE', b' stderr', b'']
        if (role=='leader' and self.mode=='owner_constructor_late') or (role=='native' and self.mode=='caller_constructor_late'):
            self.clock.now = T0+95_000_000_000

    def waitpid(self, pid, flags):
        h = self.handles[pid]
        n = self.wait_counts.get(pid, 0)+1
        self.wait_counts[pid] = n
        self.trace.append(('waitpid', pid, flags, len(self.ns['_ERRORS']), len(self.ns['_STOP_REQUESTS']), self.clock.now))
        if h.role=='leader' and flags&2:
            if self.mode=='handshake_echild':
                raise ChildProcessError(errno.ECHILD, 'Injected stopped wait loss')
            if self.mode=='early_terminal':
                return pid, 256
            return pid, 4479
        if h.role=='leader' and self.mode=='terminal_echild':
            raise ChildProcessError(errno.ECHILD, 'Injected terminal wait loss')
        if h.role=='native' and self.mode=='native_echild':
            raise ChildProcessError(errno.ECHILD, 'Injected native wait loss')
        if h.role=='query' and self.mode=='query_echild' and h.number==1:
            raise ChildProcessError(errno.ECHILD, 'Injected query wait loss')
        if h.role=='query' and self.mode=='query_timeout' and h.number==1 and not h.killed:
            return 0, 0
        if h.role=='leader' and self.mode=='leader_unreaped_late':
            self.clock.now = T0+110_000_000_000
            return 0, 0
        if h.role=='native':
            for name in ('rich2-END181-dof-map.json', 'physical-X.petsc', 'physical-F.petsc', 'physical-Y.petsc'):
                self.put('/mem/O/'+name, b'FAKE PRESENCE ONLY')
        return pid, 0

    def kill(self, pid, number):
        self.trace.append(('kill', pid, number, self.clock.now))
        if self.role=='wrapper' and pid==LEADER and number==self.sig.SIGSTOP:
            return
        handle = self.handles[pid]
        if handle.role=='leader' and number==self.sig.SIGCONT:
            if self.mode.startswith('cont_'):
                raise PermissionError(errno.EPERM, 'Injected uncertain CONT return')
            self.materialize_caller_evidence()
            return
        if number==self.sig.SIGKILL and handle.role in ('leader', 'query'):
            handle.killed = True
            return
        self.unexpected('numeric kill')()

    def killpg(self, pid, number):
        self.trace.append(('killpg', pid, number, self.clock.now))
        if pid != LEADER:
            self.unexpected('other group')()
        if number == 0:
            if self.mode=='absence_present':
                return
            if self.mode=='absence_eperm':
                raise PermissionError(errno.EPERM, 'Injected unknown absence')
            raise ProcessLookupError(errno.ESRCH, 'Synthetic absent group')
        if number not in (self.sig.SIGTERM, self.sig.SIGKILL):
            self.unexpected('group signal')()
        if number==self.sig.SIGTERM and self.mode=='cont_term_eperm':
            raise PermissionError(errno.EPERM, 'Injected TERM failure')
        if number==self.sig.SIGTERM and self.mode=='cont_term_esrch':
            raise ProcessLookupError(errno.ESRCH, 'Injected TERM ESRCH, not reap')

    def queue(self):
        world = self
        class Queue:
            def control(self, changes, maximum, timeout):
                world.trace.append(('kqueue', changes is not None))
                if changes is not None:
                    return [SimpleNamespace(ident=LEADER, filter=401, flags=8, fflags=16, data=0, udata=0)] if world.mode=='registration_error' else []
                return [SimpleNamespace(ident=LEADER, filter=401, flags=0, fflags=16, data=0, udata=0)]
            def close(self):
                world.trace.append(('kqueue-close',))
        return Queue()

    def select(self, read, write, error, timeout):
        self.trace.append(('select', tuple(read), timeout))
        if self.mode in ('query_timeout', 'query_partial') and self.query_number==1:
            if self.mode=='query_timeout' or all(not self.fd_chunks[fd] for fd in read):
                self.clock.now += 2_000_000_000
                return [], [], []
        return list(read), [], []

    def read(self, fd, count):
        self.trace.append(('read-fd', fd))
        values = self.fd_chunks[fd]
        if self.mode=='query_partial' and self.query_number==1 and fd%2==1 and values==[b'']:
            values.pop()
            raise BlockingIOError('Injected missing stderr EOF')
        if not values:
            raise BlockingIOError('No additional fake bytes')
        return values.pop(0)

    def execv(self, executable, argv):
        self.trace.append(('execv', executable, tuple(argv)))
        raise ExecHandoff('Synthetic same-PID handoff; no process execution')


class Native005Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Exactly three explicit real source reads per future fixture invocation.
        for role, (name, digest, size) in SOURCE_PINS.items():
            raw = (SOURCE_ROOT/name).read_bytes()
            if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=digest:
                raise AssertionError('Frozen native005 source changed: '+role)
            UNITS[role] = ast.parse(raw.decode('utf-8'), filename=str(SOURCE_ROOT/name))

    def setUp(self):
        self._worlds = []

    def tearDown(self):
        for world in self._worlds:
            self.assertFalse(any(row[0]=='unexpected' for row in world.trace))

    def world(self, role='owner', mode='normal'):
        w = World(role, mode)
        self._worlds.append(w)
        w.make_namespace()
        return w

    def owner(self, mode='normal'):
        w = self.world('owner', mode)
        rc = w.ns['main']()
        self.assertFalse(any(row[0]=='unexpected' for row in w.trace))
        return w, rc, json.loads(bytes(w.files['/mem/D/closed-result.json'])) if '/mem/D/closed-result.json' in w.files else None

    def caller(self, mode='normal'):
        w = self.world('caller', mode)
        rc = w.ns['run']('coupon', '/mem/P/actual-contract.json', w.descriptor('/mem/P/actual-contract.json')['sha256'], w.admission_sha, str(T0))
        self.assertFalse(any(row[0]=='unexpected' for row in w.trace))
        return w, rc, json.loads(bytes(w.files['/mem/O/native-execution.json'])) if '/mem/O/native-execution.json' in w.files else None

    def test_01_owner_normal_real_main_and_future_deadline(self):
        w, rc, r = self.owner()
        self.assertEqual(rc, 0)
        self.assertEqual(r['status'], 'COMPLETE_CANDIDATE')
        self.assertTrue(r['identities_unchanged'])
        self.assertEqual(r['native_receipt_evidence_status']['status'], 'observed')
        self.assertGreater(int(r['native_receipt_and_terminal']['receipt']['clock']['normal_until_ns']), w.clock.now)
        self.assertEqual(r['caller_exit']['reap']['raw_returncode'], 0)
        self.assertEqual(r['final_group_absence']['status'], 'ESRCH')
        self.assertEqual(r['errors_stops_signals']['all_errors'], [])
        self.assertEqual(r['resources']['valid_count'], 1)
        self.assertEqual(r['resources']['peak'], 0)
        self.assertEqual([x for x in w.trace if x[0]=='identity-inputs'], [('identity-inputs', False), ('identity-inputs', False), ('identity-inputs', True)])
        self.assertEqual(sum(x[:3]==('file-open', '/mem/D/closed-result.json', 'xb') for x in w.trace), 1)

    def test_02_owner_already_default_precondition(self):
        w, rc, r = self.owner('nondefault_chld')
        self.assertEqual(rc, 2)
        self.assertIsNone(r)
        self.assertFalse(any(x[0]=='construct' for x in w.trace))
        self.assertNotIn(('handler', 20), w.trace)

    def test_03_caller_normal_identity_running_receipt_return(self):
        w, rc, r = self.caller()
        self.assertEqual(rc, 0)
        self.assertEqual(r['status'], 'COMPLETE_CANDIDATE')
        self.assertEqual(r['native']['exit']['status'], 'reaped')
        self.assertEqual(r['native']['exit']['raw_returncode'], 0)
        self.assertEqual(r['native_signal_actions'], [])
        self.assertEqual(r['group_absence_scope'], 'OUTER_ONLY_NOT_OBSERVED_BY_CALLER')
        identity = next(i for i,x in enumerate(w.trace) if x[0]=='identity-return')
        native_wait = next(i for i,x in enumerate(w.trace) if x[:2]==('waitpid', NATIVE))
        self.assertLess(identity, native_wait)
        self.assertEqual(len([x for x in w.trace if x[:2]==('construct', 'native')]), 1)
        terminal = json.loads(''.join(w.stdout.parts))
        self.assertEqual(terminal['caller_receipt'], w.descriptor('/mem/O/native-execution.json'))

    def test_04_caller_already_default_precondition(self):
        w, rc, r = self.caller('nondefault_chld')
        self.assertEqual(rc, 2)
        self.assertIsNone(r)
        self.assertFalse(any(x[0]=='construct' for x in w.trace))
        self.assertNotIn(('handler', 20), w.trace)

    def test_05_lost_owner_handshake_revokes_next_signal(self):
        w, rc, r = self.owner('handshake_echild')
        self.assertEqual(rc, 2)
        self.assertEqual(r['ownership_state']['leader_reap']['direct_child_relationship'], 'lost')
        self.assertIsNone(r['ownership_state']['leader_reap']['raw_returncode'])
        self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))
        self.assertEqual(w.wait_counts[LEADER], 1)

    def test_06_lost_terminal_relationship_never_resignals(self):
        w, rc, r = self.owner('terminal_echild')
        self.assertEqual(rc, 2)
        self.assertEqual(r['ownership_state']['leader_reap']['direct_child_relationship'], 'lost')
        self.assertEqual([x[2] for x in w.trace if x[0]=='kill'], [19])
        self.assertFalse(any(x[0]=='killpg' for x in w.trace))
        self.assertEqual(w.wait_counts[LEADER], 2)

    def test_07_lost_owner_query_closes_only_that_pid_authority(self):
        w, rc, r = self.owner('query_echild')
        self.assertEqual(rc, 2)
        q = r['resources']['query_records'][0]
        self.assertEqual(q['exit']['direct_child_relationship'], 'lost')
        self.assertIsNone(q['exit']['raw_returncode'])
        self.assertFalse(any(x[0]=='kill' and x[1]==q['PID'] for x in w.trace))
        self.assertEqual(w.wait_counts[q['PID']], 1)
        self.assertEqual(len([x for x in w.trace if x[:3]==('killpg', LEADER, 15)]), 1)

    def test_08_lost_caller_query_has_no_pid_signal(self):
        w, rc, r = self.caller('query_echild')
        self.assertEqual(rc, 2)
        q = r['query_records'][0]
        self.assertEqual(q['exit']['direct_child_relationship'], 'lost')
        self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))
        self.assertEqual(w.wait_counts[q['PID']], 1)

    def test_09_lost_native_reap_stays_unknown(self):
        w, rc, r = self.caller('native_echild')
        self.assertEqual(rc, 2)
        self.assertEqual(r['native']['exit']['direct_child_relationship'], 'lost')
        self.assertIsNone(r['native']['exit']['raw_returncode'])
        self.assertEqual(w.wait_counts[NATIVE], 1)
        self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))

    def test_10_actual_caller_evidence_rejects_clock_echo_and_stdout_mutants(self):
        expected = dict(bad_deadline='Shared original caller deadline mismatch',
            future_observed='Nanosecond value exceeds declared clock bound', bad_echo='Exact token/authorization echo required',
            extra_stdout='Exactly two typed adapter stdout lines required', bad_schema='Complete typed caller candidate required',
            partial_receipt='Expecting', missing_receipt='Missing regular file')
        for mode in expected:
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertNotEqual(r['status'], 'COMPLETE_CANDIDATE')
                self.assertEqual(r['native_receipt_evidence_status']['status'], 'failed')
                self.assertTrue(r['errors_stops_signals']['all_errors'])
                self.assertTrue(any(expected[mode] in row['message'] for row in r['errors_stops_signals']['all_errors']))

    def test_11_full_main_postwrite_failure_preserves_prefinal_bytes_and_raw_refusal(self):
        for mode in ('postwrite_mismatch', 'postwrite_error', 'postwrite_late', 'postwrite_stop'):
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertEqual(r['status'], 'COMPLETE_CANDIDATE')
                self.assertEqual(bytes(w.files['/mem/D/closed-result.json']), w.closed_bytes)
                self.assertEqual(sum(x[:3]==('file-open', '/mem/D/closed-result.json', 'xb') for x in w.trace), 1)
                if mode=='postwrite_stop':
                    self.assertTrue(w.ns['_STOP_REQUESTS'])
                else:
                    self.assertIn('Incomplete/refused owner preservation:', ''.join(w.stderr.parts))
                self.assertTrue(any(x==('identity-inputs', True) for x in w.trace))

    def test_12_identity_edge_refuses_without_normal_wait_or_replacement(self):
        for mode in ('wrong_identity', 'wrong_native_pid', 'wrong_native_pgid', 'identity_missing', 'identity_stop', 'identity_equal'):
            with self.subTest(mode=mode):
                w, rc, r = self.caller(mode)
                self.assertEqual(rc, 2)
                self.assertFalse(r['prefinal_candidate'])
                self.assertEqual(len([x for x in w.trace if x[:2]==('construct', 'native')]), 1)
                self.assertEqual(len([x for x in w.trace if x[:2]==('construct', 'query')]), 1)
                # A permitted refusal/finally reap is distinct from normal running.
                self.assertTrue(all(x[3]>0 or x[4]>0 for x in w.trace if x[:2]==('waitpid', NATIVE)))
                self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))

    def test_13_precontinuation_abort_is_direct_pid_only(self):
        for mode in ('bad_pgid', 'registration_error'):
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertFalse(r['continuation']['attempted'])
                self.assertEqual([x[2] for x in w.trace if x[0]=='kill'], [9])
                self.assertFalse(any(x[0]=='killpg' and x[2]!=0 for x in w.trace))

    def test_14_cont_uncertainty_group_cleanup_and_first_deadlines(self):
        for mode in ('cont_error', 'cont_term_eperm', 'cont_term_esrch', 'cont_nonanchor'):
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertTrue(r['continuation']['attempted'])
                self.assertFalse(r['continuation']['acknowledged'])
                self.assertEqual([x[2] for x in w.trace if x[0]=='kill'], [19])
                state = r['ownership_state']
                self.assertEqual(int(state['TERM_until_ns']), min(int(state['first_TERM_ns'])+10_000_000_000,T0+105_000_000_000))
                self.assertEqual(len([x for x in w.trace if x[:3]==('killpg', LEADER, 15)]), 1)
                self.assertEqual(len([x for x in w.trace if x[:3]==('killpg', LEADER, 9)]), int(mode=='cont_nonanchor'))

    def test_15_owner_constructor_unknown_or_late_preserves_exact_ownership(self):
        for mode in ('owner_constructor_unknown', 'owner_constructor_late'):
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertFalse(r['continuation']['attempted'])
                if mode=='owner_constructor_unknown':
                    self.assertIsNone(r['ownership_state']['leader_PID'])
                    self.assertEqual(r['ownership_state']['leader_reap']['status'], 'unknown')
                    self.assertFalse(any(x[0] in ('kill', 'killpg', 'waitpid') for x in w.trace))
                    self.assertEqual(r['final_group_absence']['status'], 'not_reached')
                else:
                    self.assertEqual(r['ownership_state']['leader_PID'], LEADER)
                    self.assertEqual([x[2] for x in w.trace if x[0]=='kill'], [9])
                    self.assertFalse(any(x[0]=='killpg' for x in w.trace))
                    self.assertEqual(w.wait_counts[LEADER], 1)

    def test_16_native_constructor_unknown_or_late_never_gains_signal_authority(self):
        for mode in ('caller_constructor_unknown', 'caller_constructor_late'):
            with self.subTest(mode=mode):
                w, rc, r = self.caller(mode)
                self.assertEqual(rc, 2)
                self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))
                self.assertFalse(any(x[:2]==('construct', 'query') for x in w.trace))
                if mode=='caller_constructor_unknown':
                    self.assertIsNone(r['native']['PID'])
                    self.assertEqual(r['native']['exit']['status'], 'unknown')
                    self.assertFalse(any(x[0]=='waitpid' for x in w.trace))
                else:
                    self.assertEqual(r['native']['PID'], NATIVE)
                    self.assertEqual(w.wait_counts[NATIVE], 1)
                    self.assertFalse(r['prefinal_candidate'])

    def test_17_sample_error_is_not_erased_by_exit_event(self):
        w, rc, r = self.owner('query_malformed')
        self.assertEqual(rc, 2)
        self.assertEqual(r['resources']['peak'], None)
        self.assertTrue(r['caller_exit']['NOTE_EXIT_events'])
        self.assertTrue(r['errors_stops_signals']['all_errors'])
        self.assertIsNotNone(r['resources']['query_records'][0]['error'])

    def test_18_postreap_presence_or_unknown_never_resignals(self):
        for mode in ('absence_present', 'absence_eperm'):
            with self.subTest(mode=mode):
                w, rc, r = self.owner(mode)
                self.assertEqual(rc, 2)
                self.assertEqual(len([x for x in w.trace if x[:3]==('killpg', LEADER, 0)]), 1)
                self.assertFalse(any(x[0]=='killpg' and x[2]!=0 for x in w.trace))
                self.assertEqual([x[2] for x in w.trace if x[0]=='kill'], [19])

    def query(self, role, mode):
        w = self.world(role, mode)
        callback = lambda exc: w.trace.append(('query-parent-error', type(exc).__name__))
        f = w.ns['sample_owned'] if role=='owner' else w.ns['native_identity']
        return w, f, callback

    def test_19_actual_fixed_queries_drain_split_streams_and_accept_reported_zero(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w, f, cb = self.query(role, 'normal')
                result = f(LEADER if role=='owner' else NATIVE, 'fake integration', cb)
                q = result['query_record']
                self.assertTrue(q['stdout_complete'] and q['stderr_complete'])
                self.assertFalse(q['partial_capture'])
                self.assertEqual(q['exit']['raw_returncode'], 0)
                self.assertEqual(bytes(w.files[str(w.ns['QUERY_ROOT']/'query-001.stderr')]), b'FAKE stderr')
                if role=='owner':
                    self.assertEqual(result['RSS_bytes'], 0)
                self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))

    def test_20_reaped_query_partial_eof_error_never_signals_reused_pid(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w, f, cb = self.query(role, 'query_partial')
                with self.assertRaises(BaseException):
                    f(LEADER if role=='owner' else NATIVE, 'partial EOF', cb)
                q = w.ns['_QUERY_RECORDS'][0]
                self.assertEqual(q['exit']['status'], 'reaped')
                self.assertTrue(q['partial_capture'])
                self.assertFalse(q['stderr_complete'])
                self.assertTrue(q['stdout_complete'])
                self.assertEqual(w.wait_counts[q['PID']], 1)
                self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))
                self.assertEqual(bytes(w.files[str(w.ns['QUERY_ROOT']/'query-001.stderr')]), b'FAKE stderr')

    def test_21_unreaped_query_timeout_parent_refusal_precedes_own_pid_cleanup(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w, f, cb = self.query(role, 'query_timeout')
                with self.assertRaises(BaseException):
                    f(LEADER if role=='owner' else NATIVE, 'unreaped timeout', cb)
                q = w.ns['_QUERY_RECORDS'][0]
                self.assertEqual(q['exit']['status'], 'reaped')
                parent = next(i for i,x in enumerate(w.trace) if x[0]=='query-parent-error')
                kill = next(i for i,x in enumerate(w.trace) if x[:3]==('kill', q['PID'], 9))
                self.assertLess(parent, kill)
                self.assertEqual(len(q['stop_actions']), 1)
                self.assertLessEqual(int(q['KILL_until_ns']), T0+110_000_000_000)

    def test_22_actual_retained_destructor_normal_unreaped_and_partial_instances(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w = self.world(role)
                cls = w.ns['_RetainedPopen']
                # Explicitly call the actual override on partial and ordinary fake instances.
                partial = cls.__new__(cls)
                partial.__del__()
                handle = cls(['FAKE-native'], start_new_session=False)
                handle.__del__()
                handle.returncode = 0
                handle.__del__()
                self.assertFalse(any(x[0]=='unexpected' for x in w.trace))

    def test_23_no_wait_after_cutoff_and_unknown_does_not_become_zero(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w = self.world(role)
                handle = w.ns['_RetainedPopen'](['FAKE-native'], start_new_session=False)
                record = dict(status='unreaped', direct_child_relationship='retained_unreaped', numeric_signal_authority=False,
                    raw_returncode=None, wait_status=None)
                w.clock.now = T0+110_000_000_000
                with self.assertRaises(w.ns['DeadlineRefusal']):
                    w.ns['exact_reap'](handle, record, T0+110_000_000_000)
                self.assertIsNone(record['raw_returncode'])
                handle.__del__()
                self.assertFalse(any(x[0] in ('waitpid', 'kill', 'killpg', 'unexpected') for x in w.trace))

    def test_24_canonical_original_token_variants_are_refused(self):
        for role in ('owner', 'caller', 'wrapper'):
            w = self.world(role)
            f = w.ns['token'] if role=='wrapper' else w.ns['clock_token']
            self.assertEqual(f(str(T0)), T0)
            for value in ('0', '01', '+1', '-1', ' 1', '1\n', '\u0661', True, 1, str(w.clock.now+10_000_000_000)):
                with self.subTest(role=role, value=value):
                    with self.assertRaises(ValueError):
                        f(value)

    def test_25_actual_deadline_bypasses_capture_and_same_and_preserves_consumed_status(self):
        w = self.world('owner')
        with self.assertRaises(w.ns['DeadlineRefusal']):
            w.ns['capture'](lambda: w.ns['guard'](0, 'injected deadline'))
        # The real syscall consumes a terminal status before the late-return refusal.
        h = w.ns['_RetainedPopen'](['FAKE-native'], start_new_session=False)
        record = dict(status='unreaped', direct_child_relationship='retained_unreaped', numeric_signal_authority=False,
            raw_returncode=None, wait_status=None)
        actual_wait = w.ns['os'].waitpid
        def late_wait(pid, flags):
            value = actual_wait(pid, flags)
            w.clock.now = T0+110_000_000_000
            return value
        w.ns['os'].waitpid = late_wait
        with self.assertRaises(w.ns['DeadlineRefusal']):
            w.ns['exact_reap'](h, record, T0+110_000_000_000)
        self.assertEqual(record['status'], 'reaped')
        self.assertEqual(record['raw_returncode'], 0)
        before = len(w.trace)
        self.assertTrue(w.ns['exact_reap'](h, record, T0+110_000_000_000))
        self.assertEqual(len(w.trace), before)
        c = self.world('caller')
        c.clock.now = T0+95_000_000_000
        with self.assertRaises(c.ns['DeadlineRefusal']):
            c.ns['same'](c.path('/mem/card.json'), '0'*64)

    def test_26_actual_inclusive_union_counts_distinct_paths_and_pending_receipt(self):
        w = self.world('owner')
        w.put('/mem/extra-a', b'x')
        w.put('/mem/extra-b', b'x')
        a, b = w.descriptor('/mem/extra-a'), w.descriptor('/mem/extra-b')
        before = w.ns['inclusive_bytes']({})
        self.assertEqual(w.ns['inclusive_bytes']({'one': a, 'duplicate_role': a, 'other_path': b}), before+2)
        w.virtual_sizes['/mem/extra-a'] = 536870912-before-1
        with self.assertRaises(ValueError):
            w.ns['budgets']({'one': a}, {}, pending=1)
        w.virtual_sizes.clear()
        growth = w.ns['growth_bytes'](w.ns['OUTPUT'], w.ns['ROOT_EXECUTION'], {})
        key = '/mem/O/old-end.grid'
        w.virtual_sizes[key] = len(w.files[key])+33554432-growth-1
        with self.assertRaises(ValueError):
            w.ns['budgets']({}, {}, pending=1)

    def test_27_wrapper_real_main_orders_hello_stop_and_exact_handoff(self):
        w = self.world('wrapper')
        with self.assertRaises(ExecHandoff):
            w.ns['main']()
        hello = json.loads(''.join(w.stdout.parts))
        self.assertEqual(hello['owner_start_ns'], str(T0))
        flush = next(i for i,x in enumerate(w.trace) if x[:2]==('text-flush', 'stdout'))
        stop = next(i for i,x in enumerate(w.trace) if x[:3]==('kill', LEADER, 17))
        handoff = next(i for i,x in enumerate(w.trace) if x[0]=='execv')
        self.assertLess(flush, stop)
        self.assertLess(stop, handoff)
        argv = w.trace[handoff][2]
        self.assertEqual(argv[-3:], ('--owner-start-ns', str(T0), '--execute'))
        self.assertEqual(argv[4], '/mem/S/run_native_capture.py')
        self.assertFalse(any(x[0]=='construct' for x in w.trace))

    def test_28_early_consumed_terminal_is_not_continued_or_reaped_twice(self):
        w, rc, r = self.owner('early_terminal')
        self.assertEqual(rc, 2)
        self.assertEqual(r['caller_exit']['reap']['raw_returncode'], 1)
        self.assertEqual(r['caller_exit']['reap']['status'], 'reaped')
        self.assertEqual(w.wait_counts[LEADER], 1)
        self.assertFalse(any(x[0] in ('kill', 'killpg') for x in w.trace))

    def test_29_whole_owner_unreaped_late_return_preserves_unknown_without_new_api(self):
        w, rc, r = self.owner('leader_unreaped_late')
        self.assertEqual(rc, 2)
        self.assertEqual(r['caller_exit']['reap']['status'], 'unreaped')
        self.assertIsNone(r['caller_exit']['reap']['raw_returncode'])
        self.assertEqual(r['final_group_absence']['status'], 'not_reached')
        self.assertFalse(any(x[0] in ('waitpid', 'kill', 'killpg') and x[-1]>=T0+110_000_000_000 for x in w.trace))

    def test_30_whole_owner_query_timeout_latches_term_before_query_pid_cleanup(self):
        w, rc, r = self.owner('query_timeout')
        self.assertEqual(rc, 2)
        q = r['resources']['query_records'][0]
        self.assertIsNotNone(q['error'])
        parent = next(i for i,x in enumerate(w.trace) if x[:3]==('killpg', LEADER, 15))
        query = next(i for i,x in enumerate(w.trace) if x[:3]==('kill', q['PID'], 9))
        self.assertLess(parent, query)
        self.assertEqual(len([x for x in w.trace if x[:3]==('killpg', LEADER, 15)]), 1)
        state = r['ownership_state']
        self.assertEqual(int(state['TERM_until_ns']), min(int(state['first_TERM_ns'])+10_000_000_000,T0+105_000_000_000))

    def test_31_actual_timeout_conversion_and_original_equality_return_check(self):
        for role in ('owner', 'caller'):
            with self.subTest(role=role):
                w = self.world(role)
                until = w.clock.now+1_000_000
                value = w.ns['timeout_seconds'](until, 1_000_000)
                self.assertGreater(value, 0)
                self.assertLess(value, (until-w.clock.now)/1_000_000_000)
                until = w.clock.now+10_000
                calls = []
                def fixed_api():
                    calls.append(True)
                    w.clock.now = until
                    return 'FAKE completed API value'
                with self.assertRaises(w.ns['DeadlineRefusal']):
                    w.ns['call'](until, 'fake original-bound equality', fixed_api)
                self.assertEqual(calls, [True])


if __name__ == '__main__':
    unittest.main(verbosity=2)
