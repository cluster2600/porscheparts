#!/usr/bin/env python3
"""Independent pure-bending witness before comparing rotor element formulations.

This synthetic rectangular beam has nu=0 and exact end traction M*z/I.
Its small-strain displacement is u_x=M*x*z/(E*I), u_z=-M*x*x/(2*E*I).
It is a solver/formulation diagnostic, not a fan material or load case.
"""
import argparse
import hashlib
import json
from pathlib import Path
import math


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def beam(nx, ny, nz, element):
    if element not in ('C3D8', 'C3D8I') or any(type(n) is not int or not 1 <= n <= 64 for n in (nx,ny,nz)):
        raise ValueError('Bounded structured witness and explicit element formulation required')
    length, width, height, young, moment = 40., 4., 2., 70000., 1.
    inertia = width*height**3/12
    xyz = {}; cells = []
    def tag(i,j,k): return 1+(i*(ny+1)+j)*(nz+1)+k
    for i in range(nx+1):
        for j in range(ny+1):
            for k in range(nz+1):
                xyz[tag(i,j,k)] = (length*i/nx, width*(j/ny-.5), height*(k/nz-.5))
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cells.append([tag(i,j,k),tag(i+1,j,k),tag(i+1,j+1,k),tag(i,j+1,k),
                              tag(i,j,k+1),tag(i+1,j,k+1),tag(i+1,j+1,k+1),tag(i,j+1,k+1)])
    # Integrate linear end traction against the bilinear face shape functions.
    # Each y shape integrates to dy/2; each z shape gives dz*(2*z_i+z_other)/6.
    loads = {}
    for j in range(ny):
        for k in range(nz):
            for jj in (j,j+1):
                for kk in (k,k+1):
                    node = tag(nx,jj,kk); other = tag(nx,jj,2*k+1-kk)
                    force = moment/inertia*(width/ny)*(height/nz)*(2*xyz[node][2]+xyz[other][2])/12
                    loads[node] = loads.get(node,0.)+force
    net = sum(loads.values()); applied_moment = sum(xyz[n][2]*f for n,f in loads.items())
    if abs(net) > 1e-12 or abs(applied_moment-moment) > 1e-12:
        raise ValueError('Independent force and moment check failed')
    fixed = [tag(0,j,k) for j in range(ny+1) for k in range(nz+1)]
    lines = ['*HEADING','Synthetic nu=0 pure bending; N-mm-MPa; not a fan case','*NODE']
    lines += [f'{n},{x:.14g},{y:.14g},{z:.14g}' for n,(x,y,z) in xyz.items()]
    lines += [f'*ELEMENT,TYPE={element},ELSET=BEAM']
    lines += [','.join(map(str,[i+1,*c])) for i,c in enumerate(cells)]
    lines += ['*NSET,NSET=FIXED',','.join(map(str,fixed)), '*NSET,NSET=NALL,GENERATE',f'1,{len(xyz)},1',
              '*MATERIAL,NAME=WITNESS','*ELASTIC',f'{young},0', '*SOLID SECTION,ELSET=BEAM,MATERIAL=WITNESS',
              '*BOUNDARY','FIXED,1,3,0','*STEP','*STATIC','*CLOAD']
    lines += [f'{n},1,{f:.14g}' for n,f in sorted(loads.items()) if f != 0]
    lines += ['*NODE PRINT,NSET=FIXED','RF','*NODE PRINT,NSET=NALL','U','*END STEP']
    case = dict(schema='935-pure-bending-witness-v1', element=element, divisions=[nx,ny,nz],
                nodes=len(xyz),elements=len(cells),length_mm=length,width_mm=width,height_mm=height,
                young_MPa=young,poisson_ratio=0.,end_moment_Nmm=moment,
                section_I_mm4=inertia,exact_tip_uz_mm=-moment*length**2/(2*young*inertia),
                applied_force_N=net,applied_moment_y_Nmm=applied_moment,
                maximum_relative_displacement_error_limit=.01,
                exact_field='ux=M*x*z/(E*I), uy=0, uz=-M*x*x/(2*E*I)',
                geometry_only_witness=True,rotor_validated=False,manufacturing_authorized=False)
    return '\n'.join(lines)+'\n', case, xyz, fixed


def prepare(output):
    output = Path(output); output.mkdir(mode=0o700,exist_ok=False)
    rows=[]
    for nx,ny,nz in ((4,1,1),(8,2,1),(16,4,2)):
        for element in ('C3D8','C3D8I'):
            name=f'{element}-{nx}-{ny}-{nz}'; folder=output/name; folder.mkdir()
            text,case,_,_=beam(nx,ny,nz,element)
            (folder/'rotor.inp').write_text(text)
            case['deck_sha256']=sha(folder/'rotor.inp')
            (folder/'case.json').write_text(json.dumps(case,indent=2)+'\n');rows.append(name)
    (output/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')


def assess(prepared, solved):
    prepared,solved=Path(prepared),Path(solved)
    case=json.loads((prepared/'case.json').read_text())
    if (sha(prepared/'rotor.inp') != case['deck_sha256'] or sha(solved/'rotor.inp') != case['deck_sha256']
            or (solved/'ccx.exit').read_text().strip() != '0'):
        raise ValueError('Pinned deck and successful execution required')
    log=(solved/'ccx.log').read_text()
    if 'Job finished' not in log or '*ERROR' in log:
        raise ValueError('Solver completion missing')
    _,expected,xyz,fixed=beam(*case['divisions'],case['element'])
    for key,value in expected.items():
        if case[key] != value: raise ValueError('Witness definition changed')
    values={'U':{},'RF':{}}; active=None
    for line in (solved/'rotor.dat').read_text().splitlines():
        if 'displacements (vx,vy,vz)' in line: active='U';continue
        if 'forces (fx,fy,fz)' in line: active='RF';continue
        row=line.split()
        if active and len(row)==4 and row[0].isdigit():
            node=int(row[0]);vec=list(map(float,row[1:]))
            if node in values[active] or node not in xyz or not all(math.isfinite(v) for v in vec):
                raise ValueError('Invalid or duplicate result')
            values[active][node]=vec
    if set(values['U']) != set(xyz) or set(values['RF']) != set(fixed):
        raise ValueError('Complete displacement and reaction coverage required')
    tip=[u[2] for n,u in values['U'].items() if xyz[n][0]==case['length_mm']]
    measured=sum(tip)/len(tip); exact=case['exact_tip_uz_mm']
    reactions=[sum(v[d] for v in values['RF'].values()) for d in range(3)]
    moment_y=sum(xyz[n][2]*v[0]-xyz[n][0]*v[2] for n,v in values['RF'].items())
    force_error=math.sqrt(sum(v*v for v in reactions))
    moment_error=abs(moment_y+case['end_moment_Nmm'])/case['end_moment_Nmm']
    relative=abs(measured-exact)/abs(exact)
    return dict(case,tip_uz_mean_mm=measured,relative_tip_displacement_error=relative,
                analytical_displacement_pass=relative < case['maximum_relative_displacement_error_limit'],
                reaction_force_error_N=force_error,reaction_moment_relative_error=moment_error,
                equilibrium_pass=force_error < 1e-6 and moment_error < 1e-6,
                result_sha256={name:sha(solved/name) for name in ('rotor.dat','ccx.log')})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('prepare');p.add_argument('new_output',type=Path)
    p=sub.add_parser('assess');p.add_argument('prepared',type=Path);p.add_argument('solved',type=Path)
    args=parser.parse_args()
    if args.operation=='prepare':prepare(args.new_output)
    else:print(json.dumps(assess(args.prepared,args.solved),indent=2))
