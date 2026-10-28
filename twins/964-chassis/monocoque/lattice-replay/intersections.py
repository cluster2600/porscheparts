"""Reuse the repository's bounded CGAL checker on unmodified phase-replay STL."""
import argparse
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
from audit import HERE, ROOT, sha, surface

HELPER = ROOT/"twins/m64-cylinder-head/source/wholebody/audit_surface_intersections.py"
CPP = HELPER.with_name("surface_intersections_cgal.cpp")
spec = importlib.util.spec_from_file_location("replay_intersections",HELPER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def run(directory, executable, output):
    if output.exists():
        raise FileExistsError(output)
    started = time.monotonic()
    tetra = np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
    tetra_faces = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    clear = checker.intersection_pairs(tetra,tetra_faces,executable)
    crossing = np.array([[-1.,-1,0],[1.,-1,0],[0,1.,0],[0,0,-1.],[0,0,1.],[0,2.,0]])
    cross = checker.intersection_pairs(crossing,np.array([[0,1,2],[3,4,5]]),executable)
    if not clear["complete"] or clear["pairs_private"] or not cross["complete"] or len(cross["pairs_private"])!=1:
        raise ValueError("CGAL calibration fixtures failed")
    results = {}
    for label in ("phase-050","phase-025"):
        path = directory/label/"raw.stl"
        triangles,digest = surface.load_binary_stl(path)
        vertices,inverse = np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
        result = checker.intersection_pairs(vertices,inverse.reshape(-1,3),executable)
        if sha(path)!=digest:
            raise ValueError("STL changed during inspection")
        results[label] = {"raw_stl_sha256":digest,"CGAL":result,
            "screen_passed":result["complete"] and not result["pairs_private"],"mesh_modified":False}
        print(label,"intersecting pairs:",len(result["pairs_private"]),"complete:",result["complete"],flush=True)
    report = {"schema":"964-lattice-phase-CGAL-screen/v1","calibration_passed":True,
        "calibration":{"tetrahedron":clear,"crossing_triangles":cross},"cases":results,
        "binary_sha256":sha(executable),"seconds":time.monotonic()-started,
        "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),HELPER,CPP)},
        "predicates":"CGAL EPICK on the exact stored STL coordinates, not the intended smooth solid",
        "structural_analysis_executed":False,"manufacturing_authorized":False}
    with output.open("x") as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write("\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path);parser.add_argument("executable",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args();run(args.directory,args.executable.resolve(),args.output)
