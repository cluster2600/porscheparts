"""Read-only recovery/audit of the newest complete checkpoint from the retained 8 GiB trial."""
import argparse
import json
from pathlib import Path
import signal
import time

import numpy as np

from mesh_head import ROOT,FAMILY,new_output,sha,save,distribution,surface_roundtrip
from prepare_head_analysis import validate_surface
from run_head_envelope import latest_complete_checkpoint,read_surface

TRIAL=ROOT/"work/962-engineering/analysis-envelope-025-002"


def run(output):
    import gmsh
    if gmsh.__version__!="4.15.2":
        raise ValueError("Observed native Gmsh4.15.2 required for independent fixed-face quality")
    original=json.loads((TRIAL/"receipt.json").read_text())
    if not original["source_import_exact"] or not original["bound_inputs_unchanged"]:
        raise ValueError("Exact source import and unchanged bound inputs required")
    pins={str(p.relative_to(ROOT)):sha(p) for p in [TRIAL/"receipt.json",
        FAMILY/"source/run_head_envelope.py",FAMILY/"source/prepare_head_analysis.py",
        FAMILY/"source/mesh_head.py",Path(__file__),
        ROOT/"twins/m64-cylinder-head/source/wholebody/audit_fixed_face_quality.py"]}
    binaries={str(p.relative_to(TRIAL)):sha(p) for p in (TRIAL/"native").glob("*.bin")}
    new_output(output);(output/"source-executed.py").write_bytes(Path(__file__).read_bytes())
    signal.alarm(300);start=time.monotonic();initialized=False
    report=dict(status="auditing_retained_checkpoint",input_hashes=pins,
        original_native_file_hashes=binaries,qualification=dict(analysis_surface_geometric_gate_passed=False,
            solver_admission_established=False,mesh_convergence_established=False,
            engineering_accepted=False,strength_validated=False,manufacturing_authorized=False))
    try:
        selected,rejected=latest_complete_checkpoint(TRIAL/"native")
        if selected is None:raise ValueError("No complete retained checkpoint")
        report.update(selected_native_candidate=str(selected.relative_to(TRIAL)),
            selected_native_sha256=sha(selected),rejected_incomplete_payloads=rejected)
        p,f=read_surface(selected)
        np.savez_compressed(output/"analysis-surface.npz",points_mm=p,triangles=f)
        report["surface"]=validate_surface(p,f)
        report["analysis_surface_npz_sha256"]=sha(output/"analysis-surface.npz")
        gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
        gmsh.option.setNumber("General.Terminal",0);gmsh.option.setNumber("General.NumThreads",2)
        gmsh.model.add("retained_checkpoint_quality_only");gmsh.model.addDiscreteEntity(2,1)
        gmsh.model.mesh.addNodes(2,1,np.arange(1,len(p)+1,dtype=np.uint64),p.ravel())
        tags=np.arange(1,len(f)+1,dtype=np.uint64)
        gmsh.model.mesh.addElementsByType(1,2,tags,(f+1).astype(np.uint64).ravel())
        report["independent_quality_import"]=surface_roundtrip(gmsh,p,f)
        q=np.asarray(gmsh.model.mesh.getElementQualities(tags,"minSICN"),dtype=float)
        ceiling=3*q/(2+q)
        report["fixed_face_quality"]=dict(triangle_SICN=distribution(q),
            tetra_SICN_ceiling=distribution(ceiling),required_tetra_SICN=.1,
            necessary_triangle_SICN=2*.1/(3-.1),
            incompatible_fixed_triangles=int(np.sum(ceiling<.1)),
            scope="Necessary condition for fixed linear triangles; no tetrahedra were generated.",
            floating_point_algebra_not_interval_certified=True)
        report["runtime"]=dict(gmsh=gmsh.__version__,numpy=np.__version__,
            gmsh_module_sha256=sha(Path(gmsh.__file__)),libgmsh_sha256=sha(Path(gmsh.lib._name)))
        report["status"]="complete_checkpoint_recovered_independent_admission_pending"
        if np.any(ceiling<.1):report["status"]="complete_checkpoint_recovered_fixed_face_quality_rejected"
    except Exception as exc:
        report.update(status="failed_outputs_preserved",error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:gmsh.finalize()
        report.update(wall_s=time.monotonic()-start,all_source_inputs_unchanged=all(
            sha(ROOT/p)==h for p,h in pins.items()),all_native_artifacts_unchanged=all(
            sha(TRIAL/p)==h for p,h in binaries.items()))
        save(output/"receipt.json",report);signal.alarm(0)
    print(json.dumps({k:report.get(k) for k in ["status","selected_native_candidate","fixed_face_quality","wall_s","error"]}))
    return 0 if report["status"].startswith("complete_checkpoint_recovered") else 2


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();raise SystemExit(run(args.output))
