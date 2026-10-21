"""Compare analytic inverse-Frobenius SICN with native Gmsh regular/sliver fixtures."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from mesh_head import new_output,save,sha


def analytic(matrix):
    return len(matrix[0])/(np.linalg.norm(matrix,"fro")*np.linalg.norm(np.linalg.pinv(matrix),"fro"))


def run(output):
    import gmsh
    if gmsh.__version__!="4.15.2":raise ValueError("Observed Gmsh4.15.2 required")
    new_output(output);(output/"source-executed.py").write_bytes(Path(__file__).read_bytes())
    reference=np.array([[0.,0,0],[1,0,0],[.5,math.sqrt(3)/2,0],
        [.5,math.sqrt(3)/6,math.sqrt(2/3)]])
    cases=[("regular",np.eye(3)),("sliver_apex",np.diag([1.,1.,1e-3])),
        ("optimal_apex_for_slender_face",np.diag([1.,1e-4,.01])),
        ("skew_apex_for_slender_face",np.array([[1.,0,1.],[0,1e-4,1.],[0,0,.01]]))]
    rows=[]
    gmsh.initialize([],readConfigFiles=False,run=False)
    try:
        gmsh.option.setNumber("General.Terminal",0);gmsh.option.setNumber("General.NumThreads",2)
        for name,matrix in cases:
            gmsh.clear();gmsh.model.add(name);points=reference@matrix.T
            gmsh.model.addDiscreteEntity(3,1);gmsh.model.mesh.addNodes(3,1,[1,2,3,4],points.ravel())
            gmsh.model.mesh.addElementsByType(1,4,[1],[1,2,3,4])
            gmsh.model.addDiscreteEntity(2,2);gmsh.model.mesh.addNodes(2,2,[5,6,7],points[:3].ravel())
            gmsh.model.mesh.addElementsByType(2,2,[2],[5,6,7])
            q3=float(gmsh.model.mesh.getElementQualities([1],"minSICN")[0])
            q2=float(gmsh.model.mesh.getElementQualities([2],"minSICN")[0])
            a3,a2=float(analytic(matrix)),float(analytic(matrix[:,:2]))
            tight=3*q2/(2+q2);loose=1.5*q2
            if not math.isclose(q3,a3,rel_tol=1e-11,abs_tol=1e-14) or not math.isclose(q2,a2,rel_tol=1e-11,abs_tol=1e-14):
                raise ValueError("Native minSICN does not match the declared normalized inverse-Frobenius metric")
            if q3>tight+1e-13 or tight>loose+1e-13:raise ValueError("Necessary fixed-face bound failed")
            if name=="optimal_apex_for_slender_face" and not math.isclose(q3,tight,rel_tol=1e-11):
                raise ValueError("Known optimal-apex ceiling equality failed")
            rows.append(dict(name=name,transformation=matrix.tolist(),nodes_mm=points.tolist(),
                native_triangle_minSICN=q2,native_tetra_minSICN=q3,
                analytic_triangle_SICN=a2,analytic_tetra_SICN=a3,
                tight_tetra_ceiling=tight,loose_tetra_ceiling=loose))
    finally:gmsh.finalize()
    report=dict(status="native_regular_sliver_and_optimal_ceiling_fixtures_passed",
        metric="Signed normalized inverse Frobenius condition number of ideal-reference Jacobian; positive orientation in these fixtures.",
        dimension_formula="q_d = d / (||J||_F * ||J_inverse||_F); q_2 uses full-column-rank face restriction and its pseudoinverse.",
        tetra_upper_bound="q3 <= 3*q2/(2+q2) <= 1.5*q2",rows=rows,
        gmsh_version=gmsh.__version__,gmsh_module_sha256=sha(Path(gmsh.__file__)),
        libgmsh_sha256=sha(Path(gmsh.lib._name)),source_sha256=sha(Path(__file__)),
        no_head_surface_or_volume_changed=True,no_head_tetrahedra_generated=True,
        engineering_accepted=False,manufacturing_authorized=False)
    save(output/"receipt.json",report);print(json.dumps(report))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();run(args.output)
