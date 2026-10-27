"""One default Gmsh connectivity/position optimization, with an unchanged saved boundary."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes, sha


if __name__ == '__main__':
    import gmsh
    import numpy as np
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();p=args.parent;o=args.output
    parent=json.loads((p/'mesh-report.json').read_text())
    if sha(p/'coolant.msh')!=parent['mesh_sha256']:raise ValueError('Parent changed')
    if o.exists():raise ValueError('Output must be new')
    o.mkdir(parents=True)
    report=dict(parent,status='saved_default_optimizer_incomplete',source_sha256=sha(Path(__file__)),
                parent_receipt_sha256=sha(p/'mesh-report.json'),volume_quality_passed=False)
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.option.setNumber('General.NumThreads',2)
        gmsh.open(str(p/'coolant.msh'))
        print('DEFAULT_OPTIMIZE',flush=True)
        gmsh.model.mesh.optimize('',force=True,niter=5)
        gmsh.model.mesh.rebuildElementCache(False)
        typ,tags,_=gmsh.model.mesh.getElements(3)
        if list(typ)!=[4]:raise ValueError('Expected tetrahedra')
        q=gmsh.model.mesh.getElementQualities(tags[0],'minSICN')
        v=gmsh.model.mesh.getElementQualities(tags[0],'volume')*1e9
        report.update(cells=len(q),minimum_sicn=float(min(q)),below_sicn_01=int(np.count_nonzero(q<.1)),
                      minimum_volume_mm3=float(min(v)),volume_mm3=float(sum(v)),
                      volume_quality_passed=quality_passes(q,v))
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2);gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.write(str(o/'coolant.msh'))
        report.update(status='saved_default_volume_screen_only',mesh_sha256=sha(o/'coolant.msh'))
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        gmsh.finalize();(o/'mesh-report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2),flush=True)
