"""Portable stdlib integrity/edge-scope check; no plotting or mechanical solver."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    manifest=json.loads((HERE/'manifest.json').read_text());files=manifest['files_sha256']
    actual={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.name!='manifest.json'}
    if actual!=set(files)or any(sha(HERE/p)!=h for p,h in files.items()):raise ValueError('Capsule files differ')
    provenance=json.loads((HERE/'source-provenance.json').read_text())
    if any(files[p]!=row['copied_sha256']or row['copied_sha256']!=row['source_sha256']for p,row in provenance.items()):raise ValueError('A byte-identical source copy differs')
    spec=importlib.util.spec_from_file_location('_portable_edge_scope',HERE/'render.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=json.loads((HERE/'data/figure-data.json').read_text())
    terminal=json.loads((HERE/'evidence/H2-root-terminal.json').read_text())
    if terminal['actual_tool_returncode']!=0 or not terminal['pins_unchanged']or terminal['FEA_started']:raise ValueError('Real H2 terminal differs')
    if [m['role']for m in data['meshes']]!=['before','after']or len(data['regions'])!=2:raise ValueError('Two real ordered meshes/regions required')
    counts=[]
    for mesh in data['meshes']:
        for record in mesh['regions']:
            module.check_record(record);counts.append([len(record['selected_cells']),len(record['edges'])])
    after=[r['measured_h_mm']for r in data['meshes'][1]['regions']]
    targets=[r['target_h_mm']for r in data['regions']]
    if after!=terminal['actual_h_mm']or targets!=terminal['fixed_target_h_mm']or not all(h<=t for h,t in zip(after,targets)):raise ValueError('Unrounded real measurements/targets differ')
    if any(r['target_h_mm']!=r['measured_reference_h_mm']/2 for r in data['regions']):raise ValueError('The target is not the initial peak-tetrahedron half-h')
    if data['final_terminal_sha256']!=files['evidence/H2-root-terminal.json']:raise ValueError('Real root binding differs')
    print(json.dumps(dict(status='portable_geometry_figure_capsule_verified',payloads=len(files),counts=counts,unrounded_targets_passed=True,FEA_started=False)))

if __name__=='__main__':main()
