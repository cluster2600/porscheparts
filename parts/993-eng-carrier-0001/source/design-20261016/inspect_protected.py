"""Compare the exported candidate with frozen V6f protected BRep regions."""
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]
sys.path.insert(0, str(SOURCE.parent / 'bionic-20261011/correction-20261013'))
from corrected_cad import precise_volume, sha
from inspect_candidate import inspect


def check(folder):
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import Box, Pos, import_step
    folder = Path(folder)
    baseline_path = ROOT / 'parts/993-eng-carrier-0001/derived/correction-20261013/carrier.step'
    plan = json.loads((SOURCE / 'plan.json').read_text())
    assert sha(baseline_path) == plan['baseline_STEP_sha256']
    before, after = import_step(baseline_path), import_step(folder / 'carrier.step')
    region = Pos(0, 0, 0) * Box(130, 72, 8)
    original, candidate = before & region, after & region
    assert original is not None and candidate is not None
    removed, added = original - candidate, candidate - original
    difference = sum(precise_volume(shape)[0] if shape is not None else 0
                     for shape in (removed, added))
    assert difference <= plan['criteria']['protected_interface_symmetric_difference_mm3_max']
    inherited = inspect(folder)
    assert inherited['study_assembly_screen_pass']
    report = {'baseline_STEP_sha256': sha(baseline_path),
              'candidate_STEP_sha256': sha(folder / 'carrier.step'),
              'plan_sha256': sha(SOURCE / 'plan.json'),
              'source_sha256': sha(__file__),
              'central_pad_symmetric_difference_mm3': difference,
              'end_interface_symmetric_difference_mm3': inherited['end_interface_symmetric_difference_mm3'],
              'study_assembly_screen_pass': inherited['study_assembly_screen_pass'],
              'mass_ceiling_pass': inherited['mass_ceiling_pass'],
              'nominal_mass_kg': inherited['nominal_mass_kg'],
              'OEM_interfaces': None, 'manufacturing_authorized': False}
    (folder / 'protected-interfaces.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    check(sys.argv[1])
