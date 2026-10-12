#!/usr/bin/env python3
"""Native dense countertrial with the same nominal bores and candidate anchor arms."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
from engine_layout import beam
from detail_audit import audit_native
from reconstruct import save,sha256


def run(directory,dotnet):
    native=directory/'native-0.5';cfg=json.loads((directory/'config.json').read_text())
    source=native/'drive_bionic_frame.stl';receipt=json.loads((native/'receipt.json').read_text())
    if sha256(source)!=receipt['parts']['drive_bionic_frame']['stl_sha256']:raise ValueError('Native frame changed')
    candidate,audit=study.prior.inspect(source,allow_exact_zero=True)
    if not audit['passed']:raise ValueError('Invalid candidate frame')
    adds=[];cuts=[]
    for _,y,z,r in cfg['gear_envelopes']:
        adds.append(beam([408,y,z],[414,y,z],r+7))
        cuts.append(beam([403,y,z],[419,y,z],10 if r<25 or r>40 else 6))
    for sign in (-1,1):cuts.append(beam([375,sign*60,-70],[418,sign*60,-70],3.5))
    part={'id':'drive_frame_dense_reference','source_mesh':{'path':str(source.resolve()),'sha256':sha256(source)},
          'add':adds,'subtract':cuts,'intersect':[]}
    path=directory/'frame-control-recipe.json'
    if path.exists():raise ValueError('Existing countertrial preserved')
    save(path,{'classification':'hypothetical_engine_components_not_manufacturing_geometry','parts':[part]})
    study.command([dotnet,directory/'engine-app/Engine.dll',path,sha256(path),'.5',directory/'frame-control-native'],directory/'frame-control.log')
    meshes,audits=audit_native(directory/'frame-control-native')
    if not all(r['passed'] for r in audits.values()):raise ValueError('Dense countertrial topology rejected')
    dense=meshes['drive_frame_dense_reference'];fraction=1-candidate.volume/dense.volume
    if not 0<fraction<1:raise ValueError('No geometric material saving')
    report={'candidate_volume_mm3':candidate.volume,'dense_reference_volume_mm3':dense.volume,'volume_reduction_fraction':fraction,
            'source_sha256':sha256(HERE/'frame_control.py'),'recipe_sha256':sha256(path),'native_audits':audits,
            'strength_or_fatigue_optimized':False,'material_qualified':False,'manufacturing_authorized':False,'engine_start_authorized':False}
    save(directory/'frame-control.json',report);return report


if __name__=='__main__':print(json.dumps(run(Path(sys.argv[1]).resolve(),sys.argv[2]),indent=2))
