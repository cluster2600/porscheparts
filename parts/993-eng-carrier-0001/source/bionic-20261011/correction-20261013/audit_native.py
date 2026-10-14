"""Explicitly normalize raw native surfaces; retain raw files and reject added BCC."""
import json
from pathlib import Path
import sys

from corrected_cad import sha
from inspect_candidate import normalized_mesh, SurfaceGateError


def run(folder):
    folder = Path(folder)
    native = json.loads((folder/'native-results.json').read_text())
    reports = {}
    for name in ('baseline', 'candidate'):
        raw = folder/(name+'.stl')
        assert sha(raw) == native['exports'][name]['sha256']
        try:
            mesh, report = normalized_mesh(raw)
        except SurfaceGateError as error:
            if name == 'baseline':
                raise
            reports[name] = dict(error.report, raw_sha256=sha(raw),
                                 export_accepted=False, normalized_export=None,
                                 reason='Added BCC has disconnected components and exceeds the mass ceiling')
            continue
        assert abs(report['volume_mm3']-report['raw_signed_volume_mm3'])<1e-6
        output = folder/(name+'-normalized.stl')
        payload = mesh.export(file_type='stl')
        if output.exists():
            assert output.read_bytes() == payload, 'Preserve earlier export'
        else:
            output.write_bytes(payload)
        reread, after = normalized_mesh(output)
        assert after['exact_zero_faces_removed'] == 0
        report.update(raw_sha256=sha(raw), normalized_sha256=sha(output),
                      normalized_triangles=len(reread.faces), native_volume_mm3=native['exports'][name]['volume_mm3'],
                      normalized_mesh_nominal_mass_kg=report['volume_mm3']*4.42e-6,
                      no_positive_area_face_removed=True, physical_qualification=False)
        report['export_accepted'] = True
        reports[name] = report
    reports['selection'] = 'Corrected STEP master retained; added BCC rejected above 1.2 kg'
    reports['native_baseline_is_approximation_of_STEP'] = True
    reports['BCC_strength_or_fatigue_solved'] = False
    reports['manufacturing_authorized'] = False
    (folder/'surface-audit.json').write_text(json.dumps(reports, indent=2)+'\n')
    print(json.dumps(reports))


if __name__ == '__main__':
    run(sys.argv[1])
