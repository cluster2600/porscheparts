"""Calculate independent layers in bounded worker processes and return their original order."""
from concurrent.futures import ProcessPoolExecutor
import math
import multiprocessing
import os
import resource
import time
from types import SimpleNamespace

import numpy as np
import trimesh
from layers import face_z_bounds, layer_geometry

WORKER = None


def initialize(vertices, faces, parameters):
    global WORKER
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    WORKER = (SimpleNamespace(geometry=mesh), dict(parameters), face_z_bounds(mesh))


def calculate(z):
    part, parameters, bounds = WORKER
    data = layer_geometry(part, z, parameters, bounds)
    return data, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


class ParallelLayers:
    def __init__(self, parameters, workers=4, heights=None):
        if workers not in (1, 2, 4):
            raise ValueError('Use one, two or four slicing workers')
        self.parameters = dict(parameters)
        self.workers = workers
        self.heights = None if heights is None else list(heights)
        self.pool = None
        self.pending = {}
        self.next_index = 0
        self.completed = 0
        self.maximum_worker_rss = 0
        self.started = None
        self.closed = False

    def __enter__(self):
        return self

    def start(self, part):
        if self.closed:
            raise ValueError('Slicing worker group is already closed')
        self.started = time.monotonic()
        mesh = part.geometry
        if self.heights is None:
            height = self.parameters['layer_height_mm']
            self.heights = [(index + .5) * height for index in range(math.ceil(mesh.bounds[1, 2] / height))]
        if not self.heights or not np.isfinite(self.heights).all():
            raise ValueError('A finite list of layer midplanes is required')
        # These are worker resource settings, not geometry or scan parameters.
        self.previous_environment = {name: os.environ.get(name) for name in
                                     ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}
        for name in self.previous_environment:
            os.environ[name] = '1'
        try:
            self.pool = ProcessPoolExecutor(max_workers=self.workers,
                mp_context=multiprocessing.get_context('spawn'), initializer=initialize,
                initargs=(np.asarray(mesh.vertices), np.asarray(mesh.faces), self.parameters))
            for _ in range(min(2 * self.workers, len(self.heights))):
                self.submit()
        finally:
            for name, value in self.previous_environment.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def submit(self):
        index = self.next_index
        self.pending[index] = self.pool.submit(calculate, self.heights[index])
        self.next_index += 1

    def __call__(self, part, z):
        if self.pool is None:
            self.start(part)
        if self.closed or self.completed >= len(self.heights) or z != self.heights[self.completed]:
            raise ValueError('Slicing calls must follow the declared exact midplanes in order')
        data, rss = self.pending.pop(self.completed).result()
        self.maximum_worker_rss = max(self.maximum_worker_rss, rss)
        self.completed += 1
        if self.next_index < len(self.heights):
            self.submit()
        return data

    def close(self):
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)
        self.closed = True

    def __exit__(self, *_):
        self.close()

    def receipt(self):
        return {'workers': self.workers, 'maximum_pending_layers': 2 * self.workers,
                'completed_layers': self.completed, 'declared_layers': None if self.heights is None else len(self.heights),
                'worker_group_closed': self.closed,
                'maximum_individual_worker_ru_maxrss_native_units': self.maximum_worker_rss,
                'ru_maxrss_units': 'bytes on macOS; KiB on Linux',
                'elapsed_seconds': None if self.started is None else time.monotonic() - self.started,
                'layer_order_preserved': True, 'worker_BLAS_thread_limit': 1,
                'scope': 'Independent native layer calculations; parent retains support slicing and ordered file publication.'}
