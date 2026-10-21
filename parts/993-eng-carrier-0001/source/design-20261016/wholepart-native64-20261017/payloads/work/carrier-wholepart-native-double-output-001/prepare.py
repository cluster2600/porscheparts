"""Prepare four fixed wholepart linear CCX states; never execute a solver."""
import ast
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MESH=ROOT/'work/part-workflow/run-001/cad/mesh-9'
SHA={'mesh.inp':'6dae0fa717c2fa3009737efcd81f6f976fba545fe69640afc93b59936f6976d5',
     'mesh.npz':'b156b03ab99f65e534a024a63f9cec12529ce9eb6392b0579bf2c20f857a5119'}
ALPHA=9e-6
T0=300.
AMPLITUDE=1e-4
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path,value):
    with Path(path).open('x')as s:json.dump(value,s,indent=2,allow_nan=False);s.write('\n')


def model(path):
    nodes={};cells={};mode=None
    for line in Path(path).read_text().splitlines():
        if line.startswith('*'):
            mode='nodes'if line.upper().startswith('*NODE')else'cells'if line.upper().startswith('*ELEMENT')else None
            if mode=='cells'and 'C3D10'not in line.upper():raise ValueError('Only unchanged C3D10 cells are allowed')
        elif line.strip()and mode:
            row=[v.strip()for v in line.split(',')if v.strip()];tag=int(row[0])
            if mode=='nodes':
                if len(row)!=4 or tag in nodes:raise ValueError('Invalid or repeated original node')
                nodes[tag]=tuple(map(float,row[1:]))
                if not all(math.isfinite(v)for v in nodes[tag]):raise ValueError('Nonfinite original node')
            else:
                if len(row)!=11 or tag in cells:raise ValueError('Invalid or repeated original cell')
                cells[tag]=tuple(map(int,row[1:]))
    if not nodes or not cells or any(v not in nodes for row in cells.values()for v in row):raise ValueError('Missing original mesh data')
    return nodes,cells


def bore_sets(path,nodes):
    result={}
    with zipfile.ZipFile(path)as z:
        for name in ('bolt0','bolt1','bolt2','bolt3','end0','end1'):
            data=z.read(name+'.npy')
            if data[:8]!=b'\x93NUMPY\x01\x00':raise ValueError('Unexpected pinned NPY representation')
            length=struct.unpack_from('<H',data,8)[0];header=ast.literal_eval(data[10:10+length].decode())
            if header['descr']!='<i8'or header['fortran_order']or len(header['shape'])!=1:raise ValueError('Unexpected original bore IDs')
            payload=data[10+length:];ids=[v[0]for v in struct.iter_unpack('<q',payload)]
            if len(ids)!=header['shape'][0]or len(set(ids))!=len(ids)or any(v not in nodes for v in ids):raise ValueError('Invalid original bore group')
            result[name]=ids
    return result


def gauges(nodes):
    zmin=min(p[2]for p in nodes.values());clamp=sorted(i for i,p in nodes.items()if p[2]==zmin)
    if len(clamp)<3:raise ValueError('The provisional exact lower plane lacks three nodes')
    a=min(clamp,key=lambda i:(nodes[i][0],nodes[i][1],i));b=max(clamp,key=lambda i:(nodes[i][0],-i))
    def cross(i):
        return ((Q(nodes[b][0])-Q(nodes[a][0]))*(Q(nodes[i][1])-Q(nodes[a][1]))-
                (Q(nodes[b][1])-Q(nodes[a][1]))*(Q(nodes[i][0])-Q(nodes[a][0])))
    c=max(clamp,key=lambda i:(abs(cross(i)),-i));dx=Q(nodes[b][0])-Q(nodes[a][0]);area=cross(c)
    if not dx or not area:raise ValueError('The six gauge equations are not independent on rigid modes')
    # All three lie in the same z plane. After fixing A, By/Bz/Cz determine
    # all rotations because dx_B * (dx_B*dy_C-dy_B*dx_C) is nonzero.
    dofs=[(a,1),(a,2),(a,3),(b,2),(b,3),(c,3)]
    return clamp,dofs,dict(nodes=[a,b,c],exact_rigid_rotation_determinant=str(dx*area),
        provisional_fixture='All original nodes with z exactly equal to mesh zmin; no geometric tolerance and no service-bore anchors',zmin=zmin)


def nset(name,ids):return ['*NSET,NSET='+name]+[','.join(map(str,ids[i:i+12]))for i in range(0,len(ids),12)]


def deck(kind,nodes,clamp,dofs):
    lines=['** Wholepart sensitivity only: equivalent thermal eigenstrain; no LPBF temperature prediction',
        '*INCLUDE,INPUT=mesh.inp','*MATERIAL,NAME=REFERENCE','*ELASTIC','107000.,0.31','*DENSITY','4.42e-9',
        '*EXPANSION,ZERO=300.','9e-6','*SOLID SECTION,ELSET=BODY,MATERIAL=REFERENCE']
    lines+=nset('ALLN',sorted(nodes))+nset('PROVISIONAL_ZMIN',clamp)
    lines+=['*INITIAL CONDITIONS,TYPE=TEMPERATURE','ALLN,300.']
    def step(field,clamped=False,uniform=False):
        lines.extend(['*STEP','*STATIC,SOLVER=SPOOLES','1.,1.','*BOUNDARY,OP=NEW'])
        if clamped:lines.append('PROVISIONAL_ZMIN,1,3,0.')
        else:
            a=nodes[dofs[0][0]];e=ALPHA*((T0-AMPLITUDE/ALPHA)-T0)
            for i,k in dofs:
                value=e*(nodes[i][k-1]-a[k-1])if uniform else 0.
                lines.append('%d,%d,%d,%.17g'%(i,k,k,value))
        lines.append('*TEMPERATURE,OP=NEW')
        if field=='quadratic':lines.append('*INCLUDE,INPUT=quadratic-temperature.inc')
        else:lines.append('ALLN,%.17g'%(T0-AMPLITUDE/ALPHA if field=='uniform'else T0))
        lines.extend(['*NODE PRINT,NSET=ALLN','U,RF','*EL PRINT,ELSET=BODY','S,ENER','*NODE OUTPUT,DOUBLE','U','*END STEP'])
    if kind=='zero':step('zero')
    elif kind=='uniform':step('uniform',uniform=True)
    elif kind=='incompatible-release':step('quadratic',clamped=True);step('quadratic')
    else:raise ValueError('Unknown fixed sensitivity case')
    return '\n'.join(lines)+'\n'


def prepare(output):
    output=Path(output)
    if output.exists()or output.is_symlink():raise FileExistsError('A new prepared directory is required')
    before={n:sha(MESH/n)for n in SHA}
    if before!=SHA:raise ValueError('The exact current mesh changed')
    nodes,cells=model(MESH/'mesh.inp')
    if (len(nodes),len(cells))!=(103534,54149):raise ValueError('Unexpected full current mesh size')
    groups=bore_sets(MESH/'mesh.npz',nodes);clamp,dofs,gauge=gauges(nodes)
    zlo=min(p[2]for p in nodes.values());zhi=max(p[2]for p in nodes.values());height=zhi-zlo
    if height<=0:raise ValueError('No finite construction height')
    output.mkdir(exist_ok=False);shutil.copyfile(MESH/'mesh.inp',output/'mesh.inp')
    with(output/'quadratic-temperature.inc').open('x')as s:
        for i,p in sorted(nodes.items()):s.write('%d,%.17g\n'%(i,T0-AMPLITUDE/ALPHA*((p[2]-zlo)/height)**2))
    zero=deck('zero',nodes,clamp,dofs)
    uniform=deck('uniform',nodes,clamp,dofs)
    incompatible=deck('incompatible-release',nodes,clamp,dofs)
    whole=zero+'** CASE uniform free contraction\n*STEP'+uniform.split('*STEP',1)[1]+'** CASE quadratic provisional fixture then release\n*STEP'+incompatible.split('*STEP',1)[1]
    with(output/'wholepart-release.inp').open('x')as s:s.write(whole)
    after={n:sha(MESH/n)for n in SHA}
    if before!=after or sha(output/'mesh.inp')!=SHA['mesh.inp']:raise ValueError('The original mesh was not preserved')
    report=dict(status='four_wholepart_states_prepared_no_solver_run',mesh_sha256=before,nodes=len(nodes),C3D10=len(cells),mechanical_DOF=3*len(nodes),
        provisional_clamp_nodes=len(clamp),gauges=gauge,gauge_DOF=dofs,original_bore_node_groups=groups,
        uniform_gauge_values='All six DOF explicitly prescribed from u=epsilon*(x-xA), including nonzero By if needed; no rigid-rotation fitting.',zero_stress_reference_temperature_K=T0,constant_expansion_per_K=ALPHA,normalisation_strain=AMPLITUDE,
        incompatible_field='alpha*(T(Z)-300)=-1e-4*((Z-Zmin)/H)^2, isotropic; prescribed equivalent eigenstrain, not an LPBF temperature history',
        expected_total_frame_times=[1.,2.,3.,4.],frame_cases=['zero','uniform','quadratic_provisionally_clamped','quadratic_released'],
        construction_Z_range_mm=[zlo,zhi],target_continuum_Saint_Venant_nonzero_component_exact=str(-2*Q(AMPLITUDE)/Q(height)**2),
        field_interpolation='Nodal samples of a quadratic target; actual integration uses the unchanged CCX element thermal interpolation.',
        constraints_released_in_second_step=True,remaining_constraints='Six pure rigid-mode gauges only; exact determinant nonzero',
        service_loads_or_springs_used=False,physical_print_supports_claimed=False,thermal_equation_solved=False,material_plasticity_used=False,
        all7_supports_required_for_this_provisional_case=False,original_inputs_unchanged=before==after,global_admission=False,
        output_files_sha256={p.name:sha(p)for p in output.iterdir()if p.is_file()},preparer_sha256=sha(__file__))
    write(output/'preparation.json',report);return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();r=prepare(a.output)
    print(json.dumps({k:r[k]for k in ('status','nodes','C3D10','mechanical_DOF','provisional_clamp_nodes')}))
