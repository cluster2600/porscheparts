"""One bounded default optimizer on the saved Delaunay head; no generation.

The frozen controller supplies admission, claims, source capture and kill/reap.
The cube is software evidence only. Native head execution needs separate authority.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import time

WRAPPER_PATH = Path(__file__).resolve()
ROOT = WRAPPER_PATH.parents[3]
CORE_PATH = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py"
CORE_SHA256 = "a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4"
PYTHON_SHA256 = "72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621"
DEADLINE = 1200
INPUT = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-001/head-volume.msh"
INPUT_READBACK = "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/readback-report.json"
ADMISSION = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json"
ADMISSION_SHA256 = "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962"
OUTPUT = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001"
OPTIONS = {"General.NumThreads":2, "Mesh.MaxNumThreads3D":2, "Mesh.Renumber":0,
    "Mesh.Optimize":0, "Mesh.OptimizeNetgen":0, "Mesh.OptimizeThreshold":.3,
    "Mesh.Binary":1, "Mesh.SaveAll":1, "Mesh.MshFileVersion":4.1}
INPUT_HASHES = {
    "twins/962-cylinder-head-f0/source/check_saved_cube_default.py": "c8a87cc7bc312fae4bdb414c2a6c6e77b920382f5bd00ca7ae2d04e4d3de20a6",
    "tests/test_962_saved_cube_default.py": "c1f41f709123bbfc93e02cae313ae837d52e35fc2146c4bf2c9e2d4d533a142e",
    "work/962-engineering/saved-cube-default-preflight-001/frozen-contract.json": "4d4bdba83f15ca26ab80a48d7967beca63978c928dcbe51003214c85261dae81",
    "work/962-engineering/hxt-size-cap-fixture-001/capped-1p75/cube.msh": "e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1",
    "work/962-engineering/saved-cube-default-fixture-001/default-force/cube.msh": "3676ea044e2e10ea91435271687cac7f2181704014dc4e0daf8ae5c9ede26613",
    "work/962-engineering/saved-cube-default-fixture-001/receipt.json": "6021074390614545957fb2ab72c0ed4c6ca89efe2925fbd8f4f9a51ecc970c05",
    "work/962-engineering/saved-cube-default-fixture-001/default-force/worker-report.json": "e5adecf95d6c47675781fc23cf3c38395e90c973800e5757dd6ed1a97d69ff9b",
    "work/962-engineering/saved-cube-default-readback-001/review.json": "7a1628d3475cff36c14c44e5af1dbd71cf5660b28ab314a73d0efddeb19def12",
    "work/962-engineering/saved-cube-default-readback-001/arrays.json": "2f5b93350c33d53c52f3a317a08b6d8af99d25ff67e5b58554ab8b608d00248d",
    "work/962-engineering/saved-cube-default-readback-001/reader.py": "c493da25ff2e675db533f9261a4040358b46ae98c822d04e4ec68e59d1f4116e",
    "work/962-engineering/saved-cube-default-readback-001/frozen-contract.json": "7485cd3d1a64b0f047439d26baf3efea6a02c652e3e72e1c5e236675321a841b",
    "work/962-engineering/saved-cube-default-readback-001/execution-receipt.json": "6f3754722cb644a2b62fe17b5dc9493770455e7f233af4914c7fd112b1a909e7",
    "work/962-engineering/saved-cube-default-root-review-001/review.json": "88b9426578d99b36089a34beb7447ae3efc9cdfbc662ccdce28d1e9bfd62ce5e",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py": "a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4",
    "work/962-engineering/atomic-cavity-volume-default-postexport-prep-002/mesh_atomic_postexport_002.py": "28746e14a041db464c3a41b732f1fc3e9ad9fd6ce96e886f728e5409d6ea0e36",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json": "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-001/receipt.json": "a880d1c331bbce2774cb6563246c9e194eaac498a2a39b999bdba66d5a76f2be",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-001/worker-report.json": "ddd89a9f1da6f17e7974205a8ced234c18d47a0e7c02db10d21fa3a3bb22199b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-result-peer-001/review.json": "c3a1a9f2cffca676be7577cc28ed3de09329d5893084f49bd617e0107afdaf1d",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-root-execution-001/execution.json": "32d9b4e0fd401f6fb95cfc934646f98a7b7e4f5b1bc761e8219efdc9b12dc49f",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/frozen-contract.json": "89670cc7777337e5cbb999c1005d8bb0fa77fedba30074d81b679f5fa588d58a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/execution-receipt.json": "cb0d6ae9583e9ccf431b5df1e72cf395a8107db5edc2df89d51462c67d77165a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/reader.py": "ec5a45297a8d6ad73fb2fac5b087589e42a9553bc3d434a9d1dc7fb53122db30",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/native.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/readback-report.json": "1888c07cbf09931790a400e86a72d5d0cdc2ac35df4d54031380e02f0e7614eb",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-001/run_readback.py": "4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-root-execution-001/execution.json": "fd14eb79e5259d46a8355bdc36d6ee75ffdbe903893699b2286d0b015dd4956f",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-readback-result-peer-001/review.json": "0124b1fdf9098947391b20c8cfb2ed033883117766e368cb1d59a9e7cf193929",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-001/head-volume.msh": "3dd7939f34c8246a813334b2f570b2408b590965734bdf3761866569290e3593",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin": "9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4"
}


def require_inputs():
    if not INPUT_HASHES:
        raise ValueError("Complete fixed head and cube evidence bindings required")
    for name, expected in INPUT_HASHES.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Bound head optimizer input or software evidence changed")


def configure_core():
    if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA256:
        raise ValueError("Exact reviewed frozen quality-volume controller required")
    require_inputs()
    spec=importlib.util.spec_from_file_location("_962_frozen_postexport_core",CORE_PATH)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    sources=tuple(core.source_files());original_save=core.save;original_admission=core.require_admission
    if len(sources)!=5 or sources[0]!=CORE_PATH:
        raise ValueError("Original controller and its four source imports required")
    def require_bound_admission(path,digest):
        require_inputs()
        if path.resolve()!=ADMISSION.resolve() or digest!=ADMISSION_SHA256:
            raise ValueError("The fixed original surface-admission receipt is required")
        return original_admission(path,digest)
    def save_postexport(path,report):
        report["postexport_companion"]=dict(frozen_core_sha256=CORE_SHA256,
            wrapper_source_sha256=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest(),
            input_sha256s=INPUT_HASHES,optimization=dict(method="",force=True),
            mesh_generation_called=False,API_niter_limits_backend=False,
            cache_refresh="rebuildElementCache(False): lookup repair, no geometry change",
            Gamma_threshold_is_not_SICN=True,actual_minimum_SICN_gate_unchanged=.1,
            cube_success_is_not_head_acceptance=True)
        original_save(path,report)
    core.__file__=str(WRAPPER_PATH)  # Both controller and worker re-enter this wrapper.
    core.source_files=lambda:[WRAPPER_PATH,*sources]
    core.OUTPUT=OUTPUT;core.OPTIONS=dict(OPTIONS);core.DEADLINE=DEADLINE
    core.require_admission=require_bound_admission;core.save=save_postexport
    core.worker=lambda args:worker(core,args)
    return core


def classifications(core,gmsh,node_tags,boundary_count):
    np=core.np;dimensions=np.full(len(node_tags),-1,dtype=np.int8)
    entity_tags=np.zeros(len(node_tags),dtype=np.int64);periodic=[]
    for dim,tag in gmsh.model.getEntities():
        if dim in (1,2):
            masters=gmsh.model.mesh.getPeriodic(dim,[tag])
            master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
            if list(masters)!=[tag] or master!=tag or len(nodes) or len(node_masters) or len(transform):
                raise ValueError("Curve/surface periodic mappings are forbidden")
            periodic.append([dim,tag])
        tags=np.asarray(gmsh.model.mesh.getNodes(dim,tag,False,False)[0])
        indices=np.searchsorted(node_tags,tags)
        if (len(np.unique(tags))!=len(tags) or np.any(indices>=len(node_tags))
                or not np.array_equal(node_tags[indices],tags) or np.any(dimensions[indices]!=-1)):
            raise ValueError("Unique complete node classification required")
        dimensions[indices]=dim;entity_tags[indices]=tag
    boundary=node_tags<=boundary_count
    if (np.any(dimensions<0) or np.count_nonzero(boundary)!=boundary_count
            or np.any(dimensions[boundary]>=3) or np.any(dimensions[~boundary]!=3)):
        raise ValueError("Fixed boundary nodes must classify below dim3 and interior nodes at dim3")
    return dict(node_classification_dimensions_sha256=core.array_sha(dimensions),
        node_classification_entity_tags_sha256=core.array_sha(entity_tags),
        node_counts_by_classification_dimension={str(d):int(np.count_nonzero(dimensions==d)) for d in range(4)},
        no_curve_or_surface_periodic_mapping=True,periodic_query_dimensions=[1,2],periodic_entities_checked=periodic)


def array_identity(core,state):
    return dict(zip(("sorted_coordinates_sha256","sorted_node_tags_sha256",
        "sorted_tetra_tags_sha256","tagged_tetra_connectivity_sha256"),map(core.array_sha,state)))


def load_before(core,gmsh,points,faces):
    q,_,nt,et,en=core.tagged_volume(gmsh);state=(q,nt,et,en)
    retained=json.loads((ROOT/INPUT_READBACK).read_text());audit=retained["audit"]
    if (retained.get("status")!="reading_saved_mesh"
            or retained.get("stage")!="reopening_saved_file_for_tagged_array_identity"
            or retained.get("direct_full_tetra_face_incidence_completed") is not True
            or retained.get("direct_internal_face_orientation_completed") is not True
            or retained.get("exact_source_boundary_coordinate_bits") is not True
            or retained.get("mesh_sha256")!=INPUT_HASHES[str(INPUT.relative_to(ROOT))]
            or retained.get("candidate_sha256")!=core.CANDIDATE_SHA
            or audit["tetrahedra"]!=len(et) or audit["total_mesh_nodes"]!=len(nt)):
        raise ValueError("Complete first-pass audit of this exact saved input required")
    actual=array_identity(core,state)
    if actual!=audit["array_sha256s"]:
        raise ValueError("Loaded tagged arrays differ from the single retained first-pass audit")
    classification=classifications(core,gmsh,nt,len(points))
    if classification!=audit["classifications"]:
        raise ValueError("Loaded input classifications differ from the retained first-pass audit")
    report=dict(loaded_array_sha256s=actual,
        current_surface=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False),
        classifications=classification,
        retained_proof_path=INPUT_READBACK,retained_proof_sha256=INPUT_HASHES[INPUT_READBACK],
        retained_proof_scope="one_completed_first_pass_before_interrupted_optional_reopen",
        prior_optional_reopen_completed=False,prior_reader_terminal_completion=False,
        input_array_identity_freshly_closed_before_optimizer=True,
        missing_worker_array_proof_not_claimed=True,
        retained_not_recomputed={key:audit[key] for key in ["quality","tetrahedra","total_mesh_nodes",
            "tetra_referenced_nodes","tetra_referenced_interior_nodes","unreferenced_mesh_nodes",
            "summed_tetra_volume_mm3","volume_relative_error","actual_tetra_boundary","internal_tetra_face_orientation"]},
        fresh_native_quality_queries=False,fresh_tetra_face_incidence_audit=False)
    return state,report


def optimize_and_refresh(gmsh,report,checkpoint):
    report.update(stage="calling_default_postexport_optimizer",optimizer_call_count=1)
    checkpoint()
    gmsh.model.mesh.optimize(method="",force=True)
    report.update(optimizer_returned=True,stage="refreshing_element_lookup_cache")
    checkpoint()
    # False forces rebuilding even if the pre-optimization cache is populated.
    # Gmsh4.15.2 GModel.cpp2046-2082: this changes lookup pointers, not the mesh.
    report["element_cache_refresh_count"]=1
    gmsh.model.mesh.rebuildElementCache(False)
    report.update(element_cache_refresh_completed=True,
                  stage="optimizer_returned_and_element_cache_refreshed")
    checkpoint()


def audit_after(core,gmsh,points,faces):
    np=core.np;q,cells,nt,et,en=core.tagged_volume(gmsh);state=(q,nt,et,en)
    referenced=np.unique(en)
    if (len(np.unique(nt))!=len(nt) or len(np.unique(et))!=len(et)
            or not np.array_equal(referenced,nt)):
        raise ValueError("Unique tagged nodes/cells and no orphan mesh nodes required")
    report=dict(surface=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False),
        classifications=classifications(core,gmsh,nt,len(points)),tetrahedra=len(cells),
        total_mesh_nodes=len(nt),retained_boundary_nodes=len(points),tetra_referenced_nodes=len(referenced),
        tetra_referenced_interior_nodes=int(np.count_nonzero(referenced>len(points))),unreferenced_mesh_nodes=0,
        quality={},interior_node_count_establishes_thermal_resolution=False)
    for name,measure in [("minimum_jacobian","minDetJac"),("native_volume_mm3","volume"),("minimum_SICN","minSICN")]:
        values=np.asarray(gmsh.model.mesh.getElementQualities(et,measure))
        if len(values)!=len(et):raise ValueError("Every actual tetrahedron quality must be returned")
        report["quality"][name]={**core.distribution(values),"array_sha256":core.array_sha(values)}
        if measure=="minSICN":report["quality"][name]["below_point1_count"]=int(np.count_nonzero(values<.1))
    signed=core.tetra_volumes(q,cells)
    report["quality"]["independent_signed_volume_mm3"]=core.distribution(signed)
    if any(type(q.get("count")) is not int or q["count"] != len(cells) for q in report["quality"].values()):
        raise ValueError("Every metric distribution must cover every actual tetrahedron")
    report["summed_tetra_volume_mm3"]=math.fsum(signed)
    report["volume_relative_error"]=abs(report["summed_tetra_volume_mm3"]/core.CANDIDATE_VOLUME-1)
    report["actual_tetra_boundary"]=core.tetra_boundary(cells,np.searchsorted(nt,faces+1))
    report["internal_tetra_face_orientation"]=core.internal_face_orientation(cells)
    report["array_sha256s"]=array_identity(core,state)
    return state,report


def canonical_cells(np,nodes):
    ordered=np.sort(nodes,axis=1)
    return ordered[np.lexsort(ordered.T[::-1])]


def worker(core,args):
    launch=core.claim_worker(args);initialized=False;started=time.monotonic()
    path=args.output/"head-volume.msh"
    report=dict(status="running",stage="checking_runtime",optimizer_call_count=0,
        optimizer_returned=False,element_cache_refresh_count=0,element_cache_refresh_completed=False,
        API_call_counters_record_attempts=True,options=OPTIONS,mesh_generation_called=False,
        candidate_sha256=core.CANDIDATE_SHA,candidate_volume_reference_mm3=core.CANDIDATE_VOLUME,
        volume_relative_bookkeeping_bound=1e-6,bookkeeping_bound_is_manufacturing_tolerance=False,
        qualification=dict(geometric_volume_gate_passed=False,
            mesh_convergence_established=False,thermal_resolution_established=False,engineering_accepted=False,
            thermal_performance_validated=False,strength_validated=False,manufacturing_authorized=False))
    checkpoint=lambda:core.save(args.output/"worker-report.json",report)
    try:
        import gmsh
        runtime=dict(python=sys.version,numpy=core.np.__version__,gmsh=gmsh.__version__,machine=platform.machine(),
            executable_sha256=core.sha(Path(sys.executable).resolve()),gmsh_module_sha256=core.sha(Path(gmsh.__file__)),
            libgmsh_sha256=core.sha(Path(gmsh.lib._name)))
        report["runtime"]=runtime
        if runtime != {'python': '3.10.11 (v3.10.11:7d4cc5aa85, Apr  4 2023, 19:05:19) [Clang 13.0.0 (clang-1300.0.29.30)]', 'numpy': '2.0.2', 'gmsh': '4.15.2', 'machine': 'arm64', 'executable_sha256': '72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621', 'gmsh_module_sha256': 'f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3', 'libgmsh_sha256': 'def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a'}:
            raise ValueError("Exact observed native Python/NumPy/Gmsh runtime required")
        points,faces=core.audit_quality_head.read(core.CANDIDATE)
        points,faces=core.np.asarray(points,dtype=core.np.float64),core.np.asarray(faces,dtype=core.np.int64)
        if (len(points),len(faces))!=(871731,1743878):raise ValueError("Admitted candidate counts changed")
        gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
        gmsh.option.setNumber("General.Terminal",1);gmsh.logger.start()
        for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
        report.update(stage="loading_exact_saved_Delaunay_mesh");checkpoint()
        gmsh.open(str(INPUT));before,report["before"]=load_before(core,gmsh,points,faces)
        if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError("Fixed optimizer options changed")
        optimize_and_refresh(gmsh,report,checkpoint)
        gmsh.write(str(path));report.update(mesh_sha256=core.sha(path),mesh_bytes=path.stat().st_size,
                                           stage="auditing_all_optimized_tetrahedra");checkpoint()
        after,report["after"]=audit_after(core,gmsh,points,faces)
        if not core.np.array_equal(before[1],after[1]) or report["before"]["classifications"]!=report["after"]["classifications"]:
            raise ValueError("Original node tags or classifications changed")
        interior=before[1]>len(points)
        old_cells=canonical_cells(core.np,before[3]);new_cells=canonical_cells(core.np,after[3])
        report["comparison"]=dict(tetrahedra_before=len(old_cells),tetrahedra_after=len(new_cells),
            canonical_volume_topology_changed=not core.np.array_equal(old_cells,new_cells),
            canonical_cells_before_sha256=core.array_sha(old_cells),canonical_cells_after_sha256=core.array_sha(new_cells),
            interior_node_coordinates_changed=int(core.np.count_nonzero(core.np.any(before[0][interior]!=after[0][interior],axis=1))),
            boundary_coordinates_changed=0,
            minimum_SICN_before_retained=report["before"]["retained_not_recomputed"]["quality"]["minimum_SICN"]["minimum"],
            minimum_SICN_after_actual=report["after"]["quality"]["minimum_SICN"]["minimum"])
        report["comparison"]["minimum_SICN_strictly_improved"]=(report["comparison"]["minimum_SICN_after_actual"]>
            report["comparison"]["minimum_SICN_before_retained"])
        report["comparison"]["actual_SICN_point1_gate_passed"]=report["comparison"]["minimum_SICN_after_actual"]>=.1
        del old_cells,new_cells,before
        report.update(stage="reading_back_the_single_optimized_mesh");checkpoint()
        gmsh.clear();gmsh.open(str(path));q,_,nt,et,en=core.tagged_volume(gmsh)
        if not all(core.np.array_equal(a,b) for a,b in zip(after,(q,nt,et,en))) or not core.matching_mesh(path,report["mesh_sha256"]):
            raise ValueError("Saved optimized tagged coordinates/connectivity or mesh bytes changed")
        report["saved_surface"]=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False)
        if classifications(core,gmsh,nt,len(points))!=report["after"]["classifications"]:
            raise ValueError("Saved node classifications or periodic identity changed")
        report.update(saved_mesh_identity_exact=True)
        quality=report["after"]["quality"]
        if any(q["nonpositive_count"] for q in quality.values()) or quality["minimum_SICN"]["minimum"]<.1:
            raise ValueError("Positive finite Jacobians/volumes and actual minimum SICN at least 0.1 required")
        if report["after"]["volume_relative_error"]>1e-6:raise ValueError("Candidate-relative volume bookkeeping exceeds 1e-6")
        report.update(status="completed_geometric_volume_quality_only",stage="finished")
        report["qualification"]["geometric_volume_gate_passed"]=True
    except Exception as exc:report.update(status="failed_outputs_preserved",error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:
            try:
                report["gmsh_warnings_errors"]=[s for s in gmsh.logger.get() if s.startswith(("Warning","Error"))]
                gmsh.logger.stop()
            except Exception as exc:
                report.update(status="failed_runtime_cleanup",cleanup_error=type(exc).__name__+": "+str(exc))
                report["qualification"]["geometric_volume_gate_passed"]=False
            try:gmsh.finalize()
            except Exception as exc:
                report.update(status="failed_runtime_cleanup",finalize_error=type(exc).__name__+": "+str(exc))
                report["qualification"]["geometric_volume_gate_passed"]=False
        try:
            core.require_admission(args.admission,args.admission_sha256)
            report["bound_inputs_unchanged"]=(core.sha(args.output/"surface-admission.json")==args.admission_sha256
                and all(core.sha(ROOT/p)==h and core.sha(args.output/"source-snapshots"/Path(p).name)==h
                        for p,h in launch["source_sha256s"].items()))
        except Exception:report["bound_inputs_unchanged"]=False
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_bound_input_drift");report["qualification"]["geometric_volume_gate_passed"]=False
        if report["qualification"]["geometric_volume_gate_passed"] and not core.matching_mesh(path,report.get("mesh_sha256")):
            report.update(status="failed_saved_mesh_drift");report["qualification"]["geometric_volume_gate_passed"]=False
        report["worker_wall_s"]=time.monotonic()-started;checkpoint()
    return 0 if report["qualification"]["geometric_volume_gate_passed"] else 2


def main(argv=None):
    require_inputs();core=configure_core()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission",type=Path,required=True);parser.add_argument("--admission-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if core.sha(Path(sys.executable).resolve())!=PYTHON_SHA256:raise ValueError("Selected native Python required")
    return core.worker(args) if args.worker else core.run(args)


if __name__=="__main__":raise SystemExit(main())
