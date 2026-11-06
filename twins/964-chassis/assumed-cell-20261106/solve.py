#!/usr/bin/env python3
"""Conditional S8R laminate stiffness study on explicitly assumed rectangular panels.

Uses the retained offline CalculiX 2.21 image. No donor geometry or contact data
are consumed. Raw decks/fields remain in the caller's private output directory.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time

IMAGE = 'sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4'
HERE = Path(__file__).resolve().parent
FLOAT = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][-+]?\d+)?'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def linspace_breaks(breaks, size):
    result = []
    for lo, hi in zip(breaks, breaks[1:]):
        # One S8R across a free strip admitted a spurious in-plane midside
        # mode in the first coupon. Keep at least two on every shared interval.
        count = max(2, math.ceil((hi-lo)/size))
        result.extend(lo+(hi-lo)*i/count for i in range(count))
    return result + [breaks[-1]]

def mesh(model, size):
    require(model['units'] == 'mm' and model['status'] == 'assumed', 'Only explicit mm assumed geometry admitted')
    require(size > 0, 'Mesh size must be positive')
    grids = [linspace_breaks(model['axis_breaks_mm'][a], size) for a in ('x','y','z')]
    nodes, lookup, elements, seen = {}, {}, [], set()
    def node(p):
        key = tuple(round(x, 10) for x in p)
        if key not in lookup:
            lookup[key] = len(nodes)+1
            nodes[lookup[key]] = list(key)
        return lookup[key]
    for panel in model['panels']:
        n, u, v = panel['normal_axis'], panel['u_axis'], panel['v_axis']
        require((n,u,v) in [(0,1,2),(1,2,0),(2,0,1)], 'Panel axes must have positive consistent normals')
        us = [x for x in grids[u] if panel['u_mm'][0]-1e-8 <= x <= panel['u_mm'][1]+1e-8]
        vs = [x for x in grids[v] if panel['v_mm'][0]-1e-8 <= x <= panel['v_mm'][1]+1e-8]
        require(len(us)>1 and len(vs)>1, 'Empty panel mesh')
        for a,b in zip(us,us[1:]):
            for c,d in zip(vs,vs[1:]):
                uv = [(a,c),(b,c),(b,d),(a,d),((a+b)/2,c),(b,(c+d)/2),((a+b)/2,d),(a,(c+d)/2)]
                xyz = []
                for uu,vv in uv:
                    p=[0.,0.,0.];p[n]=panel['at_mm'];p[u]=uu;p[v]=vv;xyz.append(p)
                ids=[node(p) for p in xyz]
                key=tuple(sorted(ids[:4]));require(key not in seen, 'Duplicate coplanar element')
                seen.add(key)
                elements.append({'id':len(elements)+1,'nodes':ids,'panel':panel,'area':(b-a)*(d-c)})
    require(nodes and elements, 'Empty mesh')
    return nodes, elements

def edge_weights(nodes, elements, predicate):
    weights=defaultdict(float);seen=set()
    for element in elements:
        for i,j,m in [(0,1,4),(1,2,5),(2,3,6),(3,0,7)]:
            edge=[element['nodes'][k] for k in (i,j,m)]
            if predicate(element, [nodes[k] for k in edge]):
                key=tuple(sorted(edge))
                if key in seen:continue
                seen.add(key);length=math.dist(nodes[edge[0]],nodes[edge[1]])
                for k,w in zip(edge,[length/6,length/6,2*length/3]):weights[k]+=w
    require(weights and sum(weights.values())>0, 'Load patch is empty')
    total=sum(weights.values())
    return {k:v/total for k,v in weights.items()}

def make_loads(model,nodes,elements,case):
    xmax=max(p[0] for p in nodes.values());groups={};loads=defaultdict(lambda:[0.,0.,0.])
    if case in ['torsion','cantilever']:
        if case=='cantilever':
            groups['tip']=edge_weights(nodes,elements,lambda e,p:all(abs(q[0]-xmax)<1e-8 for q in p))
            for n,w in groups['tip'].items():loads[n][2]=-w
        else:
            height=model['dimensions_mm']['sill_height']
            for label,sign in [('left',1),('right',-1)]:
                groups[label]=edge_weights(nodes,elements,lambda e,p,s=sign:e['panel']['component']=='sills' and e['panel']['normal_axis']==2 and all(abs(q[0]-xmax)<1e-8 and abs(q[2]-height)<1e-8 and s*q[1]>0 for q in p))
                for n,w in groups[label].items():loads[n][2]+=sign*1000*w
    elif case=='bending':
        floor=[e for e in elements if e['panel']['component']=='floor'];area=sum(e['area'] for e in floor)
        require(area>0, 'No floor to receive bending pressure')
        for e in floor:
            for n,w in zip(e['nodes'],[-1/12]*4+[1/3]*4):loads[n][2]+=-10000*e['area']/area*w
    else:raise ValueError('Unknown load case')
    return dict(loads),groups

def validate_material(card):
    e=card['engineering_constants_MPa'];p=card['poisson']
    require(all(e[k]>0 for k in ['E1','E2','E3','G12','G13','G23']), 'Positive elastic moduli required')
    a,b,c=1/e['E1'],1/e['E2'],1/e['E3'];d=-p['nu12']/e['E1'];f=-p['nu13']/e['E1'];g=-p['nu23']/e['E2']
    require(a*b-d*d>0 and a*b*c+2*d*f*g-a*g*g-b*f*f-c*d*d>0, 'Orthotropic compliance must be positive definite')

def write_deck(path,model,nodes,elements,loads,card,material):
    validate_material(card)
    fixed=[n for n,p in nodes.items() if abs(p[0])<1e-8];require(fixed,'No x=0 clamp')
    groups=defaultdict(list);root_faces=[]
    for e in elements:
        groups[e['panel']['normal_axis']].append(e['id'])
        if e['panel']['normal_axis']!=0:
            for i,j,face in [(0,1,3),(1,2,4),(2,3,5),(3,0,6)]:
                if abs(nodes[e['nodes'][i]][0])<1e-8 and abs(nodes[e['nodes'][j]][0])<1e-8:root_faces.append((e['id'],face))
    out=['*HEADING','Explicit hypothetical panel study; no physical qualification','*NODE,NSET=NALL']
    out.extend(f"{n},"+','.join(f'{x:.12g}' for x in p) for n,p in nodes.items())
    out.append('*ELEMENT,TYPE=S8R,ELSET=EALL')
    out.extend(f"{e['id']},"+','.join(map(str,e['nodes'])) for e in elements)
    for axis,ids in groups.items():
        out.append(f'*ELSET,ELSET=P{axis}')
        out.extend(','.join(map(str,ids[k:k+12])) for k in range(0,len(ids),12))
    out.extend(['*NSET,NSET=CLAMP']+[','.join(map(str,fixed[k:k+12])) for k in range(0,len(fixed),12)])
    out.append('*MATERIAL,NAME=UD')
    if material=='isotropic':out.extend(['*ELASTIC','70000.,0.0'])
    else:
        e=card['engineering_constants_MPa'];p=card['poisson']
        out.extend(['*ELASTIC,TYPE=ENGINEERING CONSTANTS',','.join(str(x) for x in [e['E1'],e['E2'],e['E3'],p['nu12'],p['nu13'],p['nu23'],e['G12'],e['G13']]),str(e['G23'])])
    angles=card['ply_angles_deg'];thickness=model['thickness_mm'];require(thickness>0,'Positive thickness required')
    for axis in groups:
        n=[float(k==axis) for k in range(3)];a=[0.,1.,0.] if axis==0 else [1.,0.,0.];b=cross(n,a)
        for k,angle in enumerate(angles):
            r=math.radians(angle);c,s=math.cos(r),math.sin(r);aa=[c*x+s*y for x,y in zip(a,b)];bb=[-s*x+c*y for x,y in zip(a,b)]
            out.extend([f'*ORIENTATION,NAME=O{axis}_{k}',','.join(f'{x:.12g}' for x in aa+bb)])
        if material=='isotropic':out.extend([f'*SHELL SECTION,ELSET=P{axis},MATERIAL=UD',str(thickness)])
        else:
            out.append(f'*SHELL SECTION,COMPOSITE,ELSET=P{axis}')
            out.extend(f'{thickness/len(angles):.12g},,UD,O{axis}_{k}' for k in range(len(angles)))
    if root_faces:
        out.append('*SURFACE,NAME=ROOT,TYPE=ELEMENT');out.extend(f'{e},S{f}' for e,f in root_faces)
    out.extend(['*BOUNDARY','CLAMP,1,6','*STEP','*STATIC','*CLOAD'])
    for n,force in sorted(loads.items()):
        for dof,value in enumerate(force,1):
            if value:out.append(f'{n},{dof},{value:.14g}')
    out.extend(['*NODE PRINT,NSET=NALL','U','*NODE PRINT,NSET=CLAMP,TOTALS=YES','RF','*NODE FILE,OUTPUT=3D','U'])
    if root_faces:out.extend(['*SECTION PRINT,SURFACE=ROOT,NAME=ROOT_RESULTANT','SOF,SOM'])
    out.append('*END STEP');path.write_text('\n'.join(out)+'\n')
    return fixed

def parse_dat(path):
    displacement={};mode=None;sections=[];lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        low=line.lower()
        if 'displacements (' in low:mode='U';continue
        if 'forces (' in low:mode=None
        if mode=='U':
            fields=line.split()
            if len(fields)==4 and fields[0].isdigit():
                displacement[int(fields[0])]=[float(v.replace('D','E')) for v in fields[1:]]
        if 'total surface force' in low:
            numbers=[]
            for row in lines[i+1:i+6]:
                vals=re.findall(FLOAT,row)
                if len(vals)>=3:numbers=[float(x.replace('D','E')) for x in vals];break
            sections.append({'header':line.strip(),'values':numbers})
    require(displacement,'No original-node DAT displacements')
    return displacement,sections

def clamp_force_total(path):
    lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if 'total force (fx,fy,fz) for set CLAMP' in line:
            for row in lines[i+1:i+5]:
                fields=row.split()
                if len(fields)==3:
                    return [float(v.replace('D','E')) for v in fields]
    raise ValueError('DAT clamp total force is missing')

def force_balance(nodes,loads,fixed,raw_clamp_rf):
    # CalculiX RF is total external nodal force, including CLOAD and reaction.
    # Subtract the CLOAD already applied on fixed nodes to recover reactions;
    # equivalently add only free-node CLOAD to the raw clamp RF total.
    clamp=set(fixed)
    applied=[sum(f[k] for f in loads.values()) for k in range(3)]
    applied_clamp=[sum(f[k] for n,f in loads.items() if n in clamp) for k in range(3)]
    reaction=[r-f for r,f in zip(raw_clamp_rf,applied_clamp)]
    residual=[r+f for r,f in zip(reaction,applied)]
    scale=sum(math.sqrt(sum(v*v for v in f)) for f in loads.values())
    relative=math.sqrt(sum(v*v for v in residual))/scale
    return {'DAT_clamp_total_external_force_RF_N':raw_clamp_rf,
            'CLOAD_on_clamped_nodes_N':applied_clamp,
            'physical_clamp_reaction_RF_minus_clamp_CLOAD_N':reaction,
            'force_balance_residual_N':residual,
            'force_balance_reference_sum_nodal_force_magnitudes_N':scale,
            'force_balance_relative_residual':relative,'force_balance_limit':1e-5,
            'translational_force_balance_verified':relative<1e-5}

def run_solver(directory,memory_gib,timeout):
    cidfile=directory.resolve()/'container.cid'
    command=['docker','run','--rm','--cidfile',str(cidfile),'--network=none','--read-only','--cpus=1',f'--memory={memory_gib}g',f'--memory-swap={memory_gib}g','--pids-limit=256','--cap-drop=ALL','--security-opt=no-new-privileges','--tmpfs=/tmp:rw,nosuid,size=64m','--mount',f'type=bind,src={directory.resolve()},dst=/job','--workdir=/job','--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--env','CCX_NPROC_RESULTS=1','--env','CCX_NPROC_EQUATION_SOLVER=1','--entrypoint','/usr/bin/ccx',IMAGE,'-i','model']
    started=time.monotonic()
    try:r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        if cidfile.exists():
            subprocess.run(['docker','rm','--force',cidfile.read_text().strip()],capture_output=True,timeout=30)
        (directory/'failure.json').write_text(json.dumps({'status':'timeout','seconds':timeout})+'\n');raise error
    (directory/'stdout.log').write_text(r.stdout);(directory/'stderr.log').write_text(r.stderr)
    (directory/'execution.json').write_text(json.dumps({'command':command,'returncode':r.returncode,'elapsed_seconds':time.monotonic()-started,'image':IMAGE},indent=2)+'\n')
    require(r.returncode==0 and 'Job finished' in r.stdout,'CalculiX did not finish; inspect retained logs')
    require('Using up to 1 cpu' in r.stdout or 'Using up to 1 cpu' in r.stderr,'Single-thread solver witness missing')
    return time.monotonic()-started

def solve(model,card,directory,size,case,material='laminate',memory=4,timeout=600,input_hashes=None,load_factor=1.):
    require(math.isfinite(load_factor) and load_factor>0,'Positive finite load factor required')
    require(all(sha(p)==v for p,v in (input_hashes or {}).items()),'Preflight input hash mismatch')
    directory.mkdir(parents=True,exist_ok=False);nodes,elements=mesh(model,size);loads,groups=make_loads(model,nodes,elements,case)
    loads={n:[load_factor*v for v in f] for n,f in loads.items()}
    fixed=write_deck(directory/'model.inp',model,nodes,elements,loads,card,material)
    manifest={'classification':'explicit_assumed_inputs_admitted_for_conditional_linear_stiffness_only','mesh_size_mm':size,'minimum_subdivisions_per_shared_interval':2,'elements':len(elements),'nodes':len(nodes),'element':'S8R','assembly':'shared shell midplanes, rigid ideal junctions','material':material,'material_card':card if material=='laminate' else {'E_MPa':70000.,'nu':0.},'thickness_mm':model['thickness_mm'],'case':case,'load_factor':load_factor,'solver_script_sha256':sha(__file__),'deck_sha256':sha(directory/'model.inp'),'input_hashes':input_hashes or {},'source_geometry_or_contacts_admitted':False}
    (directory/'preflight.json').write_text(json.dumps(manifest,indent=2)+'\n')
    elapsed=run_solver(directory,memory,timeout);u,sections=parse_dat(directory/'model.dat')
    require(all(sha(p)==v for p,v in (input_hashes or {}).items()),'Input changed while solver ran')
    require(all(n in u for n in nodes),'DAT does not cover all original input nodes')
    total=[sum(f[k] for f in loads.values()) for k in range(3)];moment=[0.,0.,0.]
    for n,f in loads.items():
        m=cross(nodes[n],f);moment=[a+b for a,b in zip(moment,m)]
    work=sum(sum(f[k]*u[n][k] for k in range(3)) for n,f in loads.items());require(work>0,'Nonpositive external work')
    metrics={'external_work_Nmm':work,'linear_strain_energy_from_half_external_work_Nmm':work/2,'energy_output_independently_verified':False,'applied_resultant_N':total,'applied_moment_about_origin_Nmm':moment,'max_abs_U_mm':max(math.sqrt(sum(v*v for v in q)) for q in u.values()),'max_clamp_U_mm':max(math.sqrt(sum(v*v for v in u[n])) for n in fixed)}
    metrics.update(force_balance(nodes,loads,fixed,clamp_force_total(directory/'model.dat')))
    if case=='torsion':
        yl=sum(w*nodes[n][1] for n,w in groups['left'].items());yr=sum(w*nodes[n][1] for n,w in groups['right'].items());ul=sum(w*u[n][2] for n,w in groups['left'].items());ur=sum(w*u[n][2] for n,w in groups['right'].items());theta=(ul-ur)/(yl-yr)
        require(theta!=0,'Zero torsion rotation');metrics.update(twist_rad=theta,twist_deg=math.degrees(theta),load_patch_mean_y_mm=[yl,yr],load_patch_mean_Uz_mm=[ul,ur],torsion_stiffness_Nm_per_deg=(moment[0]/1000)/math.degrees(theta))
    elif case=='bending':metrics.update(work_conjugate_floor_deflection_mm=work/(10000*load_factor),bending_stiffness_N_per_mm=(10000*load_factor)**2/work)
    else:metrics['work_conjugate_tip_deflection_mm']=work/load_factor
    output=dict(manifest,classification='executed_assumed_linear_shell_stiffness_not_vehicle_validation',metrics=metrics,section_print_blocks=sections,section_resultant_scope='Stress-extrapolation/integration diagnostic; not automatically qualified support reactions, especially across laminate interfaces. Composite root resultants observed zero; moment balance remains unverified.',reaction_force_and_moment_equilibrium_verified=False,elapsed_seconds=elapsed,material_card_assumed=True,physical_validation=False,manufacturing_authorized=False,donor_transform=None,raw_solver_outputs_private=True)
    (directory/'mesh.json').write_text(json.dumps({'nodes':nodes,'elements':elements},separators=(',',':'))+'\n');(directory/'displacements.json').write_text(json.dumps(u,separators=(',',':'))+'\n');(directory/'result.json').write_text(json.dumps(output,indent=2)+'\n')
    return output

def benchmark(output,card,memory,timeout):
    output.mkdir(parents=True,exist_ok=False)
    model={'units':'mm','status':'assumed','thickness_mm':2.,'axis_breaks_mm':{'x':[0.,100.],'y':[0.,10.],'z':[0.]},'panels':[{'name':'beam','component':'benchmark','normal_axis':2,'at_mm':0.,'u_axis':0,'v_axis':1,'u_mm':[0.,100.],'v_mm':[0.,10.]}]}
    # At least two elements across this coupon's width avoid the free-edge
    # in-plane mechanism observed in the retained one-element-wide first trial.
    controls={};isocard=dict(card,engineering_constants_MPa={k:70000. if k.startswith('E') else 35000. for k in ['E1','E2','E3','G12','G13','G23']},poisson={k:0. for k in ['nu12','nu13','nu23']})
    for name,mat,coupon,E in [('isotropic','isotropic',card,70000.),('isotropic-eight-ply','laminate',isocard,70000.),('UD-zero','laminate',dict(card,ply_angles_deg=[0.]*8,poisson={k:0. for k in ['nu12','nu13','nu23']}),135000.),('UD-ninety','laminate',dict(card,ply_angles_deg=[90.]*8,poisson={k:0. for k in ['nu12','nu13','nu23']}),10000.)]:
        actual=solve(model,coupon,output/name,5.,'cantilever',mat,memory,timeout)
        expected=100.**3/(3*E*(10*2.**3/12));measured=actual['metrics']['work_conjugate_tip_deflection_mm'];error=abs(measured-expected)/expected
        controls[name]={'analytic_Euler_Bernoulli_tip_mm':expected,'measured_tip_mm':measured,'relative_error':error,'acceptance_limit':0.01,'passed':error<0.01,'solver_result_sha256':sha(output/name/'result.json')}
    equivalence=abs(controls['isotropic-eight-ply']['measured_tip_mm']/controls['isotropic']['measured_tip_mm']-1)
    result={'classification':'independently_known_cantilever_material_and_orientation_numerical_controls','controls':controls,'layered_isotropic_relative_difference':equivalence,'layered_equivalence_limit':0.0001,'passed':all(c['passed'] for c in controls.values()) and equivalence<0.0001,'scope':'100x10x2mm slender beam,1N tip,E70000 isotropic and eight-ply isotropic equivalent; UD zero/90 E135000/10000,all Poisson ratios zero for isolated orientation controls. Beam theory omits shear deformation; no Porsche or laminate strength claim.','initial_one_element_width_trial':'Retained benchmark-001 matches tip compliance but has a spurious free-edge in-plane midside mode; superseded by two elements across width.'}
    (output/'benchmark.json').write_text(json.dumps(result,indent=2)+'\n');require(result['passed'],'Independent material/orientation benchmark failed')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['benchmark','run']);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--surfaces',type=Path);ap.add_argument('--audit',type=Path);ap.add_argument('--parameters',type=Path,default=HERE/'assumptions.json');ap.add_argument('--mesh-size',type=float,default=120);ap.add_argument('--case',choices=['torsion','bending']);ap.add_argument('--material',choices=['laminate','isotropic'],default='laminate');ap.add_argument('--load-factor',type=float,default=1.);ap.add_argument('--memory-gib',type=int,default=4);ap.add_argument('--timeout',type=int,default=600);args=ap.parse_args()
    require(not args.output.exists(),'Use a fresh output path');parameters=json.loads(args.parameters.read_text());card=parameters['laminate']
    if args.mode=='benchmark':r=benchmark(args.output,card,args.memory_gib,args.timeout)
    else:
        require(args.surfaces and args.audit and args.case,'Run requires surfaces, upstream audit and case');model=json.loads(args.surfaces.read_text());audit=json.loads(args.audit.read_text());require(audit['model_sha256']==sha(args.surfaces) and audit['connected_plate_union'],'Upstream geometry audit mismatch/disconnected geometry');require(model['parameters_sha256']==sha(args.parameters),'Parameters changed since geometry generation')
        inputs={str(p):sha(p) for p in [args.surfaces,args.audit,args.parameters]}
        r=solve(model,card,args.output,args.mesh_size,args.case,args.material,args.memory_gib,args.timeout,inputs,args.load_factor)
        require(all(sha(p)==v for p,v in inputs.items()),'Input changed while solver ran')
    print(json.dumps(r))

if __name__=='__main__':main()
