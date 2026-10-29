"""Generate explicit normalized research cells with independently audited periodic T10 meshes."""
import argparse,hashlib,importlib,json,time
from pathlib import Path
import numpy as np

EDGES=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)]


def audit_periodicity(points, tolerance=1e-8):
    from scipy.spatial import cKDTree
    if not 0<tolerance<=1e-8:raise ValueError('The boundary tolerance must not exceed the fixed 1e-8 gate')
    points=np.asarray(points)
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():raise ValueError('Finite three-dimensional points required')
    if not np.allclose(points.min(0),-.5,atol=tolerance,rtol=0) or not np.allclose(points.max(0),.5,atol=tolerance,rtol=0):raise ValueError('Normalized research-cell bounds differ')
    rows=[]
    for axis in range(3):
        low=points[abs(points[:,axis]+.5)<=tolerance];high=points[abs(points[:,axis]-.5)<=tolerance];shift=np.eye(3)[axis]
        if not len(low) or len(low)!=len(high):raise ValueError('Opposite boundary rosters differ')
        errors=[]
        for source,target,translation in [(high,low,-shift),(low,high,shift)]:
            distance,index=cKDTree(target).query(source+translation)
            if distance.max()>tolerance or len(np.unique(index))!=len(target):raise ValueError('Opposite boundary matching is not a bijection within the fixed tolerance')
            errors.append(float(distance.max()))
        rows.append(dict(axis=axis,nodes_per_face=len(low),maximum_pair_error=max(errors)))
    return rows


def audit_t10(points,cells):
    if cells.ndim!=2 or cells.shape[1]!=10 or not len(cells):raise ValueError('Complete T10 elements required')
    x=points[cells];J=(x[:,1:4]-x[:,0,None,:]).transpose(0,2,1);det=np.linalg.det(J)
    if not np.all(np.isfinite(det)&(det>0)):raise ValueError('Nonpositive affine corner tetrahedron')
    delta=np.stack([x[:,4+k]-(x[:,a]+x[:,b])/2 for k,(a,b)in enumerate(EDGES)],axis=1)
    eps=4*np.sum(abs(delta),axis=1);bound=3*np.max(np.einsum('nij,nj->ni',abs(np.linalg.inv(J)),eps),axis=1)
    if not np.all(bound<1):raise ValueError('Whole-simplex quadratic Jacobian perturbation bound refused')
    return dict(minimum_corner_determinant=float(det.min()),maximum_midpoint_deviation=float(abs(delta).max()),whole_simplex_relative_Jacobian_bound=float(bound.max()),floating_point_sufficient_bound=True,formal_interval_certificate=False,volume_mm3=float(det.sum()/6))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--kind',choices=['cube','gyroid'],required=True);p.add_argument('--resolution',type=int,default=24);p.add_argument('--size',type=float,required=True);p.add_argument('--step',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists()or not 16<=a.resolution<=64 or not .015<=a.size<=.25:raise ValueError('Fresh bounded research-cell output required')
    import microgen,cadquery as cq,gmsh,meshio
    from importlib.metadata import version
    if version('microgen')!='1.3.2':raise ValueError('This orchestration adapter requires the inspected Microgen 1.3.2 API')
    start=time.monotonic();a.output.mkdir();threshold=.6170021750539874
    if a.step:
        solids=cq.importers.importStep(str(a.step)).solids().vals();shape=cq.Compound.makeCompound(solids);step=a.output/'cell.step';step.write_bytes(a.step.read_bytes())
    else:
        if a.kind=='cube':shape=cq.Workplane('XY').box(1,1,1).val()
        else:
            def field(x,y,z):return np.sin(x)*np.cos(y)+np.sin(y)*np.cos(z)+np.sin(z)*np.cos(x)
            g=microgen.Tpms(surface_function=field,offset=2*threshold,cell_size=1.,repeat_cell=1,resolution=a.resolution)
            surface=g.generate_vtk(type_part='sheet');surface.save(a.output/'surface.vtp');shape=g.generate(type_part='sheet',smoothing=0)
        step=a.output/'cell.step';cq.exporters.export(shape,str(step))
    if not shape.isValid()or not 0<shape.Volume()<=1.00000001:raise ValueError('Invalid or nonpositive research-cell solid')
    module=importlib.import_module('microgen.mesh');initialize=module._initialize_mesh
    def initialize_quadratic(*args,**kwargs):
        initialize(*args,**kwargs)
        # Microgen 1.3.2 calls setOrder before elements exist; ElementOrder controls generation.
        gmsh.option.setNumber('Mesh.ElementOrder',2);gmsh.option.setNumber('Mesh.SecondOrderLinear',1);gmsh.option.setNumber('Mesh.Binary',0);gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
    def complete_boundary_check(filename,tol):
        gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
        try:
            gmsh.open(filename);tags,coordinates,_=gmsh.model.mesh.getNodes();ids=np.asarray(tags);coords=np.asarray(coordinates).reshape(-1,3);types,_,nodes=gmsh.model.mesh.getElements(3)
            if list(types)!=[11]:raise ValueError('The requested quadratic tetrahedra were not generated')
            used=np.unique(np.concatenate(nodes));order=np.argsort(ids);indices=np.searchsorted(ids[order],used);assert np.array_equal(ids[order][indices],used);audit_periodicity(coords[order][indices],tol)
        finally:gmsh.finalize()
    module._initialize_mesh=initialize_quadratic;module._check_output_mesh_periodicity=complete_boundary_check
    mesh=a.output/'cell.msh';microgen.mesh_periodic(mesh_file=str(step),rve=microgen.Rve(dim=1.),list_phases=[microgen.Phase(shape=shape)],size=a.size,order=2,output_file=str(mesh),msh_file_version=2.2,tol=1e-8)
    m=meshio.read(mesh);cells=np.concatenate([x.data for x in m.cells if x.type=='tetra10']);used=np.unique(cells);renumber=np.full(len(m.points),-1,dtype=int);renumber[used]=np.arange(len(used));points=m.points[used];cells=renumber[cells];geometry=audit_t10(points,cells);periodic=audit_periodicity(points)
    if abs(geometry['volume_mm3']-shape.Volume())/shape.Volume()>.01:raise ValueError('Mesh-to-CAD volume difference exceeds the fixed 1% gate')
    np.savez_compressed(a.output/'transport.npz',points=points,cells=cells)
    report=dict(status='explicit_periodic_T10_research_mesh_audited',kind=a.kind,resolution=a.resolution,mesh_size=a.size,gyroid_threshold=threshold if a.kind=='gyroid'else None,normalized_cell_edge_mm=1.,CAD_volume_mm3=shape.Volume(),CAD_solids=len(shape.Solids()),CAD_valid=shape.isValid(),nodes=len(points),tetrahedra=len(cells),geometry=geometry,periodicity=periodic,periodic_tolerance=1e-8,elapsed_seconds=time.monotonic()-start,carrier_geometry_changed=False,cellular_carrier_generated=False,mechanical_calculation_completed=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),upstream_mesh_module_sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),runtime_versions={x:version(x)for x in ['microgen','cadquery','cadquery-ocp','gmsh','meshio','numpy','scipy','pyvista','vtk']})
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
