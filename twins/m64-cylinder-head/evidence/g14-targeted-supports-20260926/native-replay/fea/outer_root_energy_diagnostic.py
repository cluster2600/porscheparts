"""Read-only energy diagnostic of the pinned root2 outer minus-z result."""
import argparse
import json
import math
from pathlib import Path
import signal
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SOURCE=REPO/'twins/m64-cylinder-head/source/fourvalve'
sys.path.insert(0,str(SOURCE))
import numpy as np
import g8_pilot as g8
import g9_reference_campaign as g9

CASE=HERE/'candidate-outer-root2-2/native-mac-g14-outer_high_cheeks_extended_root2_p-2'
INP=CASE/'minus_z.inp'; DAT=CASE/'minus_z.dat'
EXTENDED=HERE/'outer-extended-minus-z-energy-v2.json'
EXTENDED_SHA='963be36a393878851baceb0822e28085fe54667f1a73f264a4ff65e05b3c7086'
PINS={
    EXTENDED:EXTENDED_SHA,
    HERE/'outer_energy_diagnostic.py':'d901486a5fdd14d09286fb8e15597b44870cdb7cc4a1e819d43bad53ff653958',
    INP:'752a4706a8397baad4d2f1734568c562b9a8c911724786d0f74c1159b5eb5f1f',
    DAT:'a7193fff941a4992ebb0463ed565316ba73e9d70c2e1c215a8bef516b15c514f',
    CASE/'case.json':'b87a9d83c78d2ae9e86118efa003bfbffbe1ca6be3f7a5765eb88564d9697616',
    CASE.parent/'summary.json':'6d717fac6cbce6ced07f321aab7ee32665749a5d0f10d37056077ad9a5e4a189',
    g8.BASELINE:'7e93be79ce379f2c4ccf26a6c129a70a093be368a2ff1f168884acc03764842e',
    SOURCE/'g8_pilot.py':'f6f3d1fe77c0a701bb1f75926cd4ac8cba3ee6cc9c3337967740d30ad85fee92',
    SOURCE/'g9_reference_campaign.py':'ed6a2b21d89030ba39fc393f8a218bbbf328eceda49ce6bed361273bd2d8170b',
    REPO/'twins/reference-917-engine/source/run_f37_carrier_calculix.py':'54e3478e219875872092cacb281dd12e640126cbed9273e8d82cd46d36fa2b13',
    REPO/'work/m64-g13/native-ccx/CalculiX/ccx_2.21/src/gauss.f':'aed2d48b6a63e30894e747a531f6edc32e3cd921338e370902dfb62d8e304df2',
    REPO/'work/m64-g13/native-ccx/CalculiX/ccx_2.21/src/shape10tet.f':'04b93f4f9cede954cc82fdfead173c84316471bfd7ffd01b6336c1647cc6644c',
}
E,NU=70000.,.33
BALANCE_LIMIT=1e-4  # Announced before reading the energy outcome; no renormalization.
MIDPOINT_LIMIT_MM=1e-7
EDGES=((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
BETA=.138196601125011; ALPHA=.585410196624968
BARY=np.full((4,4),BETA); np.fill_diagonal(BARY,ALPHA)


def fingerprints():
    got={str(path.relative_to(REPO)):g8.sha256(path) for path in PINS}
    if any(got[str(path.relative_to(REPO))]!=sha for path,sha in PINS.items()):
        raise ValueError('pinned retained input or helper changed')
    return got


def geometry(text,points):
    elements={}; active=False; blocks=0
    for line in text.splitlines():
        if line.startswith('*'):
            active=line=='*ELEMENT,TYPE=C3D10,ELSET=EALL'
            blocks+=int(active)
        elif active and line.strip():
            row=list(map(int,line.split(',')))
            if len(row)!=11 or row[0] in elements or len(set(row[1:]))!=10:
                raise ValueError('invalid or duplicate C3D10 connectivity')
            elements[row[0]]=row[1:]
    if blocks!=1 or not elements:raise ValueError('one C3D10 block required')
    xyz=np.array([[points[n] for n in nodes] for nodes in elements.values()])
    return elements,*tetra_geometry(xyz)


def tetra_geometry(xyz):
    if xyz.ndim!=3 or xyz.shape[1:]!=(10,3) or not np.isfinite(xyz).all():raise ValueError('invalid coordinates')
    mids=np.array([(xyz[:,a]+xyz[:,b])/2 for a,b in EDGES]).transpose(1,0,2)
    error=float(np.max(np.linalg.norm(xyz[:,4:]-mids,axis=2)))
    if error>MIDPOINT_LIMIT_MM:raise ValueError('curved/non-midpoint C3D10; affine quadrature not applicable')
    corners=xyz[:,:4]
    determinant=np.linalg.det((corners[:,1:]-corners[:,0,None,:]).transpose(0,2,1))
    if not np.isfinite(determinant).all() or np.any(determinant<=0):raise ValueError('nonpositive Jacobian')
    positions=np.einsum('ij,ejk->eik',BARY,corners)
    return determinant/6,positions,error


def stress_gp(path,elements):
    index={n:i for i,n in enumerate(elements)}
    stresses=np.empty((len(elements),4,6)); seen=np.zeros((len(elements),4),dtype=bool)
    active=False; blocks=0
    with path.open() as stream:
        for line in stream:
            if 'stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz)' in line:
                active=True; blocks+=1; continue
            if 'displacements (' in line:active=False
            if not active or not line.strip():continue
            fields=line.split()
            if len(fields)!=8:raise ValueError('unexpected stress row')
            n,ip=map(int,fields[:2])
            if n not in index or ip not in (1,2,3,4) or seen[index[n],ip-1]:raise ValueError('unexpected/duplicate integration point')
            stresses[index[n],ip-1]=list(map(float,fields[2:]));seen[index[n],ip-1]=True
    if blocks!=1 or not seen.all() or not np.isfinite(stresses).all():raise ValueError('incomplete/nonfinite Gauss stress')
    return stresses


def density(stress):
    stress=np.asarray(stress,dtype=float)
    if stress.shape[-1]!=6 or not np.isfinite(stress).all():raise ValueError('six finite tensor components required')
    square=np.sum(stress[...,:3]**2,axis=-1)+2*np.sum(stress[...,3:]**2,axis=-1)
    result=((1+NU)*square-NU*np.sum(stress[...,:3],axis=-1)**2)/(2*E)
    if np.any(result<0):raise ValueError('negative isotropic strain energy')
    return result


def balance(integrated,work):
    if not all(math.isfinite(v) and v>0 for v in (integrated,work)):raise ValueError('positive finite total energies required')
    error=abs(integrated-work)/work
    return dict(integrated_stress_energy_Nmm=integrated,half_F_dot_U_Nmm=work,
                relative_difference=error,relative_limit=BALANCE_LIMIT,passed=error<=BALANCE_LIMIT)


def run(output):
    if output.exists() or output.parent.resolve()!=HERE:raise ValueError('new private output beside script required')
    source_sha=g8.sha256(Path(__file__));before=fingerprints();receipt=json.loads((CASE/'case.json').read_text())
    if receipt['numerically_qualified'] is not True or receipt['complete'] is not True or receipt['backend']!='cpu':raise ValueError('qualified retained CPU case required')
    if any(receipt['hashes'].get(p.name)!=PINS[p] for p in (INP,DAT)):raise ValueError('case artifact identity mismatch')
    text=INP.read_text();points,loads,support=g9.deck(text)
    if text.count('*ELASTIC\n70000.0,0.33\n')!=1 or (g8.E,g8.NU)!=(E,NU):raise ValueError('generic isotropic material differs')
    elements,volumes,positions,midpoint_error=geometry(text,points)
    stress=stress_gp(DAT,elements);u=g8.vectors(DAT,'displacements (')
    if set(u)!=set(points) or not np.isfinite(list(u.values())).all():raise ValueError('incomplete/nonfinite U')
    if any(np.linalg.norm(u[n])>1e-12 for n in support):raise ValueError('nonzero support displacement')
    work=.5*math.fsum(f*u[n][d-1] for (n,d),f in loads.items())
    contribution=density(stress)*volumes[:,None]/4
    integrated=float(np.sum(contribution));check=balance(integrated,work)
    regions=None
    z0=json.loads(g8.BASELINE.read_text())['values']['carrier_face_height']
    if check['passed']:
        # Region boundaries classify GP coordinates, not exact clipped volumes.
        edges=[z0+1,z0+3,108.,123.,138.]
        labels=['first_1mm','root_1_to_3mm','lower_to_z108','z108_to123','z123_to138','z138_up']
        bands=np.searchsorted(edges,positions[:,:,2],side='right')
        weights=np.broadcast_to(volumes[:,None]/4,contribution.shape);regions=[]
        for band,label in enumerate(labels):
            for side in ('intake_half','exhaust_half'):
                for zone in ('local_y_below45','frame_y_atleast45'):
                    mask=(bands==band)&((positions[:,:,0]<0)==(side=='intake_half'))&((positions[:,:,1]<45)==(zone=='local_y_below45'))
                    energy=float(np.sum(contribution[mask]));volume=float(np.sum(weights[mask]))
                    regions.append(dict(z_band=label,side=side,zone=zone,energy_Nmm=energy,energy_fraction=energy/integrated,
                        quadrature_volume_mm3=volume,volume_fraction=volume/float(np.sum(volumes)),Gauss_points=int(mask.sum())))
    prior=json.loads(EXTENDED.read_text())
    after=fingerprints()
    if after!=before or g8.sha256(Path(__file__))!=source_sha:raise ValueError('retained input or diagnostic changed during read-only integration')
    result=dict(classification='retained_linear_isotropic_C3D10_energy_diagnostic_not_optimization',source_sha256=source_sha,
        input_hashes_before=before,input_hashes_after=after,inputs_unchanged=True,material=dict(E_MPa=E,nu=NU),
        elements=len(elements),Gauss_points=int(stress.shape[0]*4),maximum_mid_edge_error_mm=midpoint_error,
        mesh_volume_mm3=float(np.sum(volumes)),CAD_volume_mm3=receipt['volume_mm3'],balance=check,
        region_interpretation_permitted=check['passed'],regions=regions,
        region_definition=dict(z_boundaries_mm=[z0,z0+1,z0+3,108,123,138],frame_y_min_mm=45,side_split_x_mm=0),
        scope='Energy/compliance for retained minus-z load only; GP-based region allocation, no exact clipped-volume integration, no exact sensitivity of journal norm, no causal gain prediction, no hot/material/assembly validation.',
        new_solve_executed=False,new_CAD_executed=False,manufacturing_authorized=False)
    if prior['balance']['passed'] is not True or prior['region_definition']!=result['region_definition'] or prior['material']!=result['material']:
        raise ValueError('extended comparison gate or regional definition differs')
    result['comparison_to_extended']=dict(energy_receipt_sha256=EXTENDED_SHA,permitted=check['passed'])
    if check['passed']:
        old_energy=prior['balance']['integrated_stress_energy_Nmm']
        previous={(r['z_band'],r['side'],r['zone']):r for r in prior['regions']}
        result['comparison_to_extended'].update(global_energy_change_fraction=integrated/old_energy-1,
            regions=[dict(z_band=r['z_band'],side=r['side'],zone=r['zone'],
                energy_change_Nmm=r['energy_Nmm']-previous[r['z_band'],r['side'],r['zone']]['energy_Nmm'],
                energy_fraction_change=r['energy_fraction']-previous[r['z_band'],r['side'],r['zone']]['energy_fraction'])
                for r in regions])
    with output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'output':str(output.relative_to(REPO)),'sha256':g8.sha256(output),'balance':check}))
    return 0 if check['passed'] else 2


if __name__=='__main__':
    def stop(signum,frame):raise TimeoutError('read-only energy audit timebox')
    signal.signal(signal.SIGALRM,stop);signal.signal(signal.SIGTERM,stop);signal.alarm(180)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().output))
