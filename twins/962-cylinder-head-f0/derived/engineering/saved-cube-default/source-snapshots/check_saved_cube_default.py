"""One saved-cube default optimizer fixture; no mesh generation or head input."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys

WRAPPER = Path(__file__).resolve()
ROOT = WRAPPER.parents[3]
BASE = WRAPPER.with_name("check_hxt_size_cap_002.py")
BASE_SHA = "0cac0c2662bab1efb47df427fa9d34b13a08f74655a43673fcd9fbdc4aaa504d"
INPUT = ROOT / "work/962-engineering/hxt-size-cap-fixture-001/capped-1p75/cube.msh"
INPUT_SHA = "e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1"
OUTPUT = ROOT / "work/962-engineering/saved-cube-default-fixture-001"
CASE = "default-force"
OPTIMIZE = dict(method="", force=True)
OPTIONS = {"General.NumThreads":2, "Mesh.MaxNumThreads3D":2, "Mesh.Renumber":0,
    "Mesh.Optimize":0, "Mesh.OptimizeNetgen":0, "Mesh.OptimizeThreshold":0.3, "Mesh.Binary":1,
    "Mesh.SaveAll":1, "Mesh.MshFileVersion":4.1}


def configure():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError("Frozen bounded cube-fixture launcher required")
    spec=importlib.util.spec_from_file_location("_962_saved_cube_launcher",BASE)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    original_sources=tuple(base.source_files())
    base.__file__=str(WRAPPER)  # The frozen launcher self-spawns through this entrypoint.
    base.source_files=lambda:[WRAPPER,*original_sources]
    base.options=lambda case:dict(OPTIONS)
    return base


def specification(base):
    return dict(schema="962-saved-cube-default-optimizer-fixture/v1",length_unit="mm",
        native_execution_authorized_by_contract=False,input_sha256=INPUT_SHA,
        case=CASE,optimization=OPTIMIZE,API_niter_limits_backend=False,options=OPTIONS,
        input_geometry=dict(boundary_nodes=8,interior_nodes=34,tetrahedra=191,
            outward_triangles=12,analytic_volume_mm3=343),
        required_invariants=dict(boundary_classification_below_dim3=True,interior_classification_dim3=True,
            no_curve_or_surface_periodic_mapping=True,exact_boundary_coordinates_and_oriented_faces=True,
            volume_connectivity_change_allowed=True,positive_finite_jacobians_and_volumes=True,
            exact_opposite_internal_faces=True,saved_readback_identity=True,relative_volume_bound=1e-6),
        quality_scope=dict(actual_SICN_threshold=.1,assess_threshold_separately=True,
            require_strict_improvement_and_actual_change_for_quality_success=True,head_accepted=False,
            head_not_read_or_accepted=True),
        resources=dict(native_deadline_s=30,sampled_RSS_stop_bytes=1024**3,
            sampled_output_stop_bytes=16*1024**2,threads=2,automatic_retry=False,
            hard_address_space_limit_applied=False,hard_OS_CPU_quota_applied=False),
        runtime=dict(python="3.10.11",numpy="2.0.2",gmsh="4.15.2",machine="arm64"),
        runtime_file_sha256s=base.RUNTIME_FILES,
        primary_source=dict(url="https://gmsh.info/src/gmsh-4.15.2-source.tgz",
            archive_sha256="be3f66f225d27ba9fa014f07e83169285da8a051b0e8ab7103d88066b39bdd3e",
            dispatch="src/mesh/Generator.cpp:896-903",discrete_force_guard="src/mesh/meshGRegion.cpp:278-291",
            backend_loop_and_gamma_threshold="src/mesh/meshGRegionDelaunayInsertion.cpp:883-1035",
            closed_edge_cavity="src/mesh/meshGRegionLocalMeshMod.cpp:61-105,237-345",
            interior_only_smoothing="src/mesh/meshGRegionLocalMeshMod.cpp:624-630",
            periodic_queries="src/common/gmsh.cpp:5454-5504",renumber_and_periodic_fix="src/geo/GModel.cpp:1531-1540",
            release_source_matches_installed_binary_build_attested=False))


def require_contract(base,path,digest):
    if not isinstance(digest,str) or len(digest)!=64 or base.mesh.sha(path)!=digest:
        raise ValueError("Exact reviewed saved-cube contract required")
    contract=json.loads(path.read_text())
    for key,value in specification(base).items():
        if json.dumps(contract.get(key),sort_keys=True)!=json.dumps(value,sort_keys=True):
            raise ValueError("Frozen saved-cube specification changed: "+key)
    if contract.get("source_sha256s")!={str(p.relative_to(ROOT)):base.mesh.sha(p) for p in base.source_files()}:
        raise ValueError("Saved-cube source bindings changed")
    if contract.get("test_sha256")!=base.mesh.sha(ROOT/"tests/test_962_saved_cube_default.py"):
        raise ValueError("Saved-cube test binding changed")
    if base.mesh.sha(INPUT)!=INPUT_SHA:raise ValueError("Original capped cube bytes changed")
    for name,h in base.RUNTIME_FILES.items():
        if base.mesh.sha(Path(name))!=h:raise ValueError("Observed native runtime changed")
    return contract


def classification(gmsh,np,node_tags):
    dimensions={};periodic_checked=[]
    for dim,tag in gmsh.model.getEntities():
        if dim in (1,2):
            masters=gmsh.model.mesh.getPeriodic(dim,[tag])
            master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
            if list(masters)!=[tag] or master!=tag or len(nodes) or len(node_masters) or len(transform):
                raise ValueError("Curve/surface periodic mapping is forbidden in the optimizer fixture")
            periodic_checked.append([dim,tag])
        for node in gmsh.model.mesh.getNodes(dim,tag,False,False)[0]:
            if int(node) in dimensions:raise ValueError("Node has ambiguous entity classification")
            dimensions[int(node)]=dim
    if (set(dimensions)!=set(map(int,node_tags)) or len(node_tags)!=42
            or any(dimensions.get(n,3)>=3 for n in range(1,9))
            or sum(dim==3 for dim in dimensions.values())!=34
            or any(dimensions[int(n)]!=3 for n in node_tags if n>8)):
        raise ValueError("Eight fixed boundary nodes and 34 volume-classified interior nodes required")
    return dict(boundary_nodes=8,interior_nodes=34,no_curve_or_surface_periodic_mapping=True,
                periodic_query_dimensions=[1,2],periodic_entities_checked=periodic_checked,
                node_counts_by_classification_dimension={str(d):sum(v==d for v in dimensions.values()) for d in range(4)},
                classified_tags_and_dimensions=[[n,dimensions[n]] for n in sorted(dimensions)])


def quality_assessment(before,after,moved,topology_changed):
    changed=moved>0 or topology_changed
    return dict(minimum_SICN_before=before,minimum_SICN_after=after,minimum_SICN_change=after-before,
        actual_SICN_threshold=.1,actual_SICN_gate_passed=math.isfinite(after) and after>=.1,
        minimum_SICN_strictly_improved=after>before,changed_interior_nodes=moved,
        actual_volume_topology_changed=topology_changed,optimization_had_effect=changed,
        optimizer_quality_success=math.isfinite(after) and after>=.1 and after>before and changed,
        unchanged_or_worse=after<=before,head_accepted=False)


def canonical_cells(np,nodes):
    ordered=np.sort(nodes,axis=1)
    return ordered[np.lexsort(ordered.T[::-1])]


def audit(base,gmsh):
    mesh,np=base.mesh,base.np;points,faces=base.cube()
    q,cells,tags,et,en=base.quality.tagged_volume(gmsh)
    report=dict(surface=mesh.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False),
        classifications=classification(gmsh,np,tags),tetrahedra=len(cells),total_nodes=len(tags),
        quality={name:mesh.distribution(gmsh.model.mesh.getElementQualities(et,measure)) for name,measure in
                 [("SICN","minSICN"),("jacobian","minDetJac"),("volume_mm3","volume")]},
        actual_tetra_boundary=mesh.tetra_boundary(cells,np.searchsorted(tags,faces+1)),
        internal_faces=base.quality.internal_face_orientation(cells))
    signed=mesh.tetra_volumes(q,cells);report["independent_volume_mm3"]=mesh.distribution(signed)
    report["summed_volume_mm3"]=math.fsum(signed);report["volume_relative_error"]=abs(report["summed_volume_mm3"]/343-1)
    if (any(report["quality"][key]["nonpositive_count"] for key in ["jacobian","volume_mm3"])
            or report["independent_volume_mm3"]["nonpositive_count"] or report["volume_relative_error"]>1e-6):
        raise ValueError("Positive finite tetrahedral geometry and 343 mm3 bookkeeping required")
    return (q,tags,et,en),report


def worker(base,args,contract):
    output=args.output/CASE;launch=json.loads((output/"receipt.json").read_text())
    if (launch.get("command")!=[sys.executable,*sys.argv] or launch.get("status")!="running"
            or launch.get("options")!=OPTIONS or launch.get("contract_sha256")!=args.contract_sha256
            or {p.name for p in output.iterdir()}!={"receipt.json","native.log"}
            or not base.bound_sources(args.output,contract)):
        raise ValueError("Fresh source-bound saved-cube worker required")
    import os
    with (output/"worker-claimed.json").open("x") as f:json.dump(dict(pid=os.getpid()),f)
    report=dict(status="running",software_mesh_passed=False,head_accepted=False,optimization=OPTIMIZE,
        API_niter_limits_backend=False,mesh_generation_called=False,head_input_read=False)
    initialized=False
    try:
        import gmsh
        observed=dict(python=platform.python_version(),numpy=base.np.__version__,gmsh=gmsh.__version__,machine=platform.machine())
        if observed!=contract["runtime"]:raise ValueError("Loaded native runtime version changed")
        hashes=[base.mesh.sha(Path(sys.executable).resolve()),base.mesh.sha(Path(gmsh.__file__)),base.mesh.sha(Path(gmsh.lib._name))]
        if hashes!=list(base.RUNTIME_FILES.values()):raise ValueError("Actual loaded runtime hashes changed")
        report.update(runtime=observed,actual_runtime_sha256s=dict(zip(["python","gmsh_module","gmsh_library"],hashes)))
        gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
        gmsh.option.setNumber("General.Terminal",1);gmsh.logger.start()
        for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
        gmsh.open(str(INPUT));before,report["before"]=audit(base,gmsh)
        if report["before"]["tetrahedra"]!=191:raise ValueError("Exact capped cube191 tetrahedra required")
        if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError("Required optimizer options changed")
        gmsh.model.mesh.optimize(**OPTIMIZE)
        path=output/"cube.msh";gmsh.write(str(path));report.update(mesh_sha256=base.mesh.sha(path),mesh_bytes=path.stat().st_size)
        after,report["after"]=audit(base,gmsh)
        if not base.np.array_equal(before[1],after[1]):raise ValueError("Original node tags changed")
        if report["before"]["classifications"]!=report["after"]["classifications"]:
            raise ValueError("Node classification or periodic identity changed")
        moved=int(base.np.count_nonzero(base.np.any(before[0][before[1]>8]!=after[0][after[1]>8],axis=1)))
        old_cells=canonical_cells(base.np,before[3]);new_cells=canonical_cells(base.np,after[3])
        topology_changed=not base.np.array_equal(old_cells,new_cells)
        report["volume_connectivity"]=dict(
            before_tetrahedra=len(old_cells),after_tetrahedra=len(new_cells),
            before_canonical_cell_sha256=base.mesh.array_sha(old_cells),after_canonical_cell_sha256=base.mesh.array_sha(new_cells),
            actual_topology_changed=topology_changed,
            tagged_connectivity_changed=not(base.np.array_equal(before[2],after[2]) and base.np.array_equal(before[3],after[3])))
        report["assessment"]=quality_assessment(report["before"]["quality"]["SICN"]["minimum"],report["after"]["quality"]["SICN"]["minimum"],moved,topology_changed)
        gmsh.clear();gmsh.open(str(path));saved,report["readback"]=audit(base,gmsh)
        if not all(base.np.array_equal(a,b) for a,b in zip(after,saved)) or base.mesh.sha(path)!=report["mesh_sha256"]:
            raise ValueError("Saved optimized cube identity changed")
        report.update(saved_mesh_identity_exact=True,volume_connectivity_change_audited=True,
                      software_mesh_passed=True,status="completed_identity_checks_only")
    except Exception as exc:report.update(status="failed_outputs_preserved",error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:
            report["gmsh_warnings_errors"]=[s for s in gmsh.logger.get() if s.startswith(("Warning","Error"))]
            gmsh.logger.stop();gmsh.finalize()
        try:
            require_contract(base,args.contract,args.contract_sha256)
            report["bound_inputs_unchanged"]=base.bound_sources(args.output,contract)
        except Exception:report["bound_inputs_unchanged"]=False
        if not report["bound_inputs_unchanged"]:report.update(software_mesh_passed=False,status="failed_bound_input_drift")
        base.mesh.save(output/"worker-report.json",report)
    return 0 if report["software_mesh_passed"] else 2


def main(argv=None):
    base=configure();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract",type=Path,required=True);parser.add_argument("--contract-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    parser.add_argument("--case",choices=[CASE],help=argparse.SUPPRESS);args=parser.parse_args(argv)
    contract=require_contract(base,args.contract,args.contract_sha256)
    if args.output.resolve()!=OUTPUT.resolve() or base.mesh.sha(Path(sys.executable).resolve())!=next(iter(base.RUNTIME_FILES.values())):
        raise ValueError("Fresh fixed output and selected native interpreter required")
    if args.worker:
        if args.case!=CASE:raise ValueError("Declared saved-cube worker case required")
        return worker(base,args,contract)
    if args.case is not None:raise ValueError("Only the single fixed controller case is allowed")
    base.mesh.new_output(args.output);snapshots=args.output/"source-snapshots";snapshots.mkdir()
    for name in contract["source_sha256s"]:(snapshots/Path(name).name).write_bytes((ROOT/name).read_bytes())
    (args.output/"contract.json").write_bytes(args.contract.read_bytes())
    report=dict(status="running",software_mesh_passed=False,head_accepted=False,contract_sha256=args.contract_sha256)
    base.mesh.save(args.output/"receipt.json",report);case=base.launch_case(args,CASE)
    require_contract(base,args.contract,args.contract_sha256)
    passed=(case["software_mesh_passed"] and base.bound_sources(args.output,contract)
            and base.quality.matching_mesh(args.output/CASE/"cube.msh",case.get("worker_report",{}).get("mesh_sha256"))
            and base.mesh.sha(args.output/"contract.json")==args.contract_sha256)
    report.update(status="completed_identity_fixture_only" if passed else "rejected_or_incomplete_outputs_preserved",
        software_mesh_passed=passed,case=case,assessment=case.get("worker_report",{}).get("assessment"))
    base.mesh.save(args.output/"receipt.json",report)
    print(json.dumps(dict(status=report["status"],identity_passed=passed,assessment=report["assessment"],head_accepted=False)))
    return 0 if passed else 2


if __name__=="__main__":raise SystemExit(main())
