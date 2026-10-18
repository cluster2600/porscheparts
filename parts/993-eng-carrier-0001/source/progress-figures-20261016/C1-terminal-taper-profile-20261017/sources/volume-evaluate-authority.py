"""Three volume overloads on one reloaded native Solid; no Gmsh or meshing."""
import faulthandler
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def evaluate(solid, BRepGProp, GProp_GProps):
    """Exactly the reviewed three overload calls; the same Solid each time."""
    rows = []
    for name, args in [('Gmsh_boolean_F_F_F', (False, False, False)),
                       ('boolean_OnlyClosed_T_F_F', (True, False, False)),
                       ('adaptive_1e-10_T_F', (1e-10, True, False))]:
        props = GProp_GProps()
        returned = BRepGProp.VolumeProperties_s(solid, props, *args)
        if name.startswith('adaptive'):
            assert isinstance(returned, float) and math.isfinite(returned)
        else:
            assert returned is None, 'Boolean overload must return void/None'
        mass = props.Mass()
        assert math.isfinite(mass) and mass > 0
        rows.append(dict(method=name, arguments=list(args), signed_mass_mm3=mass,
                         mass_binary64_hex=mass.hex(), returned_error_estimate=returned))
    return rows

def compare(rows, observed):
    for row in rows:
        mass = row['signed_mass_mm3']
        difference = Fraction(mass) - Fraction(observed)
        row.update(exact_binary64_equal_to_closed_Gmsh_getMass=mass == observed,
                   signed_delta_vs_Gmsh_mm3=mass - observed,
                   exact_binary64_delta_as_rational=str(difference),
                   relative_delta_vs_Gmsh=mass / observed - 1)
    return rows

def main():
    started = time.monotonic()
    faulthandler.enable(all_threads=True)
    plan_hash = sha(HERE / 'plan.json')
    plan = json.loads((HERE / 'plan.json').read_text())
    before = {name: sha(ROOT / name) for name in plan['files_sha256']}
    assert before == plan['files_sha256']
    assert all(os.environ.get(n) == '1' for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'))
    output = ROOT / plan['output_directory']
    assert not output.exists() and not output.is_symlink()
    output.mkdir()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('240s volume diagnostic')))
    signal.alarm(240)
    resource.setrlimit(resource.RLIMIT_CPU, (220, 230))
    report = dict(schema='same-native-Solid-volume-overloads-1', status='incomplete',
                  source_sha256=sha(__file__), plan_sha256=plan_hash, sources_before=before, Gmsh_imported=False,
                  mesh_generated=False, FEA_executed=False, threshold_changed=False,
                  absence_of_import_healing_proved=False, candidate_qualified=False)
    try:
        closure = json.loads((ROOT / plan['Gmsh_root_closure']).read_text())
        observed = json.loads((ROOT / plan['Gmsh_import_receipt']).read_text())
        assert closure['group_closed'] and closure['all_pins_equal']
        assert closure['actual_tool_and_child_returncode'] == 1
        assert closure['status'] == 'actual_import_volume_comparison_refused_before_mesh_generate'
        assert closure['BREP_import'] == observed and observed['passed'] is False
        assert observed['BREP_sha256'] == before[plan['master_BREP']]
        authority = json.loads((ROOT / plan['native_volume_authority']).read_text())
        native_reference = authority['native_BREP']['material_solid_volume_mm3']
        assert native_reference == observed['native_master_volume_mm3']
        sys.path.insert(0, str(ROOT / plan['native_site']))
        import OCP
        from OCP.BRep import BRep_Builder
        from OCP.BRepTools import BRepTools
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopoDS import TopoDS_Shape, TopoDS
        from OCP.TopAbs import TopAbs_SOLID
        from OCP.TopExp import TopExp_Explorer
        from OCP.BRepCheck import BRepCheck_Analyzer
        assert 'gmsh' not in sys.modules
        runtime = dict(python=sys.version, OCP_file=str(Path(OCP.__file__).resolve()),
                       OCP_version=getattr(OCP, '__version__', None))
        write(output / 'runtime-before.json', runtime)
        raw = TopoDS_Shape()
        BRepTools.Read_s(raw, str(ROOT / plan['master_BREP']), BRep_Builder())
        assert not raw.IsNull() and raw.ShapeType() == TopAbs_SOLID
        explorer = TopExp_Explorer(raw, TopAbs_SOLID)
        solids = []
        while explorer.More():
            solids.append(TopoDS.Solid_s(explorer.Current()))
            explorer.Next()
        assert len(solids) == 1 and solids[0].IsSame(raw)
        solid = solids[0]
        assert BRepCheck_Analyzer(solid).IsValid()
        rows = compare(evaluate(solid, BRepGProp, GProp_GProps), observed['OCC_imported_volume_mm3'])
        assert solid.IsSame(raw) and BRepCheck_Analyzer(solid).IsValid()
        adaptive = rows[2]['signed_mass_mm3']
        report.update(status='three_overloads_measured_no_import_identity_claim', methods=rows,
                      one_reloaded_valid_native_Solid=True, same_Solid_native_identity=True,
                      closed_Gmsh_getMass_mm3=observed['OCC_imported_volume_mm3'],
                      closed_native_adaptive_reference_mm3=native_reference,
                      adaptive_exact_binary64_equal_to_closed_reference=adaptive == native_reference,
                      adaptive_signed_delta_vs_closed_reference_mm3=adaptive - native_reference,
                      OnlyClosed_boolean_mass_exactly_equal=rows[0]['signed_mass_mm3'] == rows[1]['signed_mass_mm3'],
                      interpretation='Numeric comparison of three integration overloads on the SAME native BREP. Actual Gmsh import options were not captured; no absence of healing or imported-geometry identity is inferred.')
        runtime_after = dict(python=sys.version, OCP_file=str(Path(OCP.__file__).resolve()),
                             OCP_version=getattr(OCP, '__version__', None))
        assert runtime == runtime_after and 'gmsh' not in sys.modules
        write(output / 'runtime-after.json', runtime_after)
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        after = {name: sha(ROOT / name) for name in before}
        intact = before == after and sha(HERE / 'plan.json') == plan_hash
        report.update(sources_after=after, sources_unchanged=intact,
                      elapsed_seconds=time.monotonic()-started,
                      maximum_RSS_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if not intact:
            report['status'] = 'refused_input_drift'
        write(output / 'assessment.json', report)
    print(json.dumps(dict(status=report['status'], assessment_sha256=sha(output / 'assessment.json'))), flush=True)
    return 0 if report['status'] == 'three_overloads_measured_no_import_identity_claim' and report['sources_unchanged'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
