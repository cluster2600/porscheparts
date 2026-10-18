"""Replay unchanged exact unit admissions in four bounded spawn workers."""
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import copy
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ENGINE = SOURCE/'build_cached_v5.py'
ENGINE_SHA256 = '65fa95a0fce52dadcf267126bf67dc07ae690b241f90f0f206ac8225cb61cac6'
AREA = SOURCE/'incremental_combinatorial_interfaces_area.py'
AREA_SHA256 = '2230847e5862b3d6668a900c2774ebb82cb3f12555486747fb06dfe8d5a90341'
PROOF_SHA256 = '62082815b2e78ee66c11f91818f2f63c46b180f75664ede6f7ef602f9a57a432'
PLAN_SHA256 = '0d684f4558cf2c818e18bb418a4ba616034c511793bc238a98b5db6f8a59891f'
FIXED_UNITS = {(3, 'grid-0-0'): 'source-003-grid-axis0-plane0', (3, 'skin-0'): 'source-003-skin0',
               (9, 'grid-0-0'): 'source-009-grid-axis0-plane0', (9, 'skin-0'): 'source-009-skin0'}
WORKER_ENGINE = None
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
encoded = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
identity = lambda value: hashlib.sha256(encoded(value)).hexdigest()


def runtime_identity():
    from region_checkpoints import runtime_identity as current
    return current()


def load_engine():
    if sha(ENGINE) != ENGINE_SHA256:
        raise ValueError('The unchanged exact admission driver differs')
    spec = importlib.util.spec_from_file_location('_parallel_exact_admission_engine', ENGINE)
    engine = importlib.util.module_from_spec(spec); spec.loader.exec_module(engine)
    engine.verify_sources()
    return engine


def initialise(sources, expected_runtime):
    global WORKER_ENGINE
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    if any(sha(path) != digest for path, digest in sources.items()):
        raise ValueError('An exact admission worker source differs')
    if runtime_identity() != expected_runtime:
        raise ValueError('An exact admission worker runtime differs')
    WORKER_ENGINE = load_engine()
    if sha(AREA) != AREA_SHA256:
        raise ValueError('The exact area-reuse assembly differs')
    spec = importlib.util.spec_from_file_location('_parallel_area_reuse_assembly', AREA)
    area = importlib.util.module_from_spec(spec); spec.loader.exec_module(area)
    WORKER_ENGINE._index._OLD._Assembly = area._Assembly
    WORKER_ENGINE._redundant._IDS._OLD._Assembly = area._Assembly


def calculate(reconstruction, contacts, penetration):
    try:
        return WORKER_ENGINE.continuous_admission(reconstruction, contacts, penetration)
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return dict(passed=False, status='rejected', error=str(error))


def units(support):
    skin = support.get('peripheral_skin') or {}
    if skin.get('continuous_fragmented_interfaces') is not True:
        raise ValueError('Every region requires the explicit continuous strategy')
    rows = []
    for axis, record in enumerate(support['grid_coverage']['axes']):
        rows.extend((f'grid-{axis}-{plane["order"]}', plane['continuous_interface_reconstruction'], plane['contacts'])
                    for plane in record['planes'])
    rows.extend((f'skin-{c["index"]}', c['infill']['continuous_interface_reconstruction'], c['infill']['interface_contacts'])
                for c in skin['components'])
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError('Duplicate support surface unit')
    if not rows:
        raise ValueError('No support surface unit was verified')
    return rows


class FourProvenResults:
    """Only the four reviewed real 003/009 results; no general cache policy."""
    def __init__(self, path, producers, engine):
        self.path = Path(path).resolve()
        folder = self.path.parent
        plan_path, runtime_path = folder/'frozen-plan.json', folder/'runtime-before.json'
        if sha(self.path) != PROOF_SHA256 or sha(plan_path) != PLAN_SHA256:
            raise ValueError('The four proven unit receipts differ')
        report = json.loads(self.path.read_text()); plan = json.loads(plan_path.read_text())
        if (report['status'] != 'selected_real_units_replayed_no_global_admission' or
                not report['inputs_and_sources_unchanged'] or not report['runtime_unchanged'] or
                sha(runtime_path) != report['runtime_before_sha256'] or
                report['runtime_before_sha256'] != report['runtime_after_sha256'] or
                runtime_identity() != json.loads(runtime_path.read_text())):
            raise ValueError('The proven unit runtime or execution identity differs')
        for path in engine.POLICY_FILES:
            digest = engine.POLICY_SHA256[path]
            found = [value for name, value in plan['inputs_sha256'].items() if Path(name).name == path.name]
            if found != [digest]:
                raise ValueError('A proven exact admission source differs')
        for producer in report['producer_identities']:
            source_index = producer['source_index']
            if source_index in (3, 9) and any(producers[source_index][key] != producer[key]
                    for key in ('checkpoint_sha256', 'metadata_sha256', 'surface_sha256')):
                raise ValueError('A proven unit producer checkpoint differs')
        self.rows = {row['id']: row for row in report['cases'] if row['id'] in FIXED_UNITS.values()}
        if set(self.rows) != set(FIXED_UNITS.values()) or any(r['status'] != 'passed' for r in self.rows.values()):
            raise ValueError('All four proven results are required')
        self.files = {self.path: PROOF_SHA256, plan_path: PLAN_SHA256, runtime_path: sha(runtime_path)}
        self.runtime = json.loads(runtime_path.read_text())

    def get(self, source_index, unit, reconstruction, contacts, penetration):
        name = FIXED_UNITS.get((source_index, unit))
        if name is None:
            return None
        row = self.rows[name]
        if (identity(reconstruction) != row['reconstruction_sha256'] or identity(contacts) != row['contacts_sha256'] or
                reconstruction['combinatorial_construction_source_sha256'] != row['recorded_authority'] or
                reconstruction['vertical_contact_penetration_mm'] != penetration):
            raise ValueError('A proven unit payload or penetration differs')
        return copy.deepcopy(row['result'])


class ParallelExactAdmissions:
    def __init__(self, source_indices, sources, proven=None, workers=4):
        if workers not in (1, 4):
            raise ValueError('Use one or four exact admission workers')
        self.source_indices, self.sources, self.proven = list(source_indices), dict(sources), proven
        self.workers, self.window, self.pool = workers, workers*2, None
        self.rows, self.closed = [], False
        self.runtime_before, self.runtime_after = None, None

    def __enter__(self):
        if self.pool is not None or self.closed:
            raise ValueError('Exact admission workers can be started only once')
        self.runtime_before = runtime_identity()
        if self.proven is not None and self.runtime_before != self.proven.runtime:
            raise ValueError('The reviewed results and replay parent runtime differ')
        keys = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
        previous = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys: os.environ[key] = '1'
            self.pool = ProcessPoolExecutor(max_workers=self.workers,
                mp_context=multiprocessing.get_context('spawn'), initializer=initialise,
                initargs=(self.sources, self.runtime_before))
        except BaseException:
            self.close(); raise
        finally:
            for key, value in previous.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
        return self

    def __call__(self, support, penetration):
        if self.pool is None or self.closed:
            raise ValueError('The exact admission worker group is not active')
        source_index = self.source_indices[support['index']]
        selected = units(support); results, origins, pending = {}, {}, {}
        jobs = []
        for index, (name, reconstruction, contacts) in enumerate(selected):
            cached = None if self.proven is None else self.proven.get(source_index, name, reconstruction, contacts, penetration)
            if cached is None: jobs.append(index)
            else: results[index], origins[index] = cached, 'reviewed_real_result_reused'
        next_job = 0
        while pending or next_job < len(jobs):
            while next_job < len(jobs) and len(pending) < self.window:
                index = jobs[next_job]; _, reconstruction, contacts = selected[index]
                pending[self._submit(reconstruction, contacts, penetration)] = index
                next_job += 1
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                index = pending.pop(future)
                results[index], origins[index] = future.result(), 'exact_function_with_reused_exact_cycle_areas'
        for index, (name, reconstruction, contacts) in enumerate(selected):
            self.rows.append(dict(source_index=source_index, unit=name, origin=origins[index],
                reconstruction_sha256=identity(reconstruction), contacts_sha256=identity(contacts),
                penetration_mm=penetration, result_sha256=identity(results[index])))
        return {name: results[index] for index, (name, _, _) in enumerate(selected)}

    def _submit(self, *args):
        # Spawn is lazy: bound BLAS threads while submit actually starts children.
        keys = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
        previous = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys: os.environ[key] = '1'
            return self.pool.submit(calculate, *args)
        finally:
            for key, value in previous.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value

    def close(self):
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)
        self.closed = True
        self.runtime_after = runtime_identity()

    def __exit__(self, *_):
        self.close()
        if any(sha(path) != digest for path, digest in self.sources.items()):
            raise ValueError('An exact admission source changed during replay')
        if self.runtime_before != self.runtime_after:
            raise ValueError('The exact admission parent runtime changed during replay')

    def receipt(self):
        return dict(schema='bounded-exact-unit-replays-1', status='worker_group_closed' if self.closed else 'incomplete',
            workers=self.workers, maximum_pending_futures=self.window, worker_group_closed=self.closed,
            engine_source_sha256=ENGINE_SHA256, sources_sha256={str(p): h for p, h in self.sources.items()},
            replay_assembly_sha256=AREA_SHA256, reused_results_assembly_sha256='81422bc8ce95beab8039e33f70a9d1274083be1ce1426c778c700a06a8b21df8',
            runtime_before_sha256=None if self.runtime_before is None else identity(self.runtime_before),
            runtime_after_sha256=None if self.runtime_after is None else identity(self.runtime_after),
            worker_runtime_identity_verified_at_initialisation=True,
            units=self.rows, scope='Exact unit replays only; the historical parent seal retains all six admissions')
