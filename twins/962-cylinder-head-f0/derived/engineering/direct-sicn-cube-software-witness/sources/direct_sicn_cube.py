"""One held 9-node software witness: direct signed-SICN SLSQP, never a head run."""
from collections import defaultdict
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

OUTPUT_NAME = 'direct-sicn-cube-002'
LIMITS = dict(wall_seconds=30, sampled_RSS_bytes=1024**3,
              sampled_output_bytes=16*1024**2, threads=2)
SOLVER = dict(method='SLSQP', maxiter=100, ftol=1e-10, eps=2.0**-26)
OPTIONS = {'General.NumThreads':2,'Mesh.Renumber':0,'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,
           'Mesh.MshFileVersion':4.1,'Mesh.Binary':1,'Mesh.SaveAll':1}
GATE = .1
NODE_TAGS = tuple(range(101, 109)) + (201,)
TET_TAGS = tuple(range(2001, 2013))
TRI_TAGS = tuple(range(1001, 1013))
BOUNDARY = ((-1.,-1.,-1.),(1.,-1.,-1.),(1.,1.,-1.),(-1.,1.,-1.),
            (-1.,-1.,1.),(1.,-1.,1.),(1.,1.,1.),(-1.,1.,1.))
TRIANGLES = ((101,103,102),(101,104,103),(105,106,107),(105,107,108),
             (101,102,106),(101,106,105),(104,108,107),(104,107,103),
             (101,105,108),(101,108,104),(102,103,107),(102,107,106))
TETS = tuple((201,)+f for f in TRIANGLES)
INITIAL = (63./64., 1./4., -1./8.)
CENTRE = (0., 0., 0.)
QUALIFICATION = dict(head_optimization_authorized=False, engineering_accepted=False,
                     physics_qualified=False, manufacturing_authorized=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def sub(a, b):
    return tuple(x-y for x,y in zip(a,b))


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def signed_sicn(points, allow_planar=False):
    """Gmsh ideal-reference inverse Frobenius expression; no inverse/regularizer."""
    if len(points)!=4 or any(len(p)!=3 or any(not math.isfinite(x) for x in p) for p in points):
        raise ValueError('Four finite triples required')
    e1,e2,e3 = (sub(p,points[0]) for p in points[1:])
    a=e1; b=tuple((2*y-x)/math.sqrt(3.) for x,y in zip(e1,e2))
    c=tuple(math.sqrt(1.5)*(z-(x+y)/3.) for x,y,z in zip(e1,e2,e3))
    determinant=dot(a,cross(b,c))
    denominator2=(dot(a,a)+dot(b,b)+dot(c,c))*sum(dot(v,v) for v in (cross(b,c),cross(c,a),cross(a,b)))
    if not math.isfinite(denominator2) or denominator2<=0 or not math.isfinite(determinant):
        raise ValueError('Singular or nonfinite signed-SICN evaluation')
    if determinant==0 and not allow_planar:
        raise ValueError('Degenerate iterate is refused; no epsilon regularization')
    return 3.*determinant/math.sqrt(denominator2)


def cube_qualities(interior):
    points=dict(zip(NODE_TAGS, BOUNDARY+(tuple(interior),)))
    return tuple(signed_sicn([points[t] for t in cell]) for cell in TETS)


def same_numpy(module, original, expected_origin):
    if module is not original or module.__version__!='2.2.6' or Path(module.__file__).resolve()!=Path(expected_origin).resolve():
        raise ValueError('The selected local NumPy object/version/origin must remain unchanged')


def require_contract_fields(c):
    if (c.get('schema')!='962-direct-sicn-cube/v1' or c.get('scope')!='tiny_cube_software_only'
            or c.get('native_execution_authorized') is not True
            or c.get('root_and_peer_review_complete') is not True
            or c.get('selected_runtime_review_complete') is not True
            or c.get('qualification')!=QUALIFICATION or c.get('limits')!=LIMITS
            or c.get('solver')!=SOLVER or c.get('options')!=OPTIONS or c.get('sicn_gate')!=GATE):
        raise ValueError('A separately reviewed exact tiny-witness child is required')
    maps=(c.get('input_hashes'), c.get('runtime_files'))
    if any(not isinstance(m,dict) or not m for m in maps):
        raise ValueError('Complete source map and selected runtime pins required')
    for mapping in maps:
        if any(not isinstance(p,str) or not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h) for p,h in mapping.items()):
            raise ValueError('Unknown/null source or runtime pins cannot authorize execution')
    if (not isinstance(c.get('numpy_init'),str) or not isinstance(c.get('scipy_directory'),str)
            or not isinstance(c.get('gmsh_module'),str)):
        raise ValueError('Exact package and Gmsh ctypes-wrapper origins required')
    if str(Path(c['gmsh_module']).resolve()) not in c['runtime_files']:
        raise ValueError('Exact Gmsh ctypes-wrapper source requires a selected runtime pin')
    return c


def bound_contract(path, digest):
    if not re.fullmatch('[0-9a-f]{64}',digest) or sha(path)!=digest:
        raise ValueError('Exact external contract digest required')
    c=require_contract_fields(json.loads(Path(path).read_text()))
    for mapping in (c['input_hashes'],c['runtime_files']):
        for name,value in mapping.items():
            p=Path(name)
            if not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=value:
                raise ValueError('A frozen input/runtime file changed')
    if c.get('reader_sha256')!=sha(__file__) or c.get('runner_sha256')!=sha(Path(__file__).with_name('run_readback.py')):
        raise ValueError('Materialized reader and reviewed runner must be explicitly bound')
    if c['runtime_files'].get(str(Path(sys.executable).resolve()))!=sha(Path(sys.executable).resolve()):
        raise ValueError('Selected interpreter must be explicitly bound')
    output=Path(c['output'])
    if output.name!=OUTPUT_NAME or not output.is_absolute() or output.resolve()!=output:
        raise ValueError('Exact declared fresh output required')
    return c


def loaded_files(c):
    """Supplementary loaded-file inventory, not a prebound complete package/OS closure."""
    rows={}
    for name,module in tuple(sys.modules.items()):
        if name=='numpy' or name.startswith('numpy.') or name=='scipy' or name.startswith('scipy.'):
            filename=getattr(module,'__file__',None)
            if filename:
                p=Path(filename).resolve(); package=Path(c['numpy_init']).resolve().parent if name.split('.')[0]=='numpy' else Path(c['scipy_directory']).resolve()
                if not p.is_relative_to(package):raise ValueError('Loaded scientific module escaped the selected package origin')
                actual=sha(p); expected=c['runtime_files'].get(str(p))
                if expected is not None and actual!=expected:raise ValueError('A selected scientific module changed')
                rows[str(p)]=dict(sha256=actual,selected_prebound=expected is not None)
    return rows


def scientific_modules(c):
    # No parent user-site directory is added to sys.path; never expose its NumPy.
    import numpy as np
    same_numpy(np,np,c['numpy_init']); original=np; old_path=tuple(sys.path)
    directory=Path(c['scipy_directory']).resolve()
    if directory.name!='scipy' or 'scipy' in sys.modules:
        raise ValueError('Only the initially unloaded exact named SciPy package is permitted')
    spec=importlib.util.spec_from_file_location('scipy',directory/'__init__.py',submodule_search_locations=[str(directory)])
    scipy=importlib.util.module_from_spec(spec); sys.modules['scipy']=scipy
    spec.loader.exec_module(scipy)
    optimize=importlib.import_module('scipy.optimize')
    if (scipy.__version__!='1.17.1' or Path(scipy.__file__).resolve()!=directory/'__init__.py'
            or tuple(sys.path)!=old_path):
        raise ValueError('SciPy version/origin or search path changed')
    same_numpy(sys.modules['numpy'],original,c['numpy_init']); loaded_files(c)
    gmsh_path=Path(c['gmsh_module']).resolve()
    if 'gmsh' in sys.modules:raise ValueError('Only the initially unloaded exact Gmsh ctypes wrapper is permitted')
    gmsh_spec=importlib.util.spec_from_file_location('gmsh',gmsh_path)
    gmsh=importlib.util.module_from_spec(gmsh_spec);sys.modules['gmsh']=gmsh
    gmsh_spec.loader.exec_module(gmsh)
    if Path(gmsh.__file__).resolve()!=gmsh_path or tuple(sys.path)!=old_path:
        raise ValueError('Gmsh ctypes-wrapper origin or search path changed')
    same_numpy(sys.modules['numpy'],original,c['numpy_init'])
    for filename in (gmsh.__file__,gmsh.lib._name):
        p=Path(filename).resolve()
        if c['runtime_files'].get(str(p))!=sha(p):
            raise ValueError('Gmsh module/library pin changed')
    if gmsh.__version__!='4.15.2':raise ValueError('Pinned Gmsh version required')
    return np,gmsh,optimize,original


def calibration(gmsh):
    regular=((0.,0.,0.),(1.,0.,0.),(.5,math.sqrt(3.)/2.,0.),(.5,math.sqrt(3.)/6.,math.sqrt(2./3.)))
    sliver=tuple((x,y,z*.001) for x,y,z in regular)
    planar=tuple((x,y,0.) for x,y,z in regular)
    rows=[]
    for name,points,expected_sign in [('regular',regular,1),('sliver',sliver,1),
            ('reversed',(regular[1],regular[0],regular[2],regular[3]),-1),('planar',planar,0)]:
        gmsh.clear(); gmsh.model.add(name); gmsh.model.addDiscreteEntity(3,1)
        gmsh.model.mesh.addNodes(3,1,[1,2,3,4],[x for p in points for x in p])
        gmsh.model.mesh.addElementsByType(1,4,[1],[1,2,3,4])
        native=float(gmsh.model.mesh.getElementQualities([1],'minSICN')[0])
        analytic=signed_sicn(points,allow_planar=name=='planar')
        if not math.isfinite(native) or not math.isclose(native,analytic,rel_tol=1e-11,abs_tol=1e-14):
            raise ValueError('Native signed-SICN normalization/sign/degeneracy calibration failed')
        if (native>0)-(native<0)!=expected_sign:
            raise ValueError('Native orientation/degenerate sign witness failed')
        rows.append(dict(case=name,native_minSICN=native,analytic_signed_SICN=analytic))
    return rows


def canonical(face):
    k=face.index(min(face)); return face[k:]+face[:k]


def inspect_cube(gmsh, np):
    nt,xyz,_=gmsh.model.mesh.getNodes(); order=np.argsort(nt)
    nt=np.asarray(nt,dtype='<u8')[order]; xyz=np.asarray(xyz,dtype='<f8').reshape(-1,3)[order]
    types,ets,connect=gmsh.model.mesh.getElements(3)
    if list(types)!=[4]:raise ValueError('Only literal TET4 volume cells permitted')
    order=np.argsort(ets[0]); et=np.asarray(ets[0],dtype='<u8')[order]
    conn=np.asarray(connect[0],dtype='<u8').reshape(-1,4)[order]
    stypes,sts,sconn=gmsh.model.mesh.getElements(2)
    if list(stypes)!=[2]:raise ValueError('Only the literal boundary TRI3 cells permitted')
    order=np.argsort(sts[0]); st=np.asarray(sts[0],dtype='<u8')[order]
    sc=np.asarray(sconn[0],dtype='<u8').reshape(-1,3)[order]
    if (nt.tolist()!=list(NODE_TAGS) or et.tolist()!=list(TET_TAGS) or conn.tolist()!=[list(t) for t in TETS]
            or st.tolist()!=list(TRI_TAGS) or sc.tolist()!=[list(t) for t in TRIANGLES]
            or not np.isfinite(xyz).all() or len(np.unique(xyz,axis=0))!=9
            or xyz[:8].tobytes()!=np.asarray(BOUNDARY,dtype='<f8').tobytes()
            or set(conn.ravel().tolist())!=set(NODE_TAGS)):
        raise ValueError('Complete literal tags/connectivity/boundary bits/reference set changed')
    classes={}
    for dim,entity in gmsh.model.getEntities():
        for tag in gmsh.model.mesh.getNodes(dim,entity,includeBoundary=False)[0]:
            if int(tag) in classes:raise ValueError('Duplicate node classification')
            classes[int(tag)]=[int(dim),int(entity)]
        if dim in (1,2):
            master,nodes,masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,entity,True)
            if (list(gmsh.model.mesh.getPeriodic(dim,[entity]))!=[entity] or master!=entity
                    or len(nodes) or len(masters) or len(transform)):
                raise ValueError('Periodic node mapping is not permitted')
    if classes!={**{t:[2,1] for t in NODE_TAGS[:8]},201:[3,1]}:
        raise ValueError('Exact boundary/interior classification changed')
    phys=sorted((int(d),int(t),gmsh.model.getPhysicalName(d,t),list(map(int,gmsh.model.getEntitiesForPhysicalGroup(d,t))))
                for d,t in gmsh.model.getPhysicalGroups())
    if phys!=[(2,11,'all_boundary',[1]),(3,21,'solid',[1])]:raise ValueError('Physical groups changed')
    incidence=defaultdict(list)
    for cell in TETS:
        for positions in ((0,2,1),(0,1,3),(1,2,3),(2,0,3)):
            face=tuple(cell[i] for i in positions); incidence[tuple(sorted(face))].append(canonical(face))
    exterior=[]
    for row in incidence.values():
        if len(row)==1:exterior.append(row[0])
        elif len(row)!=2 or row[0]!=canonical(tuple(reversed(row[1]))):
            raise ValueError('Full tetra incidence/internal opposite orientation failed')
    if sorted(exterior)!=sorted(canonical(t) for t in TRIANGLES):raise ValueError('Whole oriented boundary changed')
    p=dict(zip(NODE_TAGS,xyz.tolist())); signed=[]; analytic=[]
    for cell in TETS:
        a,b,c,d=(p[t] for t in cell)
        signed.append(dot(sub(b,a),cross(sub(c,a),sub(d,a)))/6.)
        analytic.append(signed_sicn([a,b,c,d]))
    qualities={metric:list(map(float,gmsh.model.mesh.getElementQualities(list(TET_TAGS),metric)))
               for metric in ('minSICN','minDetJac','volume')}
    if (any(len(v)!=12 or any(not math.isfinite(x) or x<=0 for x in v) for v in qualities.values())
            or any(not math.isfinite(v) or v<=0 for v in signed) or not math.isclose(sum(signed),8.,rel_tol=1e-6)
            or any(not math.isclose(q,n,rel_tol=1e-11,abs_tol=1e-14) for q,n in zip(analytic,qualities['minSICN']))):
        raise ValueError('Full native/analytic metrics/counts/positive signed volume calibration failed')
    arrays=dict(node_tags=nt,coordinates=xyz,tet_tags=et,connectivity=conn,triangle_tags=st,triangles=sc)
    return dict(array_sha256s={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in arrays.items()},
                coordinates_mm=xyz.tolist(),node_tags=nt.tolist(),tet_tags=et.tolist(),connectivity=conn.tolist(),
                triangle_tags=st.tolist(),triangles=sc.tolist(),classifications=classes,physical_groups=phys,
                qualities=qualities,analytic_SICN=analytic,signed_volumes_mm3=signed,total_volume_mm3=sum(signed),
                no_orphans=True,complete_opposite_internal_faces=True,exact_source_boundary_bits=True)


def worker(c,contract_path,contract_sha):
    out=Path(c['output']); report=dict(status='running',stage='imports',qualification=QUALIFICATION,
        scipy_minimize_calls_attempted=0,gmsh_generate_calls=0,gmsh_optimize_calls=0)
    save(out/'worker-claimed.json',dict(contract_sha256=contract_sha))
    gmsh=None
    try:
        np,gmsh,optimize,original=scientific_modules(c)
        report['loaded_scientific_files_before']=loaded_files(c)
        gmsh.initialize([],readConfigFiles=False,run=False)
        gmsh.option.setNumber('General.Terminal',0)
        for name,value in OPTIONS.items():gmsh.option.setNumber(name,value)
        report['calibration']=calibration(gmsh); print('calibration complete',flush=True)
        gmsh.clear();gmsh.model.add('literal_cube_star')
        gmsh.model.addDiscreteEntity(2,1);gmsh.model.addDiscreteEntity(3,1,[1])
        gmsh.model.mesh.addNodes(2,1,list(NODE_TAGS[:8]),[v for p in BOUNDARY for v in p])
        gmsh.model.mesh.addNodes(3,1,[201],list(INITIAL))
        gmsh.model.mesh.addElementsByType(1,2,list(TRI_TAGS),[v for t in TRIANGLES for v in t])
        gmsh.model.mesh.addElementsByType(1,4,list(TET_TAGS),[v for t in TETS for v in t])
        gmsh.model.addPhysicalGroup(2,[1],11);gmsh.model.setPhysicalName(2,11,'all_boundary')
        gmsh.model.addPhysicalGroup(3,[1],21);gmsh.model.setPhysicalName(3,21,'solid')
        report['stage']='before_and_centre'; before=inspect_cube(gmsh,np);report['before']=before
        gmsh.model.mesh.setNode(201,list(CENTRE),[]); centre=inspect_cube(gmsh,np);report['centre_reference']=centre
        gmsh.model.mesh.setNode(201,list(INITIAL),[])
        if inspect_cube(gmsh,np)!=before:raise ValueError('Restoring the literal initial state changed identity')
        initial_min=min(before['qualities']['minSICN'])
        if not 0<initial_min<GATE or min(centre['qualities']['minSICN'])<GATE:
            raise ValueError('Literal poor start / known feasible centre witness failed')
        report['stage']='one_SLSQP';print('one SLSQP call begins',flush=True)
        # All twelve coupled cells; no per-cell optimizer, retry, clipping or projection.
        report['scipy_minimize_calls_attempted']=1
        result=optimize.minimize(lambda x:-x[3], np.asarray([*INITIAL,initial_min]),
            method='SLSQP',bounds=[(None,None)]*3+[(initial_min,1.)],
            constraints=[dict(type='ineq',fun=lambda x:np.asarray(cube_qualities(x[:3]))-x[3])],
            options={k:SOLVER[k] for k in ('maxiter','ftol','eps')})
        report['solver']=dict(calls=1,success=bool(result.success),status=int(result.status),message=str(result.message),
            nit=int(result.nit),nfev=int(result.nfev),njev=int(result.njev),x=list(map(float,result.x)),fun=float(result.fun))
        if len(result.x)!=4 or any(not math.isfinite(float(x)) for x in result.x) or not result.success:
            raise ValueError('The single SLSQP call did not return a finite successful result')
        same_numpy(sys.modules['numpy'],original,c['numpy_init']);report['loaded_scientific_files_after']=loaded_files(c)
        if any(report['loaded_scientific_files_after'].get(p)!=v for p,v in report['loaded_scientific_files_before'].items()):
            raise ValueError('A previously loaded scientific file changed during the single call')
        report['stage']='after'; gmsh.model.mesh.setNode(201,list(map(float,result.x[:3])),[])
        after=inspect_cube(gmsh,np);report['after']=after
        if min(after['qualities']['minSICN'])<GATE:
            raise ValueError('Native all-cell SICN >= 0.1 gate failed; no retry')
        for key in before['array_sha256s']:
            if key!='coordinates' and before['array_sha256s'][key]!=after['array_sha256s'][key]:
                raise ValueError('Tags/connectivity/surface changed')
        if before['classifications']!=after['classifications']:raise ValueError('Classification changed')
        report['stage']='save_reopen'
        mesh=out/'cube.msh';gmsh.write(str(mesh));gmsh.clear();gmsh.open(str(mesh))
        saved=inspect_cube(gmsh,np);report['saved']=saved
        if saved!=after:raise ValueError('Every saved array/classification/metric must be byte-identical')
        same_numpy(sys.modules['numpy'],original,c['numpy_init']);loaded_files(c)
        bound_contract(contract_path,contract_sha)
        report.update(status='completed_tiny_software_witness',stage='completed',cube_SICN_gate_passed=True,
            saved_mesh_identity_exact=True,mesh_sha256=sha(mesh),mesh_bytes=mesh.stat().st_size,
            head_stronger_Mesh2_criterion_satisfied=False,head_optimization_performed=False,
            gmsh_generate_calls=0,gmsh_optimize_calls=0,scipy_minimize_calls=1)
    except Exception as error:
        report.update(status='refused_or_failed',error_type=type(error).__name__,error=str(error),cube_SICN_gate_passed=False)
    finally:
        try:
            if gmsh is not None and gmsh.isInitialized():gmsh.finalize()
        except Exception as error:
            report.update(status='refused_or_failed',finalize_error_type=type(error).__name__,cube_SICN_gate_passed=False)
        save(out/'fixture-report.json',report)
    return 0 if report['status']=='completed_tiny_software_witness' else 2


def main():
    # The separately reviewed existing cube controller owns the fresh directory/log.
    out=Path(__file__).resolve().parent;path=out/'frozen-contract.json';digest=sha(path)
    c=bound_contract(path,digest)
    if (Path(c['output'])!=out or {p.name for p in out.iterdir()}!=
            {'reader.py','run_readback.py','frozen-contract.json','native.log'}):
        raise ValueError('Worker requires exact fresh controller-owned materialization')
    return worker(c,path,digest)


if __name__=='__main__':raise SystemExit(main())
