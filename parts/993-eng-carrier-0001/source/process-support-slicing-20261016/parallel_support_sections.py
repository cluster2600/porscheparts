"""Compute exact support cuts in bounded workers and retain CORE surface/layer order."""
import hashlib
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace

import numpy as np

SOURCE = Path(__file__).resolve().parent
HOOK = SOURCE.parent / 'process-scanpath-audit-20261016/exact_support_section.py'
sys.path.insert(0, str(HOOK.parent))
from exact_support_section import support_section

_SURFACES = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_hash(array):
    array = np.ascontiguousarray(array)
    return (array.dtype.str, array.shape, hashlib.sha256(array.tobytes()).hexdigest())


def load(paths):
    surfaces = []
    for path, expected in paths:
        if sha(path) != expected:
            raise ValueError('Support source changed before worker loading')
        with np.load(path, allow_pickle=False) as data:
            vertices, faces = data['vertices'].copy(), data['faces'].copy()
        if sha(path) != expected:
            raise ValueError('Support source changed during worker loading')
        heights = vertices[faces, 2]
        bounds = np.column_stack((heights.min(axis=1), heights.max(axis=1)))
        surfaces.append((SimpleNamespace(vertices=vertices, faces=faces), bounds))
    return surfaces


def initialise(paths, hook_hash):
    global _SURFACES
    if sha(HOOK) != hook_hash:
        raise ValueError('Exact support hook identity changed before worker startup')
    _SURFACES = load(paths)


def calculate(z):
    arrays = [support_section(surface, z, bounds) for surface, bounds in _SURFACES]
    return arrays, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


class ParallelSupportSections:
    """Call once per ordered support surface at each exact ordered midplane."""
    def __init__(self, paths, heights, workers=4):
        if workers not in (1, 2, 4):
            raise ValueError('Use one, two or four bounded support workers')
        self.paths = [(str(Path(path).resolve()), sha(path)) for path in paths]
        self.heights = [float(z) for z in heights]
        if (not self.paths or not self.heights or not np.isfinite(self.heights).all()
                or any(a >= b for a, b in zip(self.heights, self.heights[1:]))):
            raise ValueError('Ordered support files and increasing finite heights are required')
        loaded = load(self.paths)
        self.identities = [(array_hash(s.vertices), array_hash(s.faces), array_hash(b)) for s, b in loaded]
        self.frozen = {str(HOOK): sha(HOOK), str(Path(__file__).resolve()): sha(__file__), **dict(self.paths)}
        self.workers, self.window = workers, workers * 2
        self.pool, self.pending, self.surfaces = None, {}, {}
        self.current, self.layer, self.surface, self.next_job = None, 0, 0, 0
        self.closed, self.maximum_rss, self.started = False, 0, None

    def _submit(self):
        while self.next_job < min(len(self.heights), self.layer + self.window):
            self.pending[self.next_job] = self.pool.submit(calculate, self.heights[self.next_job])
            self.next_job += 1

    def __enter__(self):
        if self.pool is not None or self.closed:
            raise ValueError('A support worker group can be started only once')
        self.started = time.monotonic()
        keys = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')
        previous = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ[key] = '1'
            self.pool = ProcessPoolExecutor(max_workers=self.workers,
                mp_context=multiprocessing.get_context('spawn'), initializer=initialise,
                initargs=(self.paths, self.frozen[str(HOOK)]))
            self._submit()
        except BaseException:
            if self.pool is not None:
                self.pool.shutdown(wait=True, cancel_futures=True)
            self.closed = True
            raise
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return self

    def __call__(self, surface, z, bounds):
        if self.pool is None or self.closed or self.layer >= len(self.heights):
            raise ValueError('No ordered support layer remains in this worker group')
        if float(z) != self.heights[self.layer]:
            raise ValueError('Support cuts must consume exact ordered midplanes')
        key = id(surface)
        if key not in self.surfaces:
            identity = (array_hash(surface.vertices), array_hash(surface.faces), array_hash(bounds))
            if identity != self.identities[self.surface]:
                raise ValueError('CORE support surface or bounds differ from the sealed source order')
            # CORE uses these arrays read-only while cutting and exporting its scene.
            surface.vertices.flags.writeable = False
            surface.faces.flags.writeable = False
            self.surfaces[key] = (surface, self.surface)
        elif self.surfaces[key][1] != self.surface:
            raise ValueError('CORE changed the order of support surfaces')
        if self.current is None:
            self.current, rss = self.pending.pop(self.layer).result()
            self.maximum_rss = max(self.maximum_rss, rss)
            if len(self.current) != len(self.paths):
                raise ValueError('A worker omitted a complete support surface')
        result = self.current[self.surface]
        if result.ndim != 3 or result.shape[1:] != (2, 3) or not np.isfinite(result).all():
            raise ValueError('Invalid support worker result')
        self.surface += 1
        if self.surface == len(self.paths):
            self.surface, self.current = 0, None
            self.layer += 1
            self._submit()
        return result

    def __exit__(self, *exception):
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)
        self.closed = True
        if any(sha(path) != expected for path, expected in self.frozen.items()):
            raise ValueError('Parallel support source or exact hook changed during the run')

    def receipt(self):
        return {'workers': self.workers, 'maximum_pending_layers': self.window,
                'completed_layers': self.layer, 'declared_layers': len(self.heights),
                'completed_surfaces_in_current_layer': self.surface, 'worker_group_closed': self.closed,
                'maximum_individual_worker_ru_maxrss_native_units': self.maximum_rss,
                'ru_maxrss_units': 'bytes on macOS; KiB on Linux',
                'sources_and_inputs_sha256': self.frozen,
                'elapsed_seconds': None if self.started is None else time.monotonic()-self.started,
                'method': 'Unchanged exact rational section hook; parent preserves original surface and layer order.'}
