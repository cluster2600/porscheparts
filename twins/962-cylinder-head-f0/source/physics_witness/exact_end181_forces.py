"""Exact Q1 Cartesian HEX8 integration of the retained synthetic coupon state.

Material coefficients and saved data are exact rational interpretations of their
binary64 values. This is an arithmetic diagnostic, not a new material model.
"""
import csv
from fractions import Fraction as F
import hashlib
from itertools import product
import json
from pathlib import Path
import struct
import sys

REPO=Path(__file__).resolve().parents[4]
NATIVE=None
REPORT=REPO/'twins/962-cylinder-head-f0/derived/engineering/rich3-coupon-and-head499-held/originals/rich3-END181-equilibrium-execution-001/diagnostic.json'
MATERIAL=(F(71e9/(2*(1+.33))),F(71e9*.33/((1+.33)*(1-2*.33))),F(1e-5))
H=(F(1,8),F(1,4),F(1,4)); V=H[0]*H[1]*H[2]
CORNERS=list(product((0,1),repeat=3))
FIXED={(0,0),(0,1),(0,2),(32,1),(32,2),(137,2)}
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def mass(a,b):
    return F(1,3) if a==b else F(1,6)

def gradient_product(a,i,b,j):
    value=V*F(2*a[i]-1)/H[i]*F(2*b[j]-1)/H[j]
    for k in range(3):
        value*=F(1) if k==i==j else F(1,2) if k in (i,j) else mass(a[k],b[k])
    return value

def shape_gradient(a,b,i):
    value=V*F(2*a[i]-1)/H[i]/2
    for k in range(3):
        if k!=i:value*=mass(a[k],b[k])
    return value

MU,LAM,ALPHA=MATERIAL
K={};Q={}
for n,a in enumerate(CORNERS):
    for m,b in enumerate(CORNERS):
        for i in range(3):
            Q[n,m,i]=-(2*MU+3*LAM)*ALPHA*shape_gradient(a,b,i)
            for j in range(3):
                K[n,i,m,j]=(MU*sum(gradient_product(a,k,b,k) for k in range(3)) if i==j else 0)+MU*gradient_product(a,j,b,i)+LAM*gradient_product(a,i,b,j)

def cell_forces(u,delta_t):
    return [[sum(K[n,i,m,j]*u[m][j] for m in range(8) for j in range(3))+
             sum(Q[n,m,i]*delta_t[m] for m in range(8)) for i in range(3)] for n in range(8)]

def controls():
    # Uniform free thermal expansion and a rigid translation must produce zero force.
    dt=F(13)
    expansion=[[ALPHA*dt*H[j]*a[j]+F(j+1,7) for j in range(3)] for a in CORNERS]
    assert all(v==0 for row in cell_forces(expansion,[dt]*8) for v in row)
    assert all(K[n,i,m,j]==K[m,j,n,i] for n in range(8) for i in range(3) for m in range(8) for j in range(3))
    # Constant extension and shear have closed-form face tractions.
    eps=F(1,1000000)
    u=[[eps*H[0]*a[0],F(0),F(0)] for a in CORNERS]
    f=cell_forces(u,[F(0)]*8)
    for n,a in enumerate(CORNERS):
        for i in range(3):
            stress=(LAM+2*MU)*eps if i==0 else LAM*eps
            assert f[n][i]==(2*a[i]-1)*(V/H[i])/4*stress
    u=[[eps*H[1]*a[1],F(0),F(0)] for a in CORNERS]
    f=cell_forces(u,[F(0)]*8)
    for n,a in enumerate(CORNERS):
        assert f[n]==[(2*a[1]-1)*(V/H[1])/4*MU*eps,
                      (2*a[0]-1)*(V/H[0])/4*MU*eps,F(0)]


def main(native, output):
    global NATIVE
    NATIVE=Path(native).resolve(strict=True)
    controls()
    native_receipt=json.loads((NATIVE/'native-execution.json').read_text())
    binding=REPO/'twins/962-cylinder-head-f0/derived/engineering/end181-residual-20261107/summary.json'
    expected=json.loads(binding.read_text())['cases']['three_updates']['native_receipt_sha256']
    assert sha((NATIVE/'native-execution.json').read_bytes())==expected
    pins=native_receipt['inputs_and_outputs']['artifact_sha256']; inputs={}
    def nodes(name):
        raw=(NATIVE/name).read_bytes();assert sha(raw)==pins[name]
        inputs[name]=dict(sha256=sha(raw),bytes=len(raw));out={}
        for row in csv.DictReader(raw.decode().splitlines()):
            n=int(row['id']);assert n not in out or out[n]==row;out[n]=row
        return out
    d=json.loads(REPORT.read_text())
    manifest=json.loads((REPORT.parents[2]/'manifest.json').read_text())
    pin=next(x for x in manifest['originals'] if x['copy'].endswith('rich3-END181-equilibrium-execution-001/diagnostic.json'))
    assert sha(REPORT.read_bytes())==pin['sha256']
    geometry={int(n):tuple(F(v) for v in struct.unpack('<ddd',bytes.fromhex(word))) for n,word in d['complete_source_ID_coordinate_binary64_LE_hex'].items()}
    cells=d['complete_ordered_HEX8_cells'];assert len(cells)==256 and len(geometry)==425
    birth=nodes('thermoelastic_begin_0080.csv');reference=nodes('thermoelastic_reference_begin_0080.csv')
    result={}
    for step in (181,182):
        current=nodes(f'thermoelastic_end_{step:04}.csv');forces={n:[F(0)]*3 for n in geometry}
        assert set(current)==set(geometry)
        for n,row in current.items():assert tuple(F(float(row[k])) for k in ('x','y','z'))==geometry[n]
        for cell in cells:
            tags=cell['nodes'];points=[geometry[n] for n in tags]
            lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)]
            assert tuple(hi[j]-lo[j] for j in range(3))==H
            ordered={tuple(int((p[j]-lo[j])/H[j]) for j in range(3)):n for n,p in zip(tags,points)}
            assert set(ordered)==set(CORNERS)
            tags=[ordered[c] for c in CORNERS];born=cell['block']==3
            assert cell['block'] in (2,3)
            u=[[F(float(current[n][k]))-(F(float(birth[n][k])) if born else 0) for k in ('disp_x','disp_y','disp_z')] for n in tags]
            dt=[F(float(current[n]['temperature']))-(F(float(reference[n]['born_reference_temperature'])) if born else F(400)) for n in tags]
            f=cell_forces(u,dt)
            for n,row in zip(tags,f):
                for j in range(3):forces[n][j]+=row[j]
        totals={name:[F(0)]*6 for name in ('free','constrained','all')}
        for n,f in forces.items():
            for i,value in enumerate(f):
                force=[F(0)]*3;force[i]=value;x=geometry[n]
                moment=[x[1]*force[2]-x[2]*force[1],x[2]*force[0]-x[0]*force[2],x[0]*force[1]-x[1]*force[0]]
                for group in ('all','constrained' if (n,i) in FIXED else 'free'):
                    totals[group]=[a+b for a,b in zip(totals[group],force+moment)]
        assert all(v==0 for v in totals['all']), 'Exact global force and moment balance'
        differences=[abs(value-F(float(current[n][('rx','ry','rz')[i]]))) for n,row in forces.items() for i,value in enumerate(row)]
        result[str(step)]={'resultants':{g:[float(v) for v in vs] for g,vs in totals.items()},'maximum_exact_vs_native_nodal_difference':float(max(differences)),
            'maximum_free_exact_force':float(max(abs(v) for n,row in forces.items() for i,v in enumerate(row) if (n,i) not in FIXED)),
            'exact_all_force_and_moment_zero':True,'exact_force_rows':{str(n):[str(v) for v in row] for n,row in forces.items()}}
    out=Path(output)
    data={'scope':'exact arithmetic diagnostic, no solver rerun or engineering acceptance','material_coefficients':{'mu':str(MU),'lambda':str(LAM),'alpha':str(ALPHA)},'source_sha256':sha(Path(__file__).read_bytes()),'report_sha256':sha(REPORT.read_bytes()),'native_receipt_sha256':sha((NATIVE/'native-execution.json').read_bytes()),'inputs':inputs,'python':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'cases':result,'controls_passed':True,'root_cause_accepted':False,'manufacturing_authorized':False}
    with out.open('x') as stream:json.dump(data,stream,indent=2);stream.write('\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='exact_force_rows'} for k,v in result.items()},indent=2))

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
