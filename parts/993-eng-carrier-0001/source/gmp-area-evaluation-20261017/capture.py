"""Capture one real exact_area call; stop before evaluating that ring."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/process-skins-20261016'
PIN = '81422bc8ce95beab8039e33f70a9d1274083be1ce1426c778c700a06a8b21df8'
INPUT = ROOT / 'work/carrier-process-20261016/incremental-large-chart-ids-001/assessment.json'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, data):
    (BASE / name).write_text(json.dumps(data, separators=(',', ':'), allow_nan=False)+'\n')
def points_encoded(points):
    return [[[str(c.numerator), str(c.denominator)] for c in p] for p in points]
class Captured(BaseException): pass
def expired(*_): raise TimeoutError('Capture-only budget 90 seconds')
signal.signal(signal.SIGALRM, expired)
signal.alarm(90)
resource.setrlimit(resource.RLIMIT_CPU, (90, 91))
assert os.getpriority(os.PRIO_PROCESS, 0) == 10
source_files = list(SOURCE.glob('*.py'))
before = {str(p.relative_to(ROOT)): sha(p) for p in source_files}
assert sha(SOURCE / 'incremental_combinatorial_interfaces_ids.py') == PIN
spec = importlib.util.spec_from_file_location('_private_gmp_capture_814', SOURCE / 'incremental_combinatorial_interfaces_ids.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
import shapely
data = json.loads(INPUT.read_text())
domain = shapely.from_wkb(data['domain_wkb_hex'])
assert len(domain.exterior.coords)-1 == 5876
Q = engine._OLD.Q
write('real-domain-ring.json', dict(schema='exact-rational-ring-1', origin='captured historical domain WKB, no geometric operation',
    input_sha256=sha(INPUT), source_index=1, skin_index=1,
    points=points_encoded([tuple(Q(c) for c in p) for p in list(domain.exterior.coords)[:-1]])))
original = engine._OLD.exact_area
small_calls = 0
def intercept(points):
    global small_calls
    if len(points) > 5000:
        write('intercepted-ring.json', dict(schema='exact-rational-ring-1',
            origin='First actual base69 exact_area call with more than 5000 points in private constructor814',
            input_sha256=sha(INPUT), constructor_sha256=PIN, source_index=1, skin_index=1,
            point_count=len(points), prior_small_area_calls=small_calls,
            points=points_encoded(points)))
        raise Captured()
    small_calls += 1
    return original(points)
engine._OLD.exact_area = intercept
wall, cpu = time.perf_counter(), time.process_time()
report = dict(schema='gmp-area-real-capture-1', regional_generator_executed=False, adopted=False)
try:
    engine.construct_with_statistics(domain, data['interfaces'], .2)
    raise AssertionError('Expected capture did not happen')
except Captured:
    report.update(status='captured_before_ring_area_evaluation', captured_ring_sha256=sha(BASE/'intercepted-ring.json'))
finally:
    engine._OLD.exact_area = original
    signal.alarm(0)
    after = {str(p.relative_to(ROOT)): sha(p) for p in source_files}
    report.update(wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
        maximum_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        frozen_source_sha256=before, frozen_sources_unchanged=before==after,
        input_sha256=sha(INPUT), capture_script_sha256=sha(Path(__file__)),
        nice=os.getpriority(os.PRIO_PROCESS, 0), source_boundary_vertices=5876,
        full_constructor_completed=False, capture_only=True)
    write('capture-assessment.json', report)
assert report['frozen_sources_unchanged']
print(json.dumps({k:v for k,v in report.items() if k!='frozen_source_sha256'}), flush=True)
