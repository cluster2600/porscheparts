"""Hydraulic proxy of the four-rib hot section with assumed rib-root fillets; no performance acceptance.

Runs inside the cadsim image (gmsh, numpy and scipy). The fillet radii are the design
assumptions of fillet_convergence.py, not measured or printed values. study.py is reused
unchanged for the gas state, the total mass flow and the rectangular reference.

Each channel cross-section is meshed with isoparametric 6-node triangles and the fully
developed laminar problem -lap(w) = 1, w = 0 on the wall, is solved by finite elements.
The flow rate is then Q = (-dp/dx) / mu * W with W the integral of w, so the friction
pressure drop of one channel is mu * L * mdot / (rho * W) and the Darcy f*Re is
2 * A * Dh**2 / W. The equal-pressure split and the assumed K = 2 follow study.py.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[3]
_spec=importlib.util.spec_from_file_location('pressure_coupon_study',ROOT/'source/study.py');STUDY=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(STUDY)
_spec=importlib.util.spec_from_file_location('pressure_coupon_fillets',ROOT/'source/fillet_convergence.py');FILLETS=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(FILLETS)
sys.path.insert(0,str(ROOT.parent/'source'))
from size_core import properties
RIBS=4;HEIGHT_MM=3.;LENGTH_M=.024;ENTRY_K=2.
# Same gas state and smooth-passage reference flow as study.hydraulic (1 m/s through 22.4 x 3 mm).
TEMPERATURE_K=506.46954;PRESSURE_PA=303975.;CP=1005.;GAS=287.05
RADII=FILLETS.RADII;SIZES_MM=[.2,.1,.05,.025]
# Six-point degree-4 Dunavant rule on the reference triangle (weights sum to 1).
QUADRATURE=[(a,b,w) for p,q,w in [(.445948490915965,.10810301816807,.223381589678011),(.091576213509771,.816847572980459,.109951743655322)] for a,b in [(p,p),(p,q),(q,p)]]


def widths():
    """Full clear widths of the five hot channels, from the same edges as fillet_convergence.py."""
    edges=sorted([-FILLETS.SIDE,FILLETS.SIDE]+[s*c+d for s in (-1,1) for c in STUDY.centres(RIBS) for d in (-FILLETS.RIB_HALF,FILLETS.RIB_HALF)])
    return [round(b-a,12) for a,b in zip(edges[::2],edges[1::2])]


def rectangle_w_integral(width,height,terms=200):
    """Exact series for the integral of w over a sharp rectangle (Shah and London, mm**4)."""
    a,b=min(width,height)/2,max(width,height)/2
    series=sum(math.tanh(n*math.pi*b/(2*a))/n**5 for n in range(1,2*terms,2))
    return 4*b*a**3/3*(1-192*a/(math.pi**5*b)*series)


def channel_area(width,height,radius):
    return width*height-4*(1-math.pi/4)*radius*radius


def channel_perimeter(width,height,radius):
    return 2*(width+height)-8*radius+2*math.pi*radius


def solve_section(width,height,radius,size):
    """P2 isoparametric FE solution of -lap(w)=1 on one rounded-corner channel section, mm units."""
    import gmsh
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
    try:
        occ=gmsh.model.occ;surface=occ.addRectangle(0,0,0,width,height,roundedRadius=radius);occ.synchronize()
        cad_area=occ.getMass(2,surface);curves=[c for _,c in gmsh.model.getBoundary([(2,surface)],oriented=False)];cad_perimeter=sum(occ.getMass(1,c) for c in curves)
        for name,value in [('Mesh.MeshSizeMin',size),('Mesh.MeshSizeMax',size),('Mesh.MeshSizeFromCurvature',0),('Mesh.MeshSizeExtendFromBoundary',0),('Mesh.Algorithm',6),('Mesh.ElementOrder',2),('Mesh.HighOrderOptimize',0)]:gmsh.option.setNumber(name,value)
        gmsh.model.mesh.generate(2)
        tags,coords,_=gmsh.model.mesh.getNodes()
        if len(set(tags))!=len(tags):raise ValueError('Duplicate mesh nodes')
        index={int(t):i for i,t in enumerate(tags)};xy=np.asarray(coords).reshape(-1,3)[:,:2]
        types,_,connectivity=gmsh.model.mesh.getElements(2,surface)
        if list(types)!=[9]:raise ValueError(f'Expected only 6-node triangles, got types {list(types)}')
        tri=np.array([index[int(n)] for n in connectivity[0]]).reshape(-1,6)
        wall=set()
        for c in curves:wall.update(index[int(t)] for t in gmsh.model.mesh.getNodes(1,c,includeBoundary=True)[0])
        version=gmsh.__version__
    finally:
        gmsh.finalize()
    # gmsh 6-node triangle: vertices 0,1,2 then edge nodes (0,1), (1,2), (2,0).
    n=len(xy);rows=[];cols=[];vals=[];load=np.zeros(n);area=0.;min_jacobian=math.inf
    xe=xy[tri]
    for xi,eta,weight in QUADRATURE:
        l=1-xi-eta
        shape=np.array([l*(2*l-1),xi*(2*xi-1),eta*(2*eta-1),4*l*xi,4*xi*eta,4*eta*l])
        dxi=np.array([1-4*l,4*xi-1,0,4*(l-xi),4*eta,-4*eta]);deta=np.array([1-4*l,0,4*eta-1,-4*xi,4*xi,4*(l-eta)])
        jac=np.stack([np.einsum('k,ekd->ed',dxi,xe),np.einsum('k,ekd->ed',deta,xe)],axis=1)
        det=jac[:,0,0]*jac[:,1,1]-jac[:,0,1]*jac[:,1,0];min_jacobian=min(min_jacobian,float(det.min()))
        inv=np.stack([np.stack([jac[:,1,1],-jac[:,0,1]],-1),np.stack([-jac[:,1,0],jac[:,0,0]],-1)],1)/det[:,None,None]
        grad=np.einsum('edr,rk->ekd',inv,np.stack([dxi,deta]))
        scale=.5*weight*det
        ke=np.einsum('e,ekd,eld->ekl',scale,grad,grad)
        rows.append(np.repeat(tri,6,axis=1).ravel());cols.append(np.tile(tri,(1,6)).ravel());vals.append(ke.ravel())
        np.add.at(load,tri.ravel(),(scale[:,None]*shape[None,:]).ravel());area+=float(scale.sum())
    if min_jacobian<=0:raise ValueError('Inverted element')
    stiffness=coo_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(n,n)).tocsr()
    free=np.array(sorted(set(range(n))-wall));w=np.zeros(n);w[free]=spsolve(stiffness[free][:,free].tocsc(),load[free])
    w_integral=float(load@w)
    return {'width_mm':width,'height_mm':height,'fillet_radius_mm':radius,'fillet_radius_is_assumption':True,'element_size_mm':size,'nodes':n,'elements':len(tri),
            'fe_area_mm2':area,'cad_area_mm2':cad_area,'analytic_area_mm2':channel_area(width,height,radius),'cad_perimeter_mm':cad_perimeter,'analytic_perimeter_mm':channel_perimeter(width,height,radius),
            'w_integral_mm4':w_integral,'maximum_w_mm2':float(w.max()),'gmsh_version':version}


def friction_re(area,perimeter,w_integral):
    dh=4*area/perimeter
    return 2*area*dh*dh/w_integral


def gas():
    rho,mu,_=properties(TEMPERATURE_K,PRESSURE_PA,CP,GAS)
    return rho,mu,rho*.0224*.003*1.


def split(channels):
    """Equal-pressure split at the study's total mass flow; channels carry area_m2 and w_integral_m4."""
    rho,mu,total=gas();coeff=[(mu*LENGTH_M/(rho*c['w_integral_m4']),ENTRY_K/(2*rho*c['area_m2']**2)) for c in channels]
    def flows(dp):return [2*dp/(r+math.sqrt(r*r+4*b*dp)) for r,b in coeff]
    lo,hi=0.,1000.
    for _ in range(70):
        mid=(lo+hi)/2
        if sum(flows(mid))<total:lo=mid
        else:hi=mid
    out=[]
    for c,m,(r,b) in zip(channels,flows(hi),coeff):
        dh=4*c['area_m2']/c['perimeter_m'];re=m*dh/(c['area_m2']*mu)
        out.append({'mass_flow_kg_s':m,'velocity_m_s':m/(rho*c['area_m2']),'re':re,'dh_m':dh,'friction_pressure_drop_pa':r*m,'entry_pressure_drop_pa':b*m*m,'pressure_drop_pa':r*m+b*m*m,
                    # Laminar hydrodynamic entrance length about 0.05 Re Dh: above 1 the channel never becomes fully developed.
                    'hydrodynamic_entry_length_over_length':.05*re*dh/LENGTH_M})
    if any(c['re']>=2300 for c in out):raise ValueError('Laminar model invalid')
    return {'pressure_drop_pa':hi,'total_mass_flow_kg_s':total,'mass_flow_closure':sum(c['mass_flow_kg_s'] for c in out)/total-1,'channels':out}


def run(output,image):
    if output.exists():raise FileExistsError(output)
    import numpy,scipy
    output.mkdir(parents=True);w=widths();sections=[]
    for radius in RADII:
        for width in sorted(set(w)):
            for size in SIZES_MM:
                row=solve_section(width,HEIGHT_MM,radius,size);sections.append(row);print(radius,width,size,row['elements'],row['w_integral_mm4'],flush=True)
    variants={}
    for radius in RADII:
        finest={width:next(s for s in sections if (s['fillet_radius_mm'],s['width_mm'],s['element_size_mm'])==(radius,width,SIZES_MM[-1])) for width in set(w)}
        convergence={str(width):FILLETS.richardson([s['w_integral_mm4'] for s in sections if (s['fillet_radius_mm'],s['width_mm'])==(radius,width)]) for width in sorted(set(w))}
        channels=[{'width_mm':x,'area_m2':finest[x]['fe_area_mm2']*1e-6,'perimeter_m':finest[x]['cad_perimeter_mm']*1e-3,'w_integral_m4':finest[x]['w_integral_mm4']*1e-12,
                   'friction_re':friction_re(finest[x]['fe_area_mm2'],finest[x]['cad_perimeter_mm'],finest[x]['w_integral_mm4'])} for x in w]
        variants[str(radius)]={'fillet_radius_mm':radius,'open_area_mm2':sum(c['area_m2'] for c in channels)*1e6,'w_integral_convergence':convergence,'channel_sections':channels,'split':split(channels)}
    sharp_series=[{'width_mm':x,'area_m2':x*HEIGHT_MM*1e-6,'perimeter_m':2*(x+HEIGHT_MM)*1e-3,'w_integral_m4':rectangle_w_integral(x,HEIGHT_MM)*1e-12} for x in w]
    study_proxy=STUDY.hydraulic(RIBS)
    result={'status':'conditional_fully_developed_laminar_hydraulic_proxy','fillet_radii_are_assumptions':True,'image_id_declared_by_runner':image,'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__,
            'rib_count':RIBS,'channel_height_mm':HEIGHT_MM,'channel_length_m':LENGTH_M,'assumed_entry_k':ENTRY_K,'temperature_k':TEMPERATURE_K,'pressure_pa':PRESSURE_PA,'element_sizes_mm':SIZES_MM,'clear_widths_mm':w,
            'sections':sections,'variants':variants,'sharp_exact_series_split':split(sharp_series),
            'study_rectangular_proxy':{'pressure_drop_pa':study_proxy['pressure_drop_pa'],'total_mass_flow_kg_s':study_proxy['total_mass_flow_kg_s']},
            'not_resolved':['developing flow at the channel entrances (entry lengths exceed the 24 mm channel)','LPBF roughness','headers and real flow distribution','compressibility and heat transfer'],
            'hydraulic_performance_accepted':False,'thermal_gain_claimed':False,'manufacturing_authorized':False,'resolved_thermal_or_flow_simulation':False,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'dependency_hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'source/study.py',ROOT/'source/fillet_convergence.py',ROOT.parent/'source/size_core.py']}}
    (output/'fillet-hydraulics.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--image-id',required=True);args=p.parse_args();run(args.output,args.image_id)
