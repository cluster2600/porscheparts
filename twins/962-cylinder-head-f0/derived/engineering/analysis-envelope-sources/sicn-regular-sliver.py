"""Native regular/sliver normalization witnesses, separate from the retained failed extreme fixture."""
import argparse
import json
import math
from pathlib import Path
import signal

import numpy as np

from mesh_head import new_output,save,sha


def run(output):
    import gmsh
    new_output(output);(output/"source-executed.py").write_bytes(Path(__file__).read_bytes())
    signal.alarm(30);rows=[]
    reference=np.array([[0.,0,0],[1,0,0],[.5,math.sqrt(3)/2,0],
        [.5,math.sqrt(3)/6,math.sqrt(2/3)]])
    gmsh.initialize([],readConfigFiles=False,run=False)
    try:
        gmsh.option.setNumber("General.Terminal",0);gmsh.option.setNumber("General.NumThreads",2)
        for name,height_scale in [("regular",1.),("sliver_apex",.001)]:
            gmsh.clear();gmsh.model.add(name);p=reference.copy();p[:,2]*=height_scale
            gmsh.model.addDiscreteEntity(3,1);gmsh.model.mesh.addNodes(3,1,[1,2,3,4],p.ravel())
            gmsh.model.mesh.addElementsByType(1,4,[1],[1,2,3,4])
            gmsh.model.addDiscreteEntity(2,2);gmsh.model.mesh.addNodes(2,2,[5,6,7],p[:3].ravel())
            gmsh.model.mesh.addElementsByType(2,2,[2],[5,6,7])
            q3=float(gmsh.model.mesh.getElementQualities([1],"minSICN")[0])
            q2=float(gmsh.model.mesh.getElementQualities([2],"minSICN")[0])
            expected=3/math.sqrt((2+height_scale**2)*(2+1/height_scale**2))
            if not math.isclose(q2,1.,rel_tol=1e-11,abs_tol=1e-14) or not math.isclose(q3,expected,rel_tol=1e-11,abs_tol=1e-14):
                raise ValueError("Native regular/sliver normalization witness failed")
            rows.append(dict(name=name,nodes_mm=p.tolist(),native_triangle_minSICN=q2,
                native_tetra_minSICN=q3,analytic_tetra_inverse_Frobenius_SICN=expected))
    finally:gmsh.finalize();signal.alarm(0)
    report=dict(status="two_native_regular_sliver_normalization_witnesses_passed",rows=rows,
        relative_fixture_comparison_tolerance=1e-11,absolute_fixture_comparison_tolerance=1e-14,
        original_failed_extreme_fixture_unchanged=True,head_SICN_gate_unchanged=.1,
        exact_fixed_face_proof_is_separately_rational=True,
        gmsh_version=gmsh.__version__,gmsh_module_sha256=sha(Path(gmsh.__file__)),
        libgmsh_sha256=sha(Path(gmsh.lib._name)),source_sha256=sha(Path(__file__)),
        no_head_tetrahedra_generated=True,engineering_accepted=False)
    save(output/"receipt.json",report);print(json.dumps(report))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();run(args.output)
