"""One measured local halving; retain the frozen mesh writer, bore groups and checks."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil

SOURCE=Path(__file__).resolve().parent
SIMULATION=SOURCE.parent/'bionic-20261011/simulate.py'
SIMULATION_SHA256='87be70c955e2532255fdee37cf3a686d970cb421bc9bf6094ca867f1f3098e77'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_size(x,y,z,lc,regions,factor):
    """Restore the original [2,8] clamp before applying a local prescription.

    Gmsh calls the callback before its global clamp and factor. Set its minimum
    to zero, then retain this explicit original clamp everywhere outside the
    declared transition bands. The existing curvature calculation is preserved.
    """
    original=min(8.,max(2.,lc));answer=original
    for region in regions:
        lo,hi=region['bounds_mm'];point=(x,y,z)
        distance=math.sqrt(sum(max(a-p,0.,p-b)**2 for p,a,b in zip(point,lo,hi)))
        band=8*factor  # One original global maximum edge size; no distant field.
        if distance<band:
            t=distance/band;smooth=t*t*(3-2*t)
            target=region['target_h_mm']/factor
            answer=min(answer,target+(original-target)*smooth)
    return answer


def mesh(folder,reference_mesh,spec_path,output,expected_step_sha256):
    import gmsh
    import numpy as np
    folder,reference_mesh,spec_path,output=map(Path,(folder,reference_mesh,spec_path,output))
    assert not output.exists() and sha(SIMULATION)==SIMULATION_SHA256
    assert sha(folder/'carrier.step')==expected_step_sha256
    spec=json.loads(spec_path.read_text());reference=json.loads((reference_mesh/'mesh.json').read_text())
    assert spec['candidate_STEP_sha256']==reference['STEP_sha256']==expected_step_sha256
    assert spec['reference_mesh_inp_sha256']==sha(reference_mesh/'mesh.inp')
    assert spec['single_local_size_ratio']==.5 and reference['global_mesh_size_factor']==7/8
    regions=spec['regions'];assert regions
    for region in regions:
        lo,hi=region['bounds_mm']
        assert len(lo)==len(hi)==3 and all(math.isfinite(v) for v in lo+hi)
        assert all(a<b for a,b in zip(lo,hi))
        assert 0<region['target_h_mm']==.5*region['measured_reference_h_mm']<2*(7/8)
    geometry=json.loads((folder/'geometry.json').read_text())
    protected=json.loads((folder/'protected-interfaces.json').read_text())
    assert geometry['CAD_valid'] and geometry['solid_count']==1 and geometry['dense_reference_mass_kg']<=1.30
    assert abs(geometry['STEP_readback_relative_volume_difference'])<=1e-8
    assert protected['candidate_STEP_sha256']==expected_step_sha256
    assert protected['central_pad_symmetric_difference_mm3']==0
    assert len(protected['end_interface_symmetric_difference_mm3'])==6
    assert not any(protected['end_interface_symmetric_difference_mm3'].values())
    assert protected['study_assembly_screen_pass']
    output.mkdir(parents=True)
    for name in ('carrier.step','geometry.json','study.json','protected-interfaces.json'):
        shutil.copyfile(folder/name,output/name)
    shutil.copyfile(__file__,output/'local-mesh-source.py')
    shutil.copyfile(SIMULATION,output/'frozen-simulation-source.py')
    shutil.copyfile(spec_path,output/'local-mesh-spec.json')
    module_spec=importlib.util.spec_from_file_location('frozen_carrier_simulation',SIMULATION)
    simulation=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(simulation)
    original_generate=gmsh.model.mesh.generate
    def generate(dim):
        gmsh.option.setNumber('Mesh.MeshSizeMin',0)
        gmsh.model.mesh.setSizeCallback(lambda dim,tag,x,y,z,lc:local_size(x,y,z,lc,regions,7/8))
        result=original_generate(dim)
        # Retain actual facet-to-CAD identities for the same fixed sections.
        import sys
        sys.path.insert(0,str(SOURCE))
        from mesh_root_entities import capture
        capture(output/'mesh-7',spec)
        return result
    try:
        # Only inject a sizing callback immediately before the unchanged writer
        # generates its mesh; its groups, positive Jacobian and volume checks run.
        gmsh.model.mesh.generate=generate
        result=simulation.mesh(output,7)
    finally:
        gmsh.model.mesh.generate=original_generate
    meta=json.loads((result/'mesh.json').read_text())
    with np.load(result/'mesh.npz',allow_pickle=False) as current,np.load(reference_mesh/'mesh.npz',allow_pickle=False) as before:
        checks={}
        for label in ('bolt0','bolt1','bolt2','bolt3','end0','end1'):
            points=current['xyz'][np.searchsorted(current['tags'],current[label])]
            old=before['xyz'][np.searchsorted(before['tags'],before[label])]
            sort=lambda values:values[np.lexsort((values[:,2],values[:,1],values[:,0]))]
            equal=points.shape==old.shape and np.allclose(sort(points),sort(old),atol=1e-10,rtol=0)
            checks[label]={'reference_nodes':len(old),'refined_nodes':len(points),'identical_coordinates_within_serialization_roundoff':bool(equal)}
    report={'source_sha256':sha(__file__),'simulation_source_sha256':sha(SIMULATION),
        'STEP_sha256':expected_step_sha256,'reference_mesh_inp_sha256':sha(reference_mesh/'mesh.inp'),
        'spec_sha256':sha(spec_path),'mesh_inp_sha256':sha(result/'mesh.inp'),
        'group_coordinate_comparison':checks,
        'volume_reference_relative_error':reference['volume_relative_error'],
        'volume_refined_relative_error':meta['volume_relative_error'],
        'volume_error_non_regression':abs(meta['volume_relative_error'])<=abs(reference['volume_relative_error']),
        'sizing_scope':'Original curvature rule and clamp [2,8], factor7/8 outside declared bands; local half-size prescribed inside boxes. Mesh connectivity may change outside a box through meshing propagation.',
        'callback_order_source':'https://gmsh.info/doc/texinfo/#Specifying-mesh-element-sizes',
        'new_load_or_support_definition':False}
    (output/'local-mesh-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    capture_source=SOURCE/'mesh_root_entities.py'
    shutil.copyfile(capture_source,result/'surface-entity-capture-source.py')
    capture_receipt={'source_sha256':sha(capture_source),'local_sizing_source_sha256':sha(__file__),
        'frozen_simulation_source_sha256':sha(SIMULATION),'selection_sha256':sha(spec_path),
        'STEP_sha256':expected_step_sha256,'mesh_inp_sha256':sha(result/'mesh.inp'),
        'surface_entities_npz_sha256':sha(result/'surface-entities.npz'),
        'surface_entities_json_sha256':sha(result/'surface-entities.json'),
        'meshing_parameters_changed':'Only the declared one-half local size callback; frozen groups and checks retained.'}
    (result/'surface-capture-receipt.json').write_text(json.dumps(capture_receipt,indent=2)+'\n')
    assert all(row['identical_coordinates_within_serialization_roundoff'] for row in checks.values()),'Protected bore node coordinate sets changed; do not solve'
    assert report['volume_error_non_regression'],'Refinement increased volume approximation error; retain rejection'
    print(json.dumps(report));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for label in ('folder','reference_mesh','spec','output'):parser.add_argument(label,type=Path)
    parser.add_argument('--expected-step-sha256',required=True)
    args=parser.parse_args();mesh(args.folder,args.reference_mesh,args.spec,args.output,args.expected_step_sha256)
