#!/usr/bin/env python3
"""Export checked native boundary fields, without raw scans or hidden magnification."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from native_boundary import boundary
from prepare_engineering_sensitivities import parse_mesh
from summarize_engineering_sensitivities import displacement_blocks


def export(case,output):
    r=json.load(open(case/'summary.json'))
    for name,digest in r['file_sha256'].items():
        if hashlib.sha256((case/name).read_bytes()).hexdigest()!=digest:raise ValueError('Native field chain changed '+name)
    nodes,elements=parse_mesh((case/'rotor.inp').read_text());tags,triangles=boundary(elements,nodes);fields=displacement_blocks(case/'rotor.frd')
    xyz=np.array([nodes[n] for n in tags]);released=np.array([fields[-1][n] for n in tags]);attached=np.array([fields[0][n] for n in tags])
    if len(fields)!=2 or not all(np.isfinite(v).all() for v in [xyz,released,attached]):raise ValueError('Complete attached and released fields required')
    if output.exists() or output.with_suffix('.json').exists():raise FileExistsError('Preserve existing field receipts')
    np.savez_compressed(output,xyz_mm=xyz,released_displacement_mm=released,attached_displacement_mm=attached,triangles=triangles,solver_node_id=np.array(tags))
    report={'status':'actual_native_boundary_field_bundle','configuration_id':r['assumptions']['configuration_id'],'summary_sha256':hashlib.sha256((case/'summary.json').read_bytes()).hexdigest(),'source_step_sha256':r['assumptions']['source_step_sha256'],'source_deck_sha256':r['file_sha256']['rotor.inp'],'source_field_sha256':r['file_sha256']['rotor.frd'],'field_bundle_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'boundary_nodes':len(tags),'linear_subtriangles':len(triangles),'units':'mm','state':'released_uncalibrated_elastic_contraction','deformation_scale':1,'scan_included':False,'process_calibrated':False,'fabrication_validated':False}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path);a=p.parse_args();export(a.case,a.output)
