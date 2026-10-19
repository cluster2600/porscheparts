"""Stdlib integrity of the actual CAD-point picture; no CAD import or renderer."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    files=json.loads((HERE/'manifest.json').read_text())['files_sha256']
    actual={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p!=HERE/'manifest.json'}
    if actual!=set(files)or any(sha(HERE/p)!=h for p,h in files.items()):raise ValueError('Capsule file set or full SHA differs')
    provenance=json.loads((HERE/'source-provenance.json').read_text())
    if any(files[n]!=r['copied_sha256']or r['source_sha256']!=r['copied_sha256']for n,r in provenance.items()):raise ValueError('A byte-identical copy differs')
    spec=importlib.util.spec_from_file_location('_pure_actual_R1_picture',HERE/'figure.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    data=json.loads((HERE/'data-001/section-data.json').read_text());m.check(data)
    native=json.loads((HERE/'evidence/native-prototype-assessment.json').read_text())
    if (files['evidence/native-prototype-assessment.json']!='403d77960c019c367bec96adee0078f519fda98623b2468e2c5d33fee3219b25'
            or native['status']!='refused' or native['failure']['message']!='STEP readback removed material'
            or native['old_minus_new_native_empty']is not True or native['radius_mm']!=1. or data['radius_mm']!=1.
            or native['new_minus_old_volume_mm3']!=data['native_added_volume_mm3']):raise ValueError('Native prototype and refused exchange scope differ')
    parents=data['source_sha256']
    if (parents['work/part-workflow/run-001/cad/carrier.step']!=native['baseline_STEP_sha256']
            or parents['work/carrier-process-20261017/bounded-webs-cap-rib-contour1-prototype-002/output-001/candidate-native.brep']!=native['outputs_sha256']['candidate-native.brep']):
        raise ValueError('The real parent CAD bindings differ')
    for folder in ['export-execution-001','render-execution-001']:
        receipt=json.loads((HERE/folder/'execution-receipt.json').read_text())
        if not(receipt['actual_returncode']==0 and receipt['direct_child_reaped']is True and receipt['no_non_zombie_group_members']is True
                and receipt['sources_and_plan_unchanged']is True and not receipt['signals_to_owned_group_only']):raise ValueError('Actual work execution was not successfully closed')
    extraction=json.loads((HERE/'data-001/extraction-receipt.json').read_text())
    render=json.loads((HERE/'render-001/render-receipt.json').read_text())
    if (extraction['data_sha256']!=files['data-001/section-data.json']or extraction['sources_before']!=extraction['sources_after']
            or render['data_sha256']!=files['data-001/section-data.json']or render['source_sha256']!=files['figure.py']):raise ValueError('Actual data/source identity differs')
    for n,h in render['outputs_sha256'].items():
        if files['render-001/'+n]!=h:raise ValueError('An actual export differs')
    print(json.dumps(dict(status='portable_native_CAD_point_picture_capsule_verified',payloads=len(files),
        source_points=[sum(len(e['points_xyz_mm'])for e in s['edges'])for s in data['sections']],
        native_parent_CAD_included=False,portable_scope='render_of_already_extracted_actual_points',STEP_exchange_remains_refused=True,global_admission=False)))
if __name__=='__main__':main()
