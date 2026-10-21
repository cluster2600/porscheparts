"""Diagnostic only: import the three saved solids and inspect Gmsh fragment maps.

The volume-balance and lineage checks do not prove geometric containment or
admit a mechanical mesh. All imported sources and maps are recorded first.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--solids',type=Path,nargs=3,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',diagnostic_only=True,mechanical_mesh_admitted=False,source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [*a.solids,Path(__file__)]})
    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads',1);gmsh.option.setNumber('General.Terminal',1)
        names=['OCCFixDegenerated','OCCFixSmallEdges','OCCFixSmallFaces','OCCSewFaces','OCCMakeSolids']
        options={f'Geometry.{n}':gmsh.option.getNumber(f'Geometry.{n}')for n in names};options['Geometry.OCCScaling']=gmsh.option.getNumber('Geometry.OCCScaling')
        if any(options[f'Geometry.{n}']!=0 for n in names)or options['Geometry.OCCScaling']!=1:raise ValueError('Unexpected import healing/scaling options')
        report.update(gmsh_version=gmsh.__version__,import_options=options,imported=[])
        volumes=[]
        for path in a.solids:
            shapes=gmsh.model.occ.importShapes(str(path.resolve()),highestDimOnly=True,format='brep');gmsh.model.occ.synchronize()
            if len(shapes)!=1 or shapes[0][0]!=3:raise ValueError('Each input must import as one volume')
            volumes.append(shapes[0]);report['imported'].append(dict(source=str(path),volume_tag=shapes[0][1],volume_mm3=gmsh.model.occ.getMass(*shapes[0]),bounds_mm=gmsh.model.getBoundingBox(*shapes[0])))
        (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        result,mapping=gmsh.model.occ.fragment([volumes[0]],volumes[1:],removeObject=False,removeTool=False);gmsh.model.occ.synchronize()
        report.update(fragment_outputs=result,source_to_fragment_map=mapping,output_volumes=[dict(dim=d,tag=t,volume_mm3=gmsh.model.occ.getMass(d,t))for d,t in result if d==3])
        report['source_volume_balances']=[]
        for original,children in zip(report['imported'],mapping):
            total=sum(gmsh.model.occ.getMass(d,t)for d,t in children if d==3);relative=total/original['volume_mm3']-1
            report['source_volume_balances'].append(dict(source=original['source'],fragment_volume_sum_mm3=total,relative_difference=relative,historical_volume_guard=1e-8,passed=abs(relative)<1e-8))
        report['status']='fragment_volume_balance_diagnostic_passed'if len(mapping)==3 and all(r['passed']for r in report['source_volume_balances'])else'fragment_volume_balance_diagnostic_refused'
        report['pending']=['strict complete geometry retention','protected interfaces','conformal volume mesh and quality','mechanics on the new mesh']
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        gmsh.finalize();report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'])))
    return int(report['status']!='fragment_volume_balance_diagnostic_passed')

if __name__=='__main__':raise SystemExit(main())
