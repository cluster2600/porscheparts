"""Run the unchanged carrier mesher while retaining actual CAD surface entities."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE))
from mesh_local_root import SIMULATION,SIMULATION_SHA256,sha


def capture(output,selection):
    import gmsh
    import numpy as np
    triangles=[];entities=[];triangle_ids=[];records=[]
    for _,tag in gmsh.model.getEntities(2):
        for kind,ids,connectivity in zip(*gmsh.model.mesh.getElements(2,tag)):
            assert kind==9
            nodes=np.asarray(connectivity).reshape(-1,6)[:,:3]
            triangles.extend(nodes);triangle_ids.extend(ids);entities.extend([tag]*len(ids))
        records.append({'entity_tag':tag,'type':gmsh.model.getType(2,tag),
                        'bounds_mm':gmsh.model.getBoundingBox(2,tag)})
    # This is the OCC kernel's existing tolerance, not a new admission tolerance.
    tolerance=gmsh.option.getNumber('Geometry.Tolerance');sections=[]
    for requested in selection['sections']:
        point=np.asarray(requested['point_on_blend_face_mm']);matches=[]
        assert abs(point[0]-requested['plane_X_mm'])<=tolerance
        for record in records:
            bounds=record['bounds_mm']
            if np.any(point<np.array(bounds[:3])-tolerance) or np.any(point>np.array(bounds[3:])+tolerance):continue
            projected,uv=gmsh.model.getClosestPoint(2,record['entity_tag'],point)
            error=float(np.linalg.norm(point-projected))
            if error<=tolerance and gmsh.model.isInside(2,record['entity_tag'],uv,parametric=True):
                matches.append({'entity_tag':record['entity_tag'],'probe_projection_error_mm':error})
        assert len(matches)==1,('Blend probe must identify one trimmed CAD face',requested,matches)
        sections.append({**requested,**matches[0]})
    np.savez_compressed(output/'surface-entities.npz',faces=np.asarray(triangles,dtype=np.int64),
                        triangle_ids=np.asarray(triangle_ids,dtype=np.int64),entity_tags=np.asarray(entities,dtype=np.int64))
    report={'capture_source_sha256':sha(__file__),'gmsh_version':gmsh.__version__,
            'matching_native_geometry_tolerance_mm':tolerance,'entities':records,'sections':sections,
            'matching_scope':'Each interior blend probe is matched to exactly one trimmed imported CAD face before finalization; facets retain their actual generating entity.'}
    (output/'surface-entities.json').write_text(json.dumps(report,indent=2)+'\n')


def mesh(folder,size,selection_path,expected_step_sha256):
    import gmsh
    folder,selection_path=map(Path,(folder,selection_path));selection=json.loads(selection_path.read_text())
    assert size in (7,9) and sha(SIMULATION)==SIMULATION_SHA256
    assert sha(folder/'carrier.step')==selection['candidate_STEP_sha256']==expected_step_sha256
    seam=Path(selection['seam_audit_path'])
    assert sha(seam)==selection['seam_audit_sha256']
    audit=json.loads(seam.read_text())
    assert audit['STEP_sha256']==expected_step_sha256 and audit['new_reentrant_seam_probe_screen_pass']
    geometry=json.loads((folder/'geometry.json').read_text())
    assert geometry['CAD_valid'] and geometry['solid_count']==1 and geometry['dense_reference_mass_kg']<=1.30
    assert abs(geometry['STEP_readback_relative_volume_difference'])<=1e-8
    protected=json.loads((folder/'protected-interfaces.json').read_text())
    assert protected['candidate_STEP_sha256']==expected_step_sha256 and protected['study_assembly_screen_pass']
    assert protected['central_pad_symmetric_difference_mm3']==0 and len(protected['end_interface_symmetric_difference_mm3'])==6
    assert not any(protected['end_interface_symmetric_difference_mm3'].values())
    module_spec=importlib.util.spec_from_file_location('frozen_carrier_mesh_entities',SIMULATION)
    simulation=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(simulation)
    original=gmsh.model.mesh.generate;output=folder/f'mesh-{size}'
    def generate(dim):
        result=original(dim);capture(output,selection);return result
    try:
        gmsh.model.mesh.generate=generate
        result=simulation.mesh(folder,size)
    finally:gmsh.model.mesh.generate=original
    shutil.copyfile(__file__,result/'surface-entity-capture-source.py')
    shutil.copyfile(SIMULATION,result/'frozen-simulation-source.py')
    shutil.copyfile(selection_path,result/'surface-selection.json')
    receipt={'source_sha256':sha(__file__),'frozen_simulation_source_sha256':sha(SIMULATION),
             'sha_helper_source_sha256':sha(SOURCE/'mesh_local_root.py'),
             'selection_sha256':sha(selection_path),'STEP_sha256':expected_step_sha256,
             'mesh_inp_sha256':sha(result/'mesh.inp'),'surface_entities_npz_sha256':sha(result/'surface-entities.npz'),
             'surface_entities_json_sha256':sha(result/'surface-entities.json'),
             'meshing_parameters_changed':False}
    (result/'surface-capture-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('size',type=int,choices=(7,9));parser.add_argument('selection',type=Path)
    parser.add_argument('--expected-step-sha256',required=True)
    args=parser.parse_args();mesh(args.folder,args.size,args.selection,args.expected_step_sha256)
