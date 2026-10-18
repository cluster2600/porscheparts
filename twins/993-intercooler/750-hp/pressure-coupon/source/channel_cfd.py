"""Exploratory laminar CFD of the four-rib hot channels, sharp and with assumed root fillets.

Runs inside the cadsim image (gmsh and OpenFOAM 13). Each distinct channel (1.8 and 5.2 mm
clear width, 3 mm high, 24 mm long) is solved as a quarter duct with two symmetry planes,
isothermal and incompressible, at the gas state of study.py. The inlet is a uniform total
pressure (a quiescent upstream plenum, no sharp-edge separation) and the outlet a uniform
static pressure, so developing flow is resolved but headers, roughness, compressibility and
heat transfer are not. Every mesh level runs each channel at 0.95 times the fully developed
proxy pressure drop, which gives the mesh convergence of the channel flow rates; the finest
level also runs at 1.05 times, and the two-term fit dp = a*m + b*m**2 per channel then gives
the equal-pressure split at the study's total mass flow. The fillet radii are assumptions.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import threading
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
_spec=importlib.util.spec_from_file_location('pressure_coupon_hydraulics',ROOT/'source/fillet_hydraulics.py');HYD=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(HYD)
RADII=HYD.RADII;HEIGHT_MM=HYD.HEIGHT_MM;LENGTH_MM=HYD.LENGTH_M*1000
# Cross-section target sizes refine by sqrt(2); the axial spacing follows the same ratio.
RATIO=math.sqrt(2);SIZES_MM=[.1*RATIO,.1,.1/RATIO]
CONVERGENCE_FACTOR,FIT_FACTOR=.95,1.05
HEADER='FoamFile\n{\n    format      ascii;\n    class       %s;\n    object      %s;\n}\n'
GMSH_LOCK=threading.Lock()  # gmsh keeps global state: mesh one case at a time.
FOAM='source /opt/openfoam13/etc/bashrc >/dev/null 2>&1 && '


def axial_layers(size):
    """Geometric axial spacing: about size/2 at the inlet, growing by 3 % up to 4*size."""
    first,growth,cap=size/2,1.03,4*size;cells=[];x=0.
    while x<LENGTH_MM:
        step=min(first*growth**len(cells),cap);cells.append(step);x+=step
    total=sum(cells);heights=[];acc=0.
    for c in cells:acc+=c*LENGTH_MM/total;heights.append(acc/LENGTH_MM)
    heights[-1]=1.;return heights


def mesh(path,width,radius,size):
    """Quarter duct: x across the channel (0..w/2), y across the height (0..1.5), z along the flow."""
    import gmsh
    with GMSH_LOCK:return _mesh(gmsh,path,width,radius,size)


def _mesh(gmsh,path,width,radius,size):
    """All-quad section from gmsh (subdivided), extruded here into hexahedra and written as msh 2.2 in metres."""
    gmsh.initialize(interruptible=False);gmsh.option.setNumber('General.Terminal',0)
    try:
        occ=gmsh.model.occ;full=occ.addRectangle(-width/2,-HEIGHT_MM/2,0,width,HEIGHT_MM,roundedRadius=radius)
        quarter=occ.addRectangle(0,0,0,width,HEIGHT_MM);out,_=occ.intersect([(2,full)],[(2,quarter)]);occ.synchronize()
        if len(out)!=1:raise ValueError('Quarter section is not one surface')
        surface=out[0][1];area=occ.getMass(2,surface)
        # Subdivision into quadrangles halves the edge length, so sizes are requested at twice the target.
        for name,value in [('Mesh.MeshSizeMin',2*size),('Mesh.MeshSizeMax',2*size),('Mesh.MeshSizeFromCurvature',0),('Mesh.MeshSizeExtendFromBoundary',0),('Mesh.Algorithm',8),('Mesh.RecombineAll',1),('Mesh.RecombinationAlgorithm',1),('Mesh.SubdivisionAlgorithm',1)]:gmsh.option.setNumber(name,value)
        gmsh.model.mesh.generate(2)
        tags,coords,_=gmsh.model.mesh.getNodes()
        index={int(t):i for i,t in enumerate(tags)};xy=[(float(coords[3*i]),float(coords[3*i+1])) for i in range(len(tags))]
        types,_,connectivity=gmsh.model.mesh.getElements(2,surface)
        if list(types)!=[3]:raise ValueError(f'Expected only 4-node quadrangles, got types {list(types)}')
        quads=[[index[int(n)] for n in connectivity[0][i:i+4]] for i in range(0,len(connectivity[0]),4)]
        edges={'wall':[],'symmetryX':[],'symmetryY':[]}
        for _,curve in gmsh.model.getBoundary(out,oriented=False):
            x0,y0,_,x1,y1,_=gmsh.model.getBoundingBox(1,curve)
            name='symmetryX' if max(abs(x0),abs(x1))<1e-6 else 'symmetryY' if max(abs(y0),abs(y1))<1e-6 else 'wall'
            ltypes,_,lconn=gmsh.model.mesh.getElements(1,curve)
            if list(ltypes)!=[1]:raise ValueError('Expected 2-node boundary lines')
            edges[name]+=[(index[int(lconn[0][i])],index[int(lconn[0][i+1])]) for i in range(0,len(lconn[0]),2)]
        version=gmsh.__version__
    finally:
        gmsh.finalize()
    for k,q in enumerate(quads):
        (x1,y1),(x2,y2),(x3,y3),(x4,y4)=(xy[n] for n in q)
        if (x1*y2-x2*y1)+(x2*y3-x3*y2)+(x3*y4-x4*y3)+(x4*y1-x1*y4)<0:quads[k]=q[::-1]
    if any(not v for v in edges.values()):raise ValueError('Empty patch')
    zs=[0.]+[h*LENGTH_MM for h in axial_layers(size)];n=len(xy)
    node=lambda i,k:k*n+i+1
    names=['inlet','outlet','wall','symmetryX','symmetryY'];physical={name:i+1 for i,name in enumerate(names)};fluid=len(names)+1
    elements=[]
    for q in quads:elements.append((3,physical['inlet'],[node(i,0) for i in q]))
    for q in quads:elements.append((3,physical['outlet'],[node(i,len(zs)-1) for i in q]))
    for name,pairs in edges.items():
        for k in range(len(zs)-1):
            for a,b in pairs:elements.append((3,physical[name],[node(a,k),node(b,k),node(b,k+1),node(a,k+1)]))
    for k in range(len(zs)-1):
        for q in quads:elements.append((5,fluid,[node(i,k) for i in q]+[node(i,k+1) for i in q]))
    lines=['$MeshFormat','2.2 0 8','$EndMeshFormat','$PhysicalNames',str(len(names)+1)]+[f'2 {physical[x]} "{x}"' for x in names]+[f'3 {fluid} "fluid"','$EndPhysicalNames','$Nodes',str(n*len(zs))]
    # The geometry is drawn in mm and written in m for OpenFOAM.
    lines+=[f'{node(i,k)} {x*1e-3:.12g} {y*1e-3:.12g} {z*1e-3:.12g}' for k,z in enumerate(zs) for i,(x,y) in enumerate(xy)]
    lines+=['$EndNodes','$Elements',str(len(elements))]+[f'{j} {t} 2 {tag} {tag} '+' '.join(map(str,ns)) for j,(t,tag,ns) in enumerate(elements,1)]+['$EndElements']
    path.write_text('\n'.join(lines)+'\n')
    return {'cad_area_mm2':area,'section_cells':len(quads),'axial_cells':len(zs)-1,'gmsh_version':version}


def dictionaries(nu,p0):
    """Case dictionaries in SI units; p is kinematic (Pa per kg/m3)."""
    files={}
    files['constant/physicalProperties']=HEADER%('dictionary','physicalProperties')+f'viscosityModel  constant;\nnu              {nu:.10g};\n'
    files['constant/momentumTransport']=HEADER%('dictionary','momentumTransport')+'simulationType laminar;\n'
    files['system/controlDict']=HEADER%('dictionary','controlDict')+'''solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         4000;
deltaT          1;
writeControl    timeStep;
writeInterval   4000;
purgeWrite      1;
writeFormat     binary;
writePrecision  10;
timeFormat      general;
runTimeModifiable false;
functions
{
    #includeFunc patchFlowRate(patch=inlet, name=inletFlow)
    #includeFunc patchFlowRate(patch=outlet, name=outletFlow)
    #includeFunc patchAverage(patch=inlet, fields=(p), name=inletPressure)
}
'''
    files['system/fvSchemes']=HEADER%('dictionary','fvSchemes')+'''ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
'''
    files['system/fvSolution']=HEADER%('dictionary','fvSolution')+'''solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-14; relTol 0.05; }
    U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-16; relTol 0.05; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent yes;
    residualControl { p 1e-8; U 1e-9; }
}
relaxationFactors { equations { U 0.9; } }
'''
    walls='    wall { type noSlip; }\n    symmetryX { type symmetryPlane; }\n    symmetryY { type symmetryPlane; }\n'
    files['0/U']=HEADER%('volVectorField','U')+'dimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\nboundaryField\n{\n    inlet { type pressureInletOutletVelocity; value uniform (0 0 0); }\n    outlet { type zeroGradient; }\n'+walls+'}\n'
    files['0/p']=HEADER%('volScalarField','p')+f'dimensions [0 2 -2 0 0 0 0];\ninternalField uniform 0;\nboundaryField\n{{\n    inlet {{ type totalPressure; p0 uniform {p0:.10g}; value uniform {p0:.10g}; }}\n    outlet {{ type fixedValue; value uniform 0; }}\n    wall {{ type zeroGradient; }}\n    symmetryX {{ type symmetryPlane; }}\n    symmetryY {{ type symmetryPlane; }}\n}}\n'
    return files


def set_patch_types(case):
    boundary=case/'constant/polyMesh/boundary';text=boundary.read_text()
    for name,kind in [('wall','wall'),('symmetryX','symmetryPlane'),('symmetryY','symmetryPlane')]:
        text,n=re.subn(r'(\n\s*'+name+r'\s*\n\s*\{\s*\n\s*type\s+)\w+;',r'\g<1>'+kind+';',text)
        if n!=1:raise ValueError('Patch not found '+name)
    boundary.write_text(text)


def last_value(case,name):
    files=sorted((case/'postProcessing'/name).rglob('*.dat'))
    if len(files)!=1:raise ValueError('Missing function output '+name)
    rows=[line.split() for line in files[0].read_text().splitlines() if line.strip() and not line.startswith('#')]
    return [float(v) for v in rows[-1]],[float(r[1]) for r in rows]


def solve(case,width,radius,size,dp_pa):
    rho,mu,_=HYD.gas();case.mkdir()
    info=mesh(case/'case.msh',width,radius,size)
    for name,text in dictionaries(mu/rho,dp_pa/rho).items():(case/name).parent.mkdir(parents=True,exist_ok=True);(case/name).write_text(text)
    with (case/'mesh.log').open('w') as log:subprocess.run(['bash','-c',FOAM+'gmshToFoam case.msh && checkMesh'],cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
    set_patch_types(case)
    with (case/'solver.log').open('w') as log:subprocess.run(['bash','-c',FOAM+'foamRun'],cwd=case,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=10800)
    mlog=(case/'mesh.log').read_text();slog=(case/'solver.log').read_text()
    if 'Mesh OK.' not in mlog:raise ValueError('checkMesh failed '+case.name)
    cells=int(re.search(r'cells:\s+(\d+)',mlog).group(1));hexes=int(re.search(r'hexahedra:\s+(\d+)',mlog).group(1))
    converged='SIMPLE solution converged' in slog
    inflow,inflows=last_value(case,'inletFlow');outflow,_=last_value(case,'outletFlow');p_in,_=last_value(case,'inletPressure')
    q=-inflow[1]*4;m=q*rho
    # Flow-rate drift over the last 50 iterations shows how settled the result is.
    drift=abs(inflows[-1]-inflows[max(0,len(inflows)-51)])/abs(inflows[-1])
    row={'width_mm':width,'fillet_radius_mm':radius,'fillet_radius_is_assumption':True,'element_size_mm':size,'cells':cells,'hexahedra':hexes,'section_cells':info['section_cells'],'axial_cells':info['axial_cells'],'cad_quarter_area_mm2':info['cad_area_mm2'],
         'pressure_difference_pa':dp_pa,'iterations':len(inflows),'simple_converged':converged,'flow_rate_drift_last_50':drift,'mass_flow_kg_s':m,'outlet_to_inlet_flow_ratio':-outflow[1]/inflow[1],
         'inlet_static_pressure_pa':p_in[1]*rho,'gmsh_version':info['gmsh_version'],'openfoam_version':re.search(r'Version:\s+(\S+)',slog).group(1),
         'source_hashes':{name:hashlib.sha256((case/name).read_bytes()).hexdigest() for name in ['case.msh','constant/polyMesh/boundary','system/controlDict','system/fvSchemes','system/fvSolution','constant/physicalProperties','constant/momentumTransport','0/U','0/p','mesh.log','solver.log']}}
    if not converged or drift>1e-5 or abs(row['outlet_to_inlet_flow_ratio']-1)>1e-6:raise ValueError('Unconverged or unbalanced case '+case.name)
    for name in ['mesh.log','solver.log']:(case/(name+'.gz')).write_bytes(gzip.compress((case/name).read_bytes(),mtime=0))
    for extra in case.iterdir():
        if extra.name not in {'system','constant','0','mesh.log.gz','solver.log.gz'}:
            shutil.rmtree(extra) if extra.is_dir() else extra.unlink()
    shutil.rmtree(case/'constant/polyMesh')
    (case/'receipt.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def fit(rows):
    """Exact two-term fit dp = a*m + b*m**2 through the two pressure levels of one channel."""
    (m1,p1),(m2,p2)=sorted((r['mass_flow_kg_s'],r['pressure_difference_pa']) for r in rows)
    b=(p2/m2-p1/m1)/(m2-m1);a=p1/m1-b*m1
    return a,b


def split(curves):
    """Equal-pressure split of the study's total mass flow over the five channels."""
    _,_,total=HYD.gas()
    def flows(dp):return [2*dp/(a+math.sqrt(a*a+4*b*dp)) for a,b in curves]
    lo,hi=0.,1000.
    for _ in range(70):
        mid=(lo+hi)/2
        if sum(flows(mid))<total:lo=mid
        else:hi=mid
    return {'pressure_drop_pa':hi,'channel_mass_flow_kg_s':flows(hi),'total_mass_flow_kg_s':total}


def run(output,proxy,image,workers):
    if output.exists():raise FileExistsError(output)
    if not shutil.which('gmshToFoam') and not Path('/opt/openfoam13/etc/bashrc').exists():raise RuntimeError('OpenFOAM 13 not found; run inside the cadsim image')
    output.mkdir(parents=True);proxy_data=json.loads(proxy.read_text());widths=HYD.widths();jobs=[]
    for radius in RADII:
        dp=proxy_data['variants'][str(radius)]['split']['pressure_drop_pa']
        for width in sorted(set(widths)):
            for level,size in enumerate(SIZES_MM):
                for factor in [CONVERGENCE_FACTOR]+([FIT_FACTOR] if level==len(SIZES_MM)-1 else []):jobs.append((output/f'r{radius}-w{width}-level-{level}-dp{factor}',width,radius,size,factor*dp,level,factor))
    # Largest cases first so the pool does not end on one long run.
    jobs.sort(key=lambda j:(-j[5],-j[1]))
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures={pool.submit(solve,j[0],*j[1:5]):j for j in jobs};rows=[]
        for f in concurrent.futures.as_completed(futures):
            j=futures[f];row=f.result();row.update(level=j[5],pressure_factor=j[6]);rows.append(row)
            (j[0]/'receipt.json').write_text(json.dumps(row,indent=2)+'\n');print(j[0].name,row['cells'],row['iterations'],row['mass_flow_kg_s'],flush=True)
    rows.sort(key=lambda r:(r['fillet_radius_mm'],r['width_mm'],r['level'],r['pressure_factor']))
    variants={}
    for radius in RADII:
        fine=len(SIZES_MM)-1;fd=proxy_data['variants'][str(radius)]['split']
        convergence={str(w):HYD.FILLETS.richardson([r['mass_flow_kg_s'] for r in rows if (r['fillet_radius_mm'],r['width_mm'],r['pressure_factor'])==(radius,w,CONVERGENCE_FACTOR)],RATIO) for w in sorted(set(widths))}
        curves={w:fit([r for r in rows if (r['fillet_radius_mm'],r['width_mm'],r['level'])==(radius,w,fine)]) for w in set(widths)}
        result=split([curves[w] for w in widths])
        variants[str(radius)]={'mass_flow_convergence_at_0_95_proxy_dp':convergence,'finest_fit_a_b':{str(w):list(curves[w]) for w in sorted(set(widths))},'finest_split':result,
                               'fully_developed_proxy_pressure_drop_pa':fd['pressure_drop_pa'],'finest_over_proxy':result['pressure_drop_pa']/fd['pressure_drop_pa'],
                               'proxy_channel_mass_flow_kg_s':[c['mass_flow_kg_s'] for c in fd['channels']]}
    result={'status':'exploratory_isothermal_laminar_channel_cfd','fillet_radii_are_assumptions':True,'image_id_declared_by_runner':image,'python':platform.python_version(),
            'element_sizes_mm':SIZES_MM,'refinement_ratio':RATIO,'convergence_pressure_factor':CONVERGENCE_FACTOR,'fit_pressure_factor':FIT_FACTOR,'clear_widths_mm':widths,'channel_length_mm':LENGTH_MM,'channel_height_mm':HEIGHT_MM,
            'boundary_conditions':'uniform total pressure inlet (quiescent plenum), uniform static outlet, no-slip walls, two symmetry planes; isothermal incompressible laminar',
            'cases':rows,'variants':variants,
            'not_resolved':['headers, manifolds and the real inlet distribution','sharp-edge inlet separation (vena contracta)','LPBF roughness','compressibility and heat transfer'],
            'hydraulic_performance_accepted':False,'thermal_gain_claimed':False,'manufacturing_authorized':False,'resolved_thermal_or_flow_simulation':False,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dependency_hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'source/fillet_hydraulics.py',proxy]}}
    (output/'channel-cfd.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--proxy',type=Path,required=True,help='fillet-hydraulics.json')
    p.add_argument('--image-id',required=True);p.add_argument('--workers',type=int,default=4);args=p.parse_args();run(args.output,args.proxy.resolve(),args.image_id,args.workers)
