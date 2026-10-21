"""Build explicit tensor-product root patches; never invoke the fillet builder."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    helpers = load('_patch_helpers', Path(__file__).with_name('point_radius_trial.py'))
    require, write, sha = helpers.require, helpers.write, helpers.sha
    require(not out.exists(), 'Fresh output required')
    out.mkdir(parents=True)
    began = time.monotonic()
    report = dict(status='incomplete', candidate_adopted=False,
                  declaration='Explicit NURBS quarter-section along each actual arch/rib edge; nominal R1 quartic in native edge parameter',
                  radius_nominal_mm=1., overlap_inside_parent_mm=.06,
                  FilletBuilder_called=False, patches=[], booleans=[])
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150 second inner limit')))
    signal.alarm(150)
    resource.setrlimit(resource.RLIMIT_CPU, (140, 141))
    try:
        old = root / 'work/carrier-process-20261017/bounded-webs-first-window-corner-slide-law-API-observer-preparation-001'
        p = json.loads((old / 'plan.json').read_text())
        master = root / p['master_BREP']
        require(sha(master) == helpers.MASTER, 'Current24af identity differs')
        sys.path.insert(0, str(root / p['native_site']))
        from build123d import import_brep, export_brep, Solid, Face, Wire
        from OCP.BRepAdaptor import BRepAdaptor_Curve
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
        from OCP.Geom import Geom_BSplineCurve, Geom_BSplineSurface
        from OCP.TColgp import TColgp_Array1OfPnt, TColgp_Array2OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger, TColStd_Array2OfReal
        from OCP.gp import gp_Pnt
        from OCP.TopoDS import TopoDS
        from OCP.BRepLib import BRepLib
        from OCP.OSD import OSD_ThreadPool
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut, BRepAlgoAPI_Common
        from OCP.TopTools import TopTools_ListOfShape
        from OCP.TopExp import TopExp_Explorer
        from OCP import TopAbs
        OSD_ThreadPool.DefaultPool_s().Init(1)
        observer = load('_patch_reference_reader', old / 'observe.py')
        _, nearest = observer.closed_observation(p)
        prior = observer.closed_add_observer(p)
        body = import_brep(master)
        faces, edges, graph = observer.SELECT.topology(body)
        selection = {}
        normals = load('_patch_source_normals', root / p['boundary_normal_source'])
        try:
            paths = observer.SELECT.select(body, faces, edges, graph, normals, selection, nearest, prior)
        finally:
            write(out / 'fresh-selection.json', selection)

        def scalars(values, integer=False):
            array = (TColStd_Array1OfInteger if integer else TColStd_Array1OfReal)(1, len(values))
            for i, value in enumerate(values, 1):
                array.SetValue(i, value)
            return array

        def curve_record(curve):
            return dict(degree=curve.Degree(), poles_xyz_mm=[list(curve.Pole(i).Coord()) for i in range(1, curve.NbPoles()+1)],
                        knots=[curve.Knot(i) for i in range(1,curve.NbKnots()+1)],
                        multiplicities=[curve.Multiplicity(i) for i in range(1,curve.NbKnots()+1)],
                        rational=curve.IsRational(), periodic=curve.IsPeriodic())

        patches = []
        for side, path in enumerate(paths):
            edge = edges[path[1]]
            adaptor = BRepAdaptor_Curve(edge.wrapped)
            curve = adaptor.BSpline().Copy()
            first, last = adaptor.FirstParameter(), adaptor.LastParameter()
            curve.Segment(first, last)
            require(not curve.IsRational() and not curve.IsPeriodic(), 'Nonrational source curve required')
            row = dict(side=side, source_edge=path[1], original_curve=curve_record(curve), domain=[first,last])
            report['patches'].append(row)
            radius_poles=TColgp_Array1OfPnt(1,5)
            for i,r in enumerate([0.,0.,8./3.,0.,0.],1):
                radius_poles.SetValue(i,gp_Pnt(0.,r,0.))
            radius=Geom_BSplineCurve(radius_poles,scalars([first,last]),scalars([5,5],True),4,False)
            degree=max(curve.Degree(),radius.Degree())
            curve.IncreaseDegree(degree);radius.IncreaseDegree(degree)
            targets={c.Knot(i):c.Multiplicity(i) for c in [curve,radius] for i in range(1,c.NbKnots()+1)}
            for knot,multiplicity in sorted(targets.items()):
                curve.InsertKnot(knot,multiplicity,0.,False)
                radius.InsertKnot(knot,multiplicity,0.,False)
            row.update(aligned_curve=curve_record(curve),radius_curve=curve_record(radius))
            write(out/'construction.json',report)
            require(curve.NbPoles()==radius.NbPoles() and curve.NbKnots()==radius.NbKnots(),'Aligned basis dimensions differ')
            require(all(curve.Knot(i)==radius.Knot(i) and curve.Multiplicity(i)==radius.Multiplicity(i) for i in range(1,curve.NbKnots()+1)),'Aligned basis differs')
            n=curve.NbPoles();base=[list(curve.Pole(i).Coord()) for i in range(1,n+1)]
            radii=[radius.Pole(i).Y() for i in range(1,n+1)]
            columns={name:[] for name in ['A','P','B','C','D']}
            for (x,y,z),r in zip(base,radii):
                for name,point in dict(A=[x,y,z+r],P=[x,y,z],B=[x,y-r,z],C=[x,y+.06,z-.06],D=[x,y+.06,z+r]).items():
                    columns[name].append(point)
            uk=scalars([curve.Knot(i) for i in range(1,curve.NbKnots()+1)])
            um=scalars([curve.Multiplicity(i) for i in range(1,curve.NbKnots()+1)],True)
            sewing=BRepBuilderAPI_Sewing(1e-7,True,True,True,False)
            row['surfaces']=[]
            for name,names,weights in [('arc',['A','P','B'],[1.,math.sqrt(.5),1.]),('bottom',['B','C'],[1.,1.]),('inside',['C','D'],[1.,1.]),('top',['D','A'],[1.,1.])]:
                vdegree=len(names)-1
                poles=TColgp_Array2OfPnt(1,n,1,len(names));w=TColStd_Array2OfReal(1,n,1,len(names))
                for i in range(n):
                    for j,key in enumerate(names):
                        poles.SetValue(i+1,j+1,gp_Pnt(*columns[key][i]));w.SetValue(i+1,j+1,weights[j])
                surface=Geom_BSplineSurface(poles,w,uk,scalars([0.,1.]),um,scalars([vdegree+1,vdegree+1],True),degree,vdegree,False,False)
                maker=BRepBuilderAPI_MakeFace(surface,1e-7)
                require(maker.IsDone(),'Patch face creation refused: '+name)
                face=maker.Face();sewing.Add(face)
                export_brep(Face(face),out/f'patch-{side}-{name}.brep')
                row['surfaces'].append(dict(name=name,column_order=names,weights=weights,control_columns={key:columns[key] for key in names}))
            for endpoint in [first,last]:
                point=curve.Value(endpoint);x,y,z=point.Coord()
                cap=Face(Wire.make_polygon([(x,y,z),(x,y+.06,z-.06),(x,y+.06,z)],close=True))
                sewing.Add(cap.wrapped)
            sewing.Perform();shell=sewing.SewedShape()
            row['sewn_shape_type']=str(shell.ShapeType());write(out/'construction.json',report)
            solid_maker=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shell))
            require(solid_maker.IsDone(),'Patch solid creation failed')
            solid=solid_maker.Solid();row['orientation_completed']=bool(BRepLib.OrientClosedSolid_s(solid))
            patch=Solid(solid);export_brep(patch,out/f'patch-{side}.brep')
            row.update(valid=patch.is_valid,solid_count=len(patch.solids()),volume_mm3=patch.volume)
            write(out/'construction.json',report)
            require(row['orientation_completed'] and patch.is_valid and len(patch.solids())==1 and patch.volume>0,'One valid positive patch solid required')
            patches.append(patch)

        def boolean(cls,a,b,name):
            op=cls();arguments=TopTools_ListOfShape();tools=TopTools_ListOfShape()
            arguments.Append(a);tools.Append(b)
            op.SetArguments(arguments);op.SetTools(tools);op.SetNonDestructive(True);op.SetRunParallel(False);op.SetFuzzyValue(0.)
            op.Build();require(op.IsDone(),'Native Boolean failed: '+name)
            shape=op.Shape();export_brep(__import__('build123d').Shape.cast(shape),out/(name+'.brep'))
            counts={}
            for key in ['VERTEX','EDGE','WIRE','FACE','SHELL','SOLID','COMPSOLID']:
                e=TopExp_Explorer(shape,getattr(TopAbs,'TopAbs_'+key));count=0
                while e.More():count+=1;e.Next()
                counts[key]=count
            row=dict(name=name,entity_counts=counts,topologically_empty=not any(counts.values()))
            report['booleans'].append(row);write(out/'construction.json',report)
            return shape,row

        candidate=body
        for side,patch in enumerate(patches):
            shape,_=boolean(BRepAlgoAPI_Fuse,candidate.wrapped,patch.wrapped,f'fuse-{side}')
            candidate=__import__('build123d').Shape.cast(shape)
        export_brep(candidate,out/'unqualified-candidate.brep')
        box=candidate.bounding_box();report['candidate']=dict(sha256=sha(out/'unqualified-candidate.brep'),valid=candidate.is_valid,solid_count=len(candidate.solids()),mass_kg=candidate.volume*4420e-9,bounds_mm=[list(box.min),list(box.max)])
        _,retention=boolean(BRepAlgoAPI_Cut,body.wrapped,candidate.wrapped,'baseline-minus-candidate')
        _,addition=boolean(BRepAlgoAPI_Cut,candidate.wrapped,body.wrapped,'candidate-minus-baseline')
        report['checks']=dict(strict_native_retention=retention['topologically_empty'],positive_addition=addition['entity_counts']['SOLID']>0,valid_single_solid=candidate.is_valid and len(candidate.solids())==1,mass_below_1_30_kg=0<report['candidate']['mass_kg']<=1.3)
        report['status']='candidate_saved_geometry_checks_pending' if all(report['checks'].values()) else 'candidate_saved_geometry_refused'
        report['pending']=['original four tool Commons','whole protected-interface rosters','seam continuity and endcap audit','fresh surface and T10 mesh','all20 mechanics and refinement']
    except Exception as error:
        report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);report['elapsed_seconds']=time.monotonic()-began
        write(out/'assessment.json',report)
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))))
    return 0 if report['status'].startswith('candidate_saved_') else 1


if __name__=='__main__':
    raise SystemExit(main())
