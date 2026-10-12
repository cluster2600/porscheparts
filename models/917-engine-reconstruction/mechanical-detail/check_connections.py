#!/usr/bin/env python3
"""Finite triangle Booleans at the cold candidate connections; no sealing qualification."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'head-bionic'))
import study
import trimesh
from reconstruct import save,sha256


def run(directory):
    assembly=json.loads((directory/'assembly.json').read_text());checks=[];loaded={}
    def mesh(row):
        name=row['family'];path=directory/'pieces'/(name+'.stl')
        if name not in loaded:loaded[name]=trimesh.load_mesh(path,process=True)
        m=loaded[name].copy();m.apply_transform(row['matrix_mm']);return m
    for bank in (-1,1):
        def row(name):return next(r for r in assembly['instances'] if r['family']==name and r.get('bank')==bank)
        suffix='negative' if bank<0 else 'positive'
        throttle=row('throttle');intake=row('intake_'+suffix);charge=row('charge_pipe_'+suffix)
        tanks=[r for r in assembly['instances'] if r['family']=='intercooler_tank' and r['bank']==bank]
        right=max(tanks,key=lambda r:r['matrix_mm'][0][0]);left=min(tanks,key=lambda r:r['matrix_mm'][0][0])
        turbo=row('turbo_compressor_housing')
        for label,a,b in [('return_throttle',intake,throttle),('outlet_throttle',right,throttle),('inlet_charge',left,charge),('turbo_charge',turbo,charge)]:
            hit=study.contact(mesh(a),mesh(b));checks.append({'bank':bank,'connection':label,'intersection_mm3':hit['volume_mm3'],'passed':hit['volume_mm3']==0})
        for label,point,wanted in [('manifold_end_cap',[375,bank*310,155],1),('manifold_return_bore',[350,bank*310,150],0)]:
            probe=trimesh.creation.box(extents=[1,1,1]);probe.apply_translation(point)
            hit=study.contact(mesh(intake),probe)
            checks.append({'bank':bank,'connection':label,'intersection_mm3':hit['volume_mm3'],'expected_mm3':wanted,'passed':abs(hit['volume_mm3']-wanted)<1e-6})
    result={'checks':checks,'passed':all(r['passed'] for r in checks),'source_sha256':sha256(HERE/'check_connections.py'),
            'pressure_sealing_qualified':False,'manufacturing_authorized':False,'engine_start_authorized':False}
    save(directory/'connection-checks.json',result)
    if not result['passed']:raise ValueError('Cold connection overlaps rejected')
    return result


if __name__=='__main__':print(json.dumps(run(Path(sys.argv[1])),indent=2))
