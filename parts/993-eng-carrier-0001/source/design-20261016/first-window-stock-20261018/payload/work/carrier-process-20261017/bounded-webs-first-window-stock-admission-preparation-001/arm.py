"""Derive exactly the three ROOT-approved controls for the saved-stock local check."""
import copy
import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
EXPECTED_GO = '9f09027936527b98949868b36c75a290e9f90ba2a69771365f5d4785817a139b'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''): digest.update(block)
    return digest.hexdigest()

def encoded(value): return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
def read(path): return json.loads(path.read_bytes())
def write(path, value):
    with path.open('xb') as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())

def main():
    began = time.monotonic()
    go = H / 'root-GO-001.json'; go_name = str(go.relative_to(R))
    assert sha(go) == EXPECTED_GO
    authority = read(go)
    pp, pl, pc = (H / name for name in ('pending-plan.json', 'pending-launch-plan.json', 'pending-command.json'))
    ap, al, ac = (H / name for name in ('plan.json', 'launch-plan.json', 'command.json'))
    for path in (pp, pl, pc): assert sha(path) == authority['pending_sha256'][path.name]
    original_p, original_l, original_c = read(pp), read(pl), read(pc)
    for original, path in ((original_p, pp), (original_l, pl), (original_c, pc)): assert encoded(original) == path.read_bytes()
    for path in (ap, al, ac, R / original_p['output_directory'], R / original_p['execution_directory']):
        assert not path.exists() and not any(parent.is_symlink() for parent in [path, *path.parents])
    p = copy.deepcopy(original_p)
    p.update(launch_ready=True, root_GO=go_name, root_GO_sha256=EXPECTED_GO); p['files_sha256'][go_name] = EXPECTED_GO
    back = copy.deepcopy(p); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None); del back['files_sha256'][go_name]
    assert back == original_p and encoded(back) == pp.read_bytes(); write(ap, p)
    l = copy.deepcopy(original_l)
    l.update(launch_ready=True, root_GO=go_name, root_GO_sha256=EXPECTED_GO)
    assert l['command'][5:7] == [str(pp), sha(pp)]
    l['command'][5:7] = [str(ap), sha(ap)]
    pending_name, active_name = str(pp.relative_to(R)), str(ap.relative_to(R))
    l['inputs_sha256'] = {active_name if key == pending_name else key: sha(ap) if key == pending_name else value for key, value in l['inputs_sha256'].items()}
    l['inputs_sha256'][go_name] = EXPECTED_GO
    back = copy.deepcopy(l); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None)
    back['command'][5:7] = [str(pp), sha(pp)]; del back['inputs_sha256'][go_name]
    back['inputs_sha256'] = {pending_name if key == active_name else key: sha(pp) if key == active_name else value for key, value in back['inputs_sha256'].items()}
    assert back == original_l and encoded(back) == pl.read_bytes(); write(al, l)
    c = copy.deepcopy(original_c); c.update(launch_ready=True, root_GO=go_name, root_GO_sha256=EXPECTED_GO)
    assert c['argv'][4] == str(pl) and c['argv'][6] == sha(pl)
    c['argv'][4], c['argv'][6] = str(al), sha(al)
    back = copy.deepcopy(c); back.update(launch_ready=False, root_GO=None, root_GO_sha256=None); back['argv'][4], back['argv'][6] = str(pl), sha(pl)
    assert back == original_c and encoded(back) == pc.read_bytes(); write(ac, c)
    pins = {**l['source_sha256'], **l['inputs_sha256']}
    assert all(sha(R / name) == digest for name, digest in pins.items())
    spec = importlib.util.spec_from_file_location('_armed_window_metadata_only', H / 'admit.py')
    trial = importlib.util.module_from_spec(spec); spec.loader.exec_module(trial); trial.verify(ap, sha(ap), True)
    result = dict(schema='first-window-stock-local-arming-1', status='armed_exactly_one_owned_execution', root_GO_sha256=EXPECTED_GO,
        all_three_whole_object_and_stored_byte_inverses=True, all_current_pins_equal=True, merged_pins=len(pins),
        active_sha256={path.name: sha(path) for path in (ap, al, ac)}, native_executed=False, elapsed_seconds=time.monotonic()-began)
    write(H / 'arming-assessment.json', result); print(json.dumps(result))

if __name__ == '__main__': main()
