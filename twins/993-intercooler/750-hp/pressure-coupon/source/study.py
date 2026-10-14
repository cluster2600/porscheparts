"""Quarter-section plane-strain pressure study; no component qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
sys.path.insert(0,str(REPO/'models/horizontal-fan-reconstruction/source'))
from summarize_analytical_fem import read_frd
sys.path.insert(0,str(ROOT.parent/'source'))
from size_core import duct,properties
IMAGE='sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
E=50000.;NU=.33;PRESSURE=.375


def centres(count):
    if count not in (0,2,4):raise ValueError('Unsupported rib count')
    return [12/count*(1+2*i) for i in range(count//2)] if count else []


def axis(breaks,h):
    return [round(a+(b-a)*i/math.ceil((b-a)/h),9) for a,b in zip(breaks,breaks[1:]) for i in range(math.ceil((b-a)/h))]+[breaks[-1]]


def mesh(count,h,patch=False):
    if h not in (.4,.2,.1):raise ValueError('Unsupported mesh size')
    ribs=centres(count);xs=axis(sorted({0.,11.2,12.,*[c+d for c in ribs for d in [-.4,.4]]}),h);ys=axis([0.,1.5,2.3],h)
    if patch:xs,ys=[0.,1.],[0.,1.]
    def fluid(x,y):return 0<=x<11.2 and 0<=y<1.5 and not any(abs(x-c)<.4 for c in ribs)
    nodes={};ids={};elements=[];loads=[];cells={}
    def node(x,y):
        key=(round(x,9),round(y,9))
        if key not in ids:ids[key]=len(ids)+1;nodes[ids[key]]=key
        return ids[key]
    for i,(x0,x1) in enumerate(zip(xs,xs[1:])):
        for j,(y0,y1) in enumerate(zip(ys,ys[1:])):
            if not patch and fluid((x0+x1)/2,(y0+y1)/2):continue
            points=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),((x0+x1)/2,y0),(x1,(y0+y1)/2),((x0+x1)/2,y1),(x0,(y0+y1)/2)]
            tag=len(elements)+1;elements.append([node(*p) for p in points]);cells[i,j]=tag
            if not patch:
                for face,(x,y) in enumerate([((x0+x1)/2,y0-1e-6),(x1+1e-6,(y0+y1)/2),((x0+x1)/2,y1+1e-6),(x0-1e-6,(y0+y1)/2)],1):
                    if fluid(x,y):loads.append((tag,face))
    return nodes,elements,loads


def deck(count,h,patch=False,pressure=PRESSURE):
    nodes,elements,loads=mesh(count,h,patch);lines=['*HEADING','Conditional coupon quarter-section, mm N MPa','*NODE']
    lines += [f'{i},{x:.9g},{y:.9g},0' for i,(x,y) in nodes.items()]
    lines+=['*ELEMENT,TYPE=CPE8,ELSET=BODY']+[','.join(map(str,[i,*e])) for i,e in enumerate(elements,1)]
    lines+=['*MATERIAL,NAME=ASSUMED_HOT_AL','*ELASTIC',f'{E},{NU}','*SOLID SECTION,ELSET=BODY,MATERIAL=ASSUMED_HOT_AL','1','*BOUNDARY']
    if patch is True:
        for i,(x,y) in nodes.items():lines += [f'{i},1,1,{.001*x:.12g}',f'{i},2,2,{-NU/(1-NU)*.001*y:.12g}']
    else:
        lines += [f'{i},1,1' for i,(x,y) in nodes.items() if x==0]+[f'{i},2,2' for i,(x,y) in nodes.items() if y==0]
    if patch=='traction':loads=[(1,2)]
    lines+=['*STEP','*STATIC']
    if loads:lines+=['*DLOAD']+[f'{i},P{face},{pressure}' for i,face in loads]
    lines+=['*NODE FILE,OUTPUT=2D','U','*EL FILE','S','*EL PRINT,ELSET=BODY','S','*END STEP']
    return '\n'.join(lines)+'\n',nodes,elements,loads


def solve(directory,count,h,patch=False,pressure=PRESSURE):
    directory.mkdir();text,nodes,elements,loads=deck(count,h,patch,pressure);(directory/'case.inp').write_text(text)
    with (directory/'solver.log').open('w') as log:
        subprocess.run(['docker','run','--rm','--network','none','--cpus','2','--memory','2g','-e','OMP_NUM_THREADS=2','-v',f'{directory.resolve()}:/case','-w','/case','--entrypoint','/usr/bin/ccx',IMAGE,'-i','case'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    log=(directory/'solver.log').read_text()
    if 'Job finished' not in log or '*ERROR' in log:raise ValueError('Solver failed')
    fields=read_frd(directory/'case.frd')
    if set(fields['DISP'])!=set(nodes) or set(fields['STRESS'])!=set(nodes):raise ValueError('Incomplete field coverage')
    if not all(math.isfinite(v) for values in fields.values() for row in values.values() for v in row):raise ValueError('Nonfinite result')
    def vm(s):
        x,y,z,xy,yz,zx=s
        return math.sqrt(((x-y)**2+(y-z)**2+(z-x)**2)/2+3*(xy*xy+yz*yz+zx*zx))
    stresses={i:vm(s) for i,s in fields['STRESS'].items()};disp=max(math.sqrt(sum(v*v for v in u)) for u in fields['DISP'].values())
    peak=max(stresses,key=stresses.get)
    result={'rib_count':count,'mesh_mm':h,'pressure_mpa':pressure,'nodes':len(nodes),'elements':len(elements),'pressure_faces':len(loads),'maximum_displacement_mm':disp,'maximum_nodal_von_mises_mpa':stresses[peak],'peak_position_section_mm':nodes[peak],'small_displacement_screen':disp/.8<.1,'below_assumed_40mpa':stresses[peak]<40,'pressure_qualified':False,'solver_version':log.split('CalculiX Version ')[1].split(',')[0],'source_hashes':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ['case.inp','case.frd','case.dat','solver.log']}}
    if patch:
        expected=-pressure if patch=='traction' else E*.001/(1-NU*NU);target=[expected,0,NU*expected,0,0,0]
        strain=expected*(1-NU*NU)/E
        result['patch_stress_error_mpa']=max(abs(s[k]-target[k]) for s in fields['STRESS'].values() for k in range(6))
        result['patch_displacement_error_mm']=max(abs(fields['DISP'][i][k]-v) for i,(x,y) in nodes.items() for k,v in enumerate([strain*x,-NU/(1-NU)*strain*y,0]))
        ip=[list(map(float,line.split()[2:])) for line in (directory/'case.dat').read_text().splitlines() if len(line.split())==8 and line.split()[0].isdigit() and line.split()[1].isdigit()]
        if len(ip)!=27:raise ValueError('Missing expanded CPE8 integration points')
        result['patch_integration_point_error_mpa']=max(abs(s[k]-target[k]) for s in ip for k in range(6))
        if result['patch_integration_point_error_mpa']>1e-4 or result['patch_stress_error_mpa']/abs(expected)>1e-4 or result['patch_displacement_error_mm']>1e-8:raise ValueError('Analytical patch failed')
    (directory/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def hydraulic(count):
    # shortcut: smooth fully developed laminar resistance plus K=2; short-coupon entrance and roughness require CFD or measurements.
    edges=[-11.2]+[s*c+d for s in [-1,1] for c in centres(count) for d in [-.4,.4]]+[11.2];edges=sorted(edges)
    widths=[b-a for a,b in zip(edges[::2],edges[1::2])]
    a={'gas_constant_j_kg_k':287.05,'gamma':1.4};temp=506.46954;pressure=303975.;rho,mu,k=properties(temp,pressure,1005,287.05)
    total_mass=rho*.0224*.003*1.;coeff=[]
    for width in widths:
        d=duct(.003,width/1000,.024,1,1e-8,temp,pressure,1005,a,1,1,0)
        coeff.append((d['pressure_drop_pa']/1e-8,2/(2*rho*d['open_area_m2']**2)))
    def flows(dp):return [2*dp/(r+math.sqrt(r*r+4*b*dp)) for r,b in coeff]
    lo,hi=0.,1000.
    for _ in range(70):
        mid=(lo+hi)/2
        if sum(flows(mid))<total_mass:lo=mid
        else:hi=mid
    channels=[duct(.003,w/1000,.024,1,m,temp,pressure,1005,a,1,1,2) for w,m in zip(widths,flows(hi))]
    if any(d['regime']!='laminar' for d in channels):raise ValueError('Laminar model invalid')
    return {'clear_widths_mm':widths,'total_mass_flow_kg_s':total_mass,'open_area_mm2':sum(widths)*3,'pressure_drop_pa':hi,'channels':channels,'hydraulic_performance_accepted':False}


def run(output):
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);patch=solve(output/'patch',0,.4,True);traction=solve(output/'traction-patch',0,.4,'traction')
    rows=[]
    for count in [0,2,4]:
        for h in [.4,.2,.1]:
            row=solve(output/f'ribs-{count}-h-{h}',count,h);rows.append(row);print(count,h,row['maximum_nodal_von_mises_mpa'],row['maximum_displacement_mm'],flush=True)
    half=solve(output/'half-pressure',4,.2,pressure=PRESSURE/2);full=next(r for r in rows if r['rib_count']==4 and r['mesh_mm']==.2)
    ratio=half['maximum_displacement_mm']/full['maximum_displacement_mm']
    if abs(ratio-.5)>1e-5:raise ValueError('Linear pressure scaling failed')
    result={'status':'conditional_plane_strain_pressure_comparison','image_id':IMAGE,'elastic_modulus_mpa':E,'poisson_ratio':NU,'pressure_mpa':PRESSURE,'patch':patch,'traction_patch':traction,'cases':rows,'half_pressure_check':half,'half_pressure_displacement_ratio':ratio,'hydraulic_proxies':{str(n):hydraulic(n) for n in [0,2,4]},'pressure_qualified':False,'manufacturing_authorized':False,'resolved_thermal_or_flow_simulation':False,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'dependency_hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [REPO/'models/horizontal-fan-reconstruction/source/summarize_analytical_fem.py',ROOT.parent/'source/size_core.py']}}
    (output/'study.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();run(args.output)
