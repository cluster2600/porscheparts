"""Rib-root fillet convergence on the four-rib quarter section; no component qualification.

Runs inside the cadsim image (gmsh and CalculiX 2.21 on PATH). The fillet radii are
design assumptions for the next geometry, not measured or printed values.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
sys.path.insert(0,str(REPO/'models/horizontal-fan-reconstruction/source'))
from summarize_analytical_fem import read_frd
_spec=importlib.util.spec_from_file_location('pressure_coupon_study',ROOT/'source/study.py');STUDY=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(STUDY)
E,NU,PRESSURE=STUDY.E,STUDY.NU,STUDY.PRESSURE
WIDTH,HALF_HEIGHT,WALL,RIB_HALF,SIDE=12.,1.5,.8,.4,11.2
RIBS=4;RADII=[0.,.2,.4];GLOBAL_MM=[.2,.1,.05,.025];LOCAL_MM=[.05,.025,.0125,.00625]
ROOT_CORNERS=[(c+d,HALF_HEIGHT) for c in STUDY.centres(RIBS) for d in (-RIB_HALF,RIB_HALF)]+[(SIDE,HALF_HEIGHT)]
GCI_SAFETY=1.25;CONVERGED_GCI=.05


def channel_edges():
    edges=sorted([-SIDE,SIDE]+[s*c+d for s in (-1,1) for c in STUDY.centres(RIBS) for d in (-RIB_HALF,RIB_HALF)])
    return [(a,b) for a,b in zip(edges[::2],edges[1::2]) if b>0]


def solid_area(radius):
    """Analytical quarter-section area: each concave root corner gains (1-pi/4) r^2."""
    return WIDTH*(HALF_HEIGHT+WALL)-HALF_HEIGHT*sum(b-max(a,0.) for a,b in channel_edges())+len(ROOT_CORNERS)*(1-math.pi/4)*radius*radius


def richardson(values,ratio=2.):
    """Observed order, extrapolated value and fine-grid GCI from the last three levels (Roache)."""
    f1,f2,f3=values[-3:];d1,d2=f2-f1,f3-f2
    if d1==0 or d2==0 or d2/d1<=0 or abs(d2)>=abs(d1):return {'monotone_convergence':False,'successive_difference_ratio':d2/d1 if d1 else None}
    p=math.log(d1/d2)/math.log(ratio);extrapolated=f3+d2/(ratio**p-1);gci=GCI_SAFETY*abs(d2/f3)/(ratio**p-1)
    return {'monotone_convergence':True,'successive_difference_ratio':d2/d1,'observed_order':p,'extrapolated':extrapolated,'gci_fine':gci,'converged_within_gci':gci<CONVERGED_GCI}


def mesh(radius,level):
    import gmsh
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
    try:
        occ=gmsh.model.occ;body=occ.addRectangle(0,0,0,WIDTH,HALF_HEIGHT+WALL)
        # Channels are drawn full height and full width, so only the wall-side corners fall in the quarter.
        tools=[(2,occ.addRectangle(a,-HALF_HEIGHT,0,b-a,2*HALF_HEIGHT,roundedRadius=radius)) for a,b in channel_edges()]
        out,_=occ.cut([(2,body)],tools);occ.synchronize()
        if len(out)!=1:raise ValueError('Quarter section is not one surface')
        surface=out[0][1];area=occ.getMass(2,surface)
        loaded=[]
        for _,curve in gmsh.model.getBoundary(out,oriented=False):
            x0,y0,_,x1,y1,_=gmsh.model.getBoundingBox(1,curve)
            # OCC bounding boxes are padded by the modeling tolerance; 1e-4 mm still separates every face here.
            if not (max(x0,x1)<1e-4 or max(y0,y1)<1e-4 or min(x0,x1)>WIDTH-1e-4 or min(y0,y1)>HALF_HEIGHT+WALL-1e-4):loaded.append(curve)
        field=gmsh.model.mesh.field;points=[occ.addPoint(x,y,0) for x,y in ROOT_CORNERS];occ.synchronize()
        distance=field.add('Distance')
        if radius:field.setNumbers(distance,'CurvesList',[c for c in loaded if gmsh.model.getType(1,c)=='Circle']);field.setNumber(distance,'Sampling',200)
        else:field.setNumbers(distance,'PointsList',points)
        # Subdivision into quadrangles halves the edge length, so sizes are requested at twice the target.
        threshold=field.add('Threshold');field.setNumber(threshold,'InField',distance)
        field.setNumber(threshold,'SizeMin',2*LOCAL_MM[level]);field.setNumber(threshold,'SizeMax',2*GLOBAL_MM[level])
        field.setNumber(threshold,'DistMin',max(radius,.05));field.setNumber(threshold,'DistMax',max(radius,.05)+.6)
        field.setAsBackgroundMesh(threshold)
        for name,value in [('Mesh.MeshSizeExtendFromBoundary',0),('Mesh.MeshSizeFromPoints',0),('Mesh.MeshSizeFromCurvature',0),('Mesh.Algorithm',8),('Mesh.RecombineAll',1),('Mesh.RecombinationAlgorithm',1),('Mesh.SubdivisionAlgorithm',1),('Mesh.SecondOrderIncomplete',1),('Mesh.ElementOrder',2)]:gmsh.option.setNumber(name,value)
        gmsh.model.mesh.generate(2)
        tags,coords,_=gmsh.model.mesh.getNodes(-1,-1,includeBoundary=True)
        nodes={int(t):(float(coords[3*i]),float(coords[3*i+1])) for i,t in enumerate(tags)}
        types,_,connectivity=gmsh.model.mesh.getElements(2,surface)
        if list(types)!=[16]:raise ValueError(f'Expected only 8-node quadrangles, got types {list(types)}')
        flat=[int(n) for n in connectivity[0]];elements=[flat[i:i+8] for i in range(0,len(flat),8)]
        on_load=set()
        for curve in loaded:on_load.update(int(t) for t in gmsh.model.mesh.getNodes(1,curve,includeBoundary=True)[0])
        version=gmsh.__version__
    finally:
        gmsh.finalize()
    for k,e in enumerate(elements):
        (x1,y1),(x2,y2),(x3,y3),(x4,y4)=(nodes[n] for n in e[:4])
        if (x1*y2-x2*y1)+(x2*y3-x3*y2)+(x3*y4-x4*y3)+(x4*y1-x1*y4)<0:elements[k]=[e[0],e[3],e[2],e[1],e[7],e[6],e[5],e[4]]
    count={}
    for e in elements:
        for f in range(4):key=frozenset((e[f],e[(f+1)%4]));count[key]=count.get(key,0)+1
    loads=[(k,f+1) for k,e in enumerate(elements,1) for f in range(4) if count[frozenset((e[f],e[(f+1)%4]))]==1 and {e[f],e[(f+1)%4],e[4+f]}<=on_load]
    used=sorted({n for e in elements for n in e});nodes={n:nodes[n] for n in used}
    return {'nodes':nodes,'elements':elements,'loads':loads,'cad_area_mm2':area,'loaded_curves':len(loaded),'gmsh_version':version}


def resultant(m):
    """Independent pressure resultant from the loaded faces; curved faces enter by their chords, which is exact for uniform pressure."""
    fx=fy=0.
    for tag,face in m['loads']:
        e=m['elements'][tag-1];a=m['nodes'][e[face-1]];c=m['nodes'][e[4+face-1]];b=m['nodes'][e[face%4]]
        for p,q in [(a,c),(c,b)]:fx-=PRESSURE*(q[1]-p[1]);fy+=PRESSURE*(q[0]-p[0])
    return fx,fy


def deck(m):
    lines=['*HEADING','Filleted four-rib coupon quarter-section, mm N MPa','*NODE']+[f'{i},{x:.12g},{y:.12g},0' for i,(x,y) in m['nodes'].items()]
    lines+=['*ELEMENT,TYPE=CPE8,ELSET=BODY']+[','.join(map(str,[k,*e])) for k,e in enumerate(m['elements'],1)]
    xsym=[i for i,(x,y) in m['nodes'].items() if abs(x)<1e-9];ysym=[i for i,(x,y) in m['nodes'].items() if abs(y)<1e-9]
    for name,ids in [('XSYM',xsym),('YSYM',ysym)]:lines+=[f'*NSET,NSET={name}']+[','.join(map(str,ids[i:i+12])) for i in range(0,len(ids),12)]
    lines+=['*MATERIAL,NAME=ASSUMED_HOT_AL','*ELASTIC',f'{E},{NU}','*SOLID SECTION,ELSET=BODY,MATERIAL=ASSUMED_HOT_AL','1','*BOUNDARY','XSYM,1,1','YSYM,2,2','*STEP','*STATIC','*DLOAD']
    lines+=[f'{k},P{face},{PRESSURE}' for k,face in m['loads']]
    lines+=['*NODE FILE,OUTPUT=2D','U','*EL FILE','S','*EL PRINT,ELSET=BODY','S','*NODE PRINT,NSET=XSYM,TOTALS=ONLY','RF','*NODE PRINT,NSET=YSYM,TOTALS=ONLY','RF','*END STEP']
    return '\n'.join(lines)+'\n'


def vm(s):
    x,y,z,xy,yz,zx=s
    return math.sqrt(((x-y)**2+(y-z)**2+(z-x)**2)/2+3*(xy*xy+yz*yz+zx*zx))


def solve(directory,radius,level):
    directory.mkdir();m=mesh(radius,level);(directory/'case.inp').write_text(deck(m))
    with (directory/'solver.log').open('w') as log:
        subprocess.run(['ccx','-i','case'],cwd=directory,env={'PATH':'/usr/bin:/bin','OMP_NUM_THREADS':'1'},stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
    log=(directory/'solver.log').read_text()
    if 'Job finished' not in log or '*ERROR' in log:raise ValueError('Solver failed')
    fields=read_frd(directory/'case.frd')
    if set(fields['DISP'])!=set(m['nodes']) or set(fields['STRESS'])!=set(m['nodes']):raise ValueError('Incomplete field coverage')
    if not all(math.isfinite(v) for values in fields.values() for row in values.values() for v in row):raise ValueError('Nonfinite result')
    dat=(directory/'case.dat').read_text().splitlines();totals={}
    for i,line in enumerate(dat):
        if line.strip().startswith('total force') and 'set' in line:totals[line.split('set')[1].split()[0]]=list(map(float,dat[i+2].split()))
    ip=[]
    for line in dat:
        v=line.split()
        if len(v)==8 and v[0].isdigit() and v[1].isdigit():ip.append((int(v[0]),list(map(float,v[2:]))))
    if len(ip)!=27*len(m['elements']):raise ValueError('Missing expanded CPE8 integration points')
    stresses={i:vm(s) for i,s in fields['STRESS'].items()};peak=max(stresses,key=stresses.get)
    def near_root(n,margin):x,y=m['nodes'][n];return min(math.hypot(x-cx,y-cy) for cx,cy in ROOT_CORNERS)<=radius+margin
    root=max((n for n in stresses if near_root(n,.1)),key=stresses.get)
    ip_peak=max(vm(s) for _,s in ip);near=[k for k,e in enumerate(m['elements'],1) if any(near_root(n,.1) for n in e)]
    near=set(near);root_ip=max(vm(s) for k,s in ip if k in near);fx,fy=resultant(m)
    for name in ['case.frd','case.dat']:
        with (directory/name).open('rb') as src:(directory/(name+'.gz')).write_bytes(gzip.compress(src.read(),mtime=0))
    result={'fillet_radius_mm':radius,'fillet_radius_is_assumption':True,'level':level,'global_size_mm':GLOBAL_MM[level],'root_size_mm':LOCAL_MM[level],'nodes':len(m['nodes']),'elements':len(m['elements']),'pressure_faces':len(m['loads']),'cad_area_mm2':m['cad_area_mm2'],
            'pressure_resultant_n_per_mm':[fx,fy],'reaction_xsym_n_per_mm':totals['XSYM'][:2],'reaction_ysym_n_per_mm':totals['YSYM'][:2],
            'maximum_displacement_mm':max(math.sqrt(sum(v*v for v in u)) for u in fields['DISP'].values()),'maximum_nodal_von_mises_mpa':stresses[peak],'peak_position_section_mm':m['nodes'][peak],
            'root_nodal_von_mises_mpa':stresses[root],'root_peak_position_section_mm':m['nodes'][root],'maximum_integration_point_von_mises_mpa':ip_peak,'root_integration_point_von_mises_mpa':root_ip,
            'solver_version':log.split('CalculiX Version ')[1].split(',')[0],'gmsh_version':m['gmsh_version'],'pressure_qualified':False,
            'source_hashes':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ['case.inp','case.frd','case.dat','solver.log']}}
    (directory/'case.frd').unlink();(directory/'case.dat').unlink()
    for extra in directory.iterdir():
        if extra.name not in {'case.inp','case.frd.gz','case.dat.gz','solver.log'}:extra.unlink()
    (directory/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def reuse(directory,radius,level):
    """Accept a finished case only if its outputs match its receipt and its deck regenerates byte for byte."""
    row=json.loads((directory/'receipt.json').read_text())
    for name,digest in row['source_hashes'].items():
        data=gzip.decompress((directory/(name+'.gz')).read_bytes()) if name.endswith(('.frd','.dat')) else (directory/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise ValueError(f'{directory.name}: {name} does not match its receipt')
    if hashlib.sha256(deck(mesh(radius,level)).encode()).hexdigest()!=row['source_hashes']['case.inp']:raise ValueError(f'{directory.name}: deck does not regenerate')
    if (row['fillet_radius_mm'],row['level'])!=(radius,level):raise ValueError(f'{directory.name}: receipt is for another case')
    return row


def run(output,image,resume=False):
    if output.exists() and not resume:raise FileExistsError(output)
    if resume and not output.exists():raise FileNotFoundError(output)
    if (output/'fillet-convergence.json').exists():raise FileExistsError(output/'fillet-convergence.json')
    if not shutil.which('ccx'):raise RuntimeError('CalculiX not on PATH; run inside the cadsim image')
    output.mkdir(parents=True,exist_ok=resume);cases=[];reused=[];discarded=[]
    for radius in RADII:
        for level in range(len(GLOBAL_MM)):
            directory=output/f'fillet-{radius}-level-{level}'
            if resume and (directory/'receipt.json').exists():row=reuse(directory,radius,level);reused.append(directory.name)
            else:
                if resume and directory.exists():shutil.rmtree(directory);discarded.append(directory.name)
                row=solve(directory,radius,level)
            cases.append(row)
            print(radius,level,row['elements'],row['root_nodal_von_mises_mpa'],row['root_integration_point_von_mises_mpa'],row['maximum_displacement_mm'],flush=True)
    summary={}
    for radius in RADII:
        rows=[c for c in cases if c['fillet_radius_mm']==radius]
        summary[str(radius)]={'root_nodal_von_mises_mpa':[r['root_nodal_von_mises_mpa'] for r in rows],'maximum_integration_point_von_mises_mpa':[r['maximum_integration_point_von_mises_mpa'] for r in rows],
                              'maximum_displacement_mm':[r['maximum_displacement_mm'] for r in rows],'root_nodal_richardson':richardson([r['root_nodal_von_mises_mpa'] for r in rows]),
                              'root_integration_point_von_mises_mpa':[r['root_integration_point_von_mises_mpa'] for r in rows],'integration_point_richardson':richardson([r['root_integration_point_von_mises_mpa'] for r in rows]),'displacement_richardson':richardson([r['maximum_displacement_mm'] for r in rows]),
                              'solid_area_mm2':solid_area(radius),'full_section_open_area_mm2':4*HALF_HEIGHT*sum(b-max(a,0.) for a,b in channel_edges())-4*len(ROOT_CORNERS)*(1-math.pi/4)*radius*radius}
    result={'status':'conditional_plane_strain_fillet_convergence','fillet_radii_are_assumptions':True,'image_id_declared_by_runner':image,'python':platform.python_version(),
            'elastic_modulus_mpa':E,'poisson_ratio':NU,'pressure_mpa':PRESSURE,'assumed_threshold_mpa':40,'global_sizes_mm':GLOBAL_MM,'root_sizes_mm':LOCAL_MM,'refinement_ratio':2,'gci_safety_factor':GCI_SAFETY,
            'cases':cases,'summary':summary,'resumed':resume,'reuse_note':'Reused cases were solved by an earlier revision of this file that lacked only the resume path in run(); each reused deck regenerates byte for byte with this revision and its outputs match its receipt.' if reused else None,'reused_verified_cases':reused,'discarded_incomplete_cases':discarded,'pressure_qualified':False,'manufacturing_authorized':False,'resolved_thermal_or_flow_simulation':False,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dependency_hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [REPO/'models/horizontal-fan-reconstruction/source/summarize_analytical_fem.py',ROOT/'source/study.py']}}
    (output/'fillet-convergence.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--image-id',required=True);p.add_argument('--resume',action='store_true',help='reuse verified finished cases of an interrupted run');args=p.parse_args();run(args.output,args.image_id,args.resume)
