"""Export sparse fields only after tying a corrected STEP, mesh and solve together."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from corrected_cad import BASE, sha

spec=importlib.util.spec_from_file_location('retained_sparse_transfer',BASE/'native-leap71/prepare.py')
transfer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)
from simulate import elements


def prepare(folder,output):
    folder,output=Path(folder),Path(output)
    geometry=json.loads((folder.parent/'geometry.json').read_text())
    mesh_report=json.loads((folder/'mesh.json').read_text())
    result=json.loads((folder/'combined-rigid-static.json').read_text())
    stl=folder.parent/'carrier.stl';step=folder.parent/'carrier.step'
    if not (sha(stl)==geometry['geometry_sha256']['carrier.stl'] and
            sha(step)==geometry['geometry_sha256']['carrier.step']==mesh_report['STEP_sha256'] and
            sha(folder/'mesh.inp')==result['mesh_sha256'] and
            sha(folder/'combined-rigid-static.inp')==result['input_sha256']):
        raise ValueError('Geometry, mesh and solver identity chain does not match')
    data=np.load(folder/'combined-rigid-static.npz',allow_pickle=False)
    mesh=np.load(folder/'mesh.npz',allow_pickle=False)
    assert np.array_equal(data['tags'],mesh['tags']) and np.array_equal(data['xyz'],mesh['xyz'])
    assert np.isclose(data['VM'].max(),result['integration_point_VM_max_MPa'])
    assert np.isclose(np.linalg.norm(data['displacement'],axis=1).max(),result['displacement_max_mm'])
    E=elements(folder/'mesh.inp');ids=np.array(sorted(E))
    assert np.array_equal(np.unique(data['element_ids']),ids)
    centres=np.array([data['xyz'][np.searchsorted(data['tags'],E[int(e)][:4])].mean(0) for e in ids])
    peaks=np.full(len(ids),-np.inf)
    np.maximum.at(peaks,np.searchsorted(ids,data['element_ids']),data['VM'])
    assert np.isfinite(peaks).all() and (peaks>=0).all()
    u,u_info=transfer.sparse_bins(data['xyz'],data['displacement'],.5)
    vm,vm_info=transfer.sparse_bins(centres,peaks[:,None],.5)
    assert np.isclose(vm_info['stored_peak_magnitude'],data['VM'].max(),rtol=1e-6)
    output.mkdir(parents=True,exist_ok=False)
    fields={'voxel_mm':.5,'geometry_sha256':sha(stl),'STEP_sha256':sha(step),
            'displacement_rows_xyz_ux_uy_uz_mm':u.tolist(),
            'element_peak_rows_xyz_mm_vm_MPa':vm.tolist()}
    (output/'samples.json').write_text(json.dumps(fields,separators=(',',':'),allow_nan=False)+'\n')
    inputs=[stl,step,folder/'mesh.inp',folder/'mesh.npz',folder/'combined-rigid-static.inp',
            folder/'combined-rigid-static.npz',folder/'combined-rigid-static.json']
    report={'geometry_id':geometry['design_id'],'source_frame':'Original solver XYZ in mm; no print transform',
            'solver_case':'4 kN in -Z plus 850 Nm about Y; assumed rigid bore fixture',
            'source_displacement_max_mm':result['displacement_max_mm'],
            'source_integration_point_VM_max_MPa':result['integration_point_VM_max_MPa'],
            'displacement_transfer':u_info,'stress_transfer':vm_info,
            'stress_location':'Element integration-point maximum at corner centroid, then binned; not a tensor/interpolant',
            'empty_bins':'Unknown; never zero stress',
            'collision_rule':'Preserve maximum magnitude and selected displacement direction',
            'new_solver_executed_for_corrected_STEP':True,
            'solver_executed_for_BCC_comparison':False,
            'manufacturing_authorized':False,
            'inputs_sha256':{p.name:sha(p) for p in inputs},'samples_sha256':sha(output/'samples.json')}
    (output/'transfer.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'displacement':u_info,'stress':vm_info}))


if __name__=='__main__':
    prepare(*sys.argv[1:])
