"""Compare full C3D4 stress/compliance energy against independent external work."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import time


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--assessment',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150);start=time.monotonic()
    import numpy as np
    summary=json.loads(a.assessment.read_text());preparation=a.preparation/'assessment.json';mesh=a.preparation/'transport.npz';config=json.loads(preparation.read_text())
    if sha(a.results)!=summary['output_sha256']or sha(mesh)not in summary['source_sha256'].values()or sha(preparation)not in summary['source_sha256'].values():raise ValueError('Completed field and preparation identities differ')
    E=float(config['material']['E_MPa']);nu=float(config['material']['nu'])
    if not E>0 or not -1<nu<.5:raise ValueError('Positive isotropic elastic material required')
    def density(stress):
        diagonal=stress[:,:3];shear=stress[:,3:];pairs=diagonal[:,0]*diagonal[:,1]+diagonal[:,1]*diagonal[:,2]+diagonal[:,2]*diagonal[:,0]
        return (np.sum(diagonal*diagonal,axis=1)-2*nu*pairs+2*(1+nu)*np.sum(shear*shear,axis=1))/(2*E)
    controls=[([1,0,0,0,0,0],1/(2*E)),([1,1,1,0,0,0],3*(1-2*nu)/(2*E)),([0,0,0,1,0,0],(1+nu)/E)]
    for state,expected in controls:
        if abs(float(density(np.array([state],dtype=float))[0])/expected-1)>1e-14:raise ValueError('Analytic elastic-energy density control refused')
    with np.load(mesh,allow_pickle=False)as data:v=data['vertices'].copy();cells=data['tetrahedra'].copy()
    with np.load(a.results,allow_pickle=False)as data:stress=data['stress'].copy();displacement=data['displacement'].copy();force=data['force'].copy()
    if stress.shape!=(len(cells),6)or displacement.shape!=v.shape or force.shape!=v.shape:raise ValueError('Whole result rosters differ')
    energy=0.;volume=0.;minimum=None
    for start_index in range(0,len(cells),65536):
        stop=min(start_index+65536,len(cells));points=v[cells[start_index:stop]];edges=points[:,1:]-points[:,0,None];six_volumes=np.sum(edges[:,0]*np.cross(edges[:,1],edges[:,2]),axis=1)
        if not np.all(six_volumes>0):raise ValueError('Nonpositive serialized cell volume')
        local=six_volumes/6;minimum=float(local.min())if minimum is None else min(minimum,float(local.min()));energy+=float(np.dot(local,density(stress[start_index:stop])));volume+=float(local.sum())
    external=float(np.sum(force*displacement));reference=.5*external
    if reference<=0 or not np.isfinite(energy):raise ValueError('Positive finite work required')
    relative=abs(energy-reference)/reference;limit=1e-4;passed=relative<=limit
    report=dict(status='complete_independent_stress_energy_check_passed'if passed else'independent_stress_energy_check_refused',cells=len(cells),stress_rows=len(stress),internal_stress_compliance_energy_Nmm=energy,external_force_displacement_work_Nmm=external,half_external_work_Nmm=reference,relative_energy_residual=relative,fixed_relative_limit=limit,volume_mm3=volume,minimum_serialized_cell_volume_mm3=minimum,material_E_MPa=E,material_nu=nu,analytic_controls=['uniaxial stress','hydrostatic stress','pure shear'],nodal_stress_averaging=False,stress_convergence_demonstrated=False,strength_qualified=False,scope='Exact-in-cell C3D4 constant-stress elastic compliance energy using the complete printed field; accounts for output rounding through the retained fixed relative criterion',source_sha256={str(p):sha(p)for p in [mesh,preparation,a.results,a.assessment,Path(__file__)]},elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps({k:report[k]for k in ['status','cells','relative_energy_residual','fixed_relative_limit']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
