"""One original-source endpoint pass; every candidate remains unadmitted."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import uuid

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve()
HELPER = HERE.with_name("run_finest_endpoint_preflight.py")
HELPER_SHA = "b214e1cece8dbf66be6071199cbdf1a8e22a2a59328888011de17492f923c86b"
METADATA_SOURCE = HERE.with_name("run_finest_endpoint_metadata.py")
METADATA_SHA = "a88477c47d406cea3761c324e1f6eb82dcb1c2b962698d7f328261c6cef2929b"
if (hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA
        or hashlib.sha256(METADATA_SOURCE.read_bytes()).hexdigest() != METADATA_SHA):
    raise ValueError("Frozen cleanup and metadata sources required before import")
SPEC = importlib.util.spec_from_file_location("frozen_finest_head_metadata", METADATA_SOURCE)
METADATA = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(METADATA)
BOUNDED = METADATA.CORE
ORIGINAL = "work/962-engineering/analysis-envelope-025-003/exact-input.bin"
ORIGINAL_SHA = "894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95"
COMPILE = "work/962-engineering/finest-surface-endpoint-compile-001/phase-summary.json"
COMPILE_SHA = "e67773720041eebd43f87effbd13560447c94895732b6d75623dafdcb61517ff"
BINARY = "work/962-engineering/finest-surface-endpoint-compile-001/compile-002/finest-endpoint"
BINARY_SHA = "e5779c184fc9f2e8680d9565f0c1075d4b615baef911f784b808051c3a4c2bdb"
TEST = "tests/test_962_finest_endpoint_head.py"
LIMITS = dict(cpus=2, memory_bytes=4294967296, swap_bytes=0, hard_wall_seconds=300, network="none")
LABELS = {"common-neighbor-source001": False, "common-neighbor-source002": True, "all-fixed-source002": False}


def current_hashes(pins):
    result = {}
    for name in pins:
        path = ROOT/name
        try:
            result[name] = BOUNDED.digest(path) if path.is_file() and not path.is_symlink() else None
        except OSError:
            result[name] = None
    return result


def fixture_pins(proof):
    """Called only after fixed completed fixtures exist; no pending record credited."""
    pins = {}
    for name in ["phase_summary", "metadata_receipt", "array_assessment", "root_review", "peer_review"]:
        row = proof[name]
        if BOUNDED.digest(ROOT/row["path"]) != row["sha256"]:
            raise ValueError("The completed fixture evidence changed")
        pins[row["path"]] = row["sha256"]
    summary_path = ROOT/proof["phase_summary"]["path"]
    summary = json.loads(summary_path.read_text())
    if (summary["phase"] != "fixtures" or summary["complete"] is not True
            or summary["preparation_sha256"] != BOUNDED.PREP_SHA or summary["image_id"] != BOUNDED.IMAGE
            or summary["controller_sha256"] != HELPER_SHA or summary["all_inputs_unchanged"] is not True
            or summary["all_prior_outputs_unchanged"] is not True
            or {r["label"] for r in summary["jobs"]} != set(LABELS)
            or any(r["execution_passed"] is not True for r in summary["jobs"])):
        raise ValueError("Three completed declared fixture executions are required")
    for name, sha in summary["artifact_sha256"].items():
        path = summary_path.parent/name
        if not path.is_file() or path.is_symlink() or BOUNDED.digest(path) != sha:
            raise ValueError("An original fixture artifact changed")
        pins[str(path.relative_to(ROOT))] = sha
    child = json.loads((summary_path.parent/"frozen-execution-contract.json").read_text())
    if (child["phase"] != "fixtures" or child["root_authorized"] is not True
            or child["compiled_binaries"]["002"] != dict(path=BINARY, sha256=BINARY_SHA)
            or child["compile_summary"] != dict(path=COMPILE, sha256=COMPILE_SHA)):
        raise ValueError("Fixture child does not bind the actual reviewed binary002")
    companion = json.loads((ROOT/proof["metadata_receipt"]["path"]).read_text())
    if (companion["metadata_companion"] != METADATA.companion_binding()
            or companion["core_phase_summary_sha256"] != proof["phase_summary"]["sha256"]
            or companion["execution_contract_sha256"] != summary["execution_contract_sha256"]
            or companion["all_additional_inputs_unchanged"] is not True
            or companion["core_returncode"] != 0 or companion["error"] is not None
            or companion["compiled_binaries_replaced"] is not False):
        raise ValueError("The separately attributed metadata companion proof did not pass")
    snapshot = summary_path.parent/"metadata-companion-executed.py"
    if BOUNDED.digest(snapshot) != METADATA_SHA or companion["companion_snapshot_sha256"] != METADATA_SHA:
        raise ValueError("Actual metadata companion snapshot differs from the frozen source")
    pins[str(snapshot.relative_to(ROOT))] = METADATA_SHA
    for table in [child["input_sha256"], companion["metadata_companion"]["input_sha256"]]:
        pins.update(table)
    pins[child["compile_summary"]["path"]] = child["compile_summary"]["sha256"]
    for row in child["compiled_binaries"].values():
        pins[row["path"]] = row["sha256"]
    inventory = set(summary["artifact_sha256"]) | {"phase-summary.json", "metadata-companion-executed.py",
        "metadata-companion-receipt.json", "fixture-array-assessment.json"}
    if {str(p.relative_to(summary_path.parent)) for p in summary_path.parent.rglob("*") if p.is_file()} != inventory:
        raise ValueError("The complete stopped fixture inventory changed")
    root_review = json.loads((ROOT/proof["root_review"]["path"]).read_text())
    if (root_review["status"] != "root_actual_fixture_readback_passed"
            or root_review["phase_summary_sha256"] != proof["phase_summary"]["sha256"]
            or root_review["metadata_receipt_sha256"] != proof["metadata_receipt"]["sha256"]
            or root_review["array_assessment_sha256"] != proof["array_assessment"]["sha256"]):
        raise ValueError("Actual fixture root review does not bind these outputs")
    assessed = json.loads((ROOT/proof["array_assessment"]["path"]).read_text())
    if (assessed["status"] != "synthetic_actual_array_checks_passed_execution_receipts_still_separate"
            or set(assessed["results"]) != set(LABELS)):
        raise ValueError("Complete independent actual fixture-array assessment required")
    for label, improves in LABELS.items():
        row = assessed["results"][label]
        if (row["before"]["below_necessary_bound"] != 2
                or row["after"]["below_necessary_bound"] != (0 if improves else 2)
                or row["after"]["triangles"] != (14 if improves else 16)
                or row["actual_vertices"] != (9 if improves else 10)
                or row["exact_signed_volume_mm3"] != 152**3
                or row["analytical_whole_surface_bidirectional_distance_mm"] != 0
                or any(row[k] is not True for k in ["all_fixed_coordinates_exact", "all_exterior_oriented_faces_exact",
                    "all_complete_coordinate_triangles_match_known_reference", "source_origin_map_independently_checked"])):
            raise ValueError("A predeclared numerical fixture expectation was not met")
    return pins


def expected_pins(proof):
    pins = fixture_pins(proof)
    for name in [str(HERE.relative_to(ROOT)), TEST]:
        pins[name] = BOUNDED.digest(ROOT/name)
    return pins


def reviewed_child(path, expected):
    if BOUNDED.digest(path) != expected or BOUNDED.digest(HELPER) != HELPER_SHA:
        raise ValueError("Exact head child and unchanged cleanup helper required")
    child = json.loads(path.read_text())
    if (child.get("schema") != "962-finest-endpoint-head-execution/v1" or child.get("root_authorized") is not True
            or child.get("root_and_peer_review_complete") is not True or child.get("limits") != LIMITS
            or child.get("maximum_passes") != 1 or child.get("automatic_retry") is not False
            or child.get("image_id") != BOUNDED.IMAGE):
        raise ValueError("A separately reviewed single-pass head child is required")
    if BOUNDED.digest(ROOT/BOUNDED.PREP) != BOUNDED.PREP_SHA or BOUNDED.digest(ROOT/COMPILE) != COMPILE_SHA:
        raise ValueError("Original preparation or actual compilation changed")
    pins = expected_pins(child["fixture_proof"])
    if pins.get(ORIGINAL) != ORIGINAL_SHA:
        raise ValueError("Only the exact original894ece source is supported")
    if pins.get(BINARY) != BINARY_SHA or pins.get(COMPILE) != COMPILE_SHA:
        raise ValueError("Actual binary002/compile proof changed")
    if child.get("input_sha256") != pins:
        raise ValueError("Every original/source/runtime/actual-fixture proof pin must be frozen")
    return child, pins


def run(contract_path, expected, output):
    child, pins = reviewed_child(contract_path, expected)
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(ROOT/"work/962-engineering"):
        raise ValueError("Fresh task-owned head output required")
    before = current_hashes(pins)
    if before != pins or BOUNDED.digest(contract_path) != expected or BOUNDED.INSPECT != METADATA.ORIGINAL_FORMAT:
        raise ValueError("Input drift refused before output creation or native launch")
    output.mkdir(parents=True); output = output.resolve()
    (output/"frozen-execution-contract.json").write_bytes(contract_path.read_bytes())
    (output/"head-controller-executed.py").write_bytes(HERE.read_bytes())
    (output/"cleanup-core-executed.py").write_bytes(HELPER.read_bytes())
    (output/"metadata-source-executed.py").write_bytes(METADATA_SOURCE.read_bytes())
    owner = uuid.uuid4().hex; name = "962-finest-original-head-"+owner[:10]
    mounts = [(str(output), "/out", True, "bind"),
              (str((ROOT/ORIGINAL).resolve()), "/original.bin", False, "bind"),
              (str((ROOT/BINARY).resolve()), "/finest-endpoint", False, "bind")]
    command = ["docker", "create", "--name", name, "--label", "io.962-finest.owner="+owner,
               "--network", "none", "--read-only", "--cpus", "2", "--memory", "4294967296", "--memory-swap", "4294967296"]
    for source, target, writable, _ in mounts:
        command += ["--mount", "type=bind,src="+source+",dst="+target+("" if writable else ",readonly")]
    command += ["--entrypoint", "/finest-endpoint", BOUNDED.IMAGE, "/original.bin", "/out/native"]
    controls = dict(NanoCpus=2000000000, Memory=4294967296, MemorySwap=4294967296,
                    NetworkMode="none", ReadonlyRootfs=True, Tmpfs=None)
    receipt = None; error = None
    BOUNDED.INSPECT = METADATA.CORRECTED_FORMAT
    try:
        receipt = BOUNDED.execute(command, name, owner, output, "original-head", 300, controls, mounts)
    except BaseException as exc:
        error = type(exc).__name__+": "+str(exc)
    finally:
        BOUNDED.INSPECT = METADATA.ORIGINAL_FORMAT
    after = current_hashes(pins)
    unchanged = after == pins and BOUNDED.digest(contract_path) == expected
    state = receipt["final_metadata"]["State"] if receipt and receipt["final_metadata"] else {}
    finished = (receipt is not None and not error and not receipt["error"] and not receipt["cleanup_errors"] and receipt["attach_reaped"]
                and receipt["owned_container_removed"] and receipt["attach_returncode"] in (0, 3)
                and state.get("ExitCode") == receipt["attach_returncode"] and state.get("Running") is False
                and state.get("OOMKilled") is False and unchanged)
    result = dict(schema="962-finest-original-head-execution-summary/v1",
        status="native_pass_stopped_independent_assessment_pending" if finished else "native_failure_or_stop_preserved",
        execution_contract_sha256=expected, actual_before_sha256=before, actual_after_sha256=after,
        all_inputs_unchanged=unchanged, native_pass_finished=finished, single_pass_request_attempted=True,
        native_attach_started=receipt["attach_process_started"] if receipt else None, error=error,
        source_attribution=dict(head_companion_sha256=BOUNDED.digest(HERE), cleanup_core_sha256=HELPER_SHA,
            metadata_source_sha256=METADATA_SHA,
            applied_inspect_format_sha256=hashlib.sha256(METADATA.CORRECTED_FORMAT.encode()).hexdigest(),
            scope="Frozen core execute/cleanup with the separately frozen one-field optional Tmpfs formatter; no core or binary replacement."),
        artifact_sha256=BOUNDED.file_hashes(output), automatic_retry=False,
        candidate_surface_admitted=False, independent_full_array_audit_completed=False,
        independent_whole_surface_bidirectional_distance_completed=False,
        independent_topology_features_intersections_completed=False, CUB_or_volume_calls=0,
        solver_admission_established=False, head_physics_executed=False, manufacturing_authorized=False)
    BOUNDED.save(output/"head-execution-summary.json", result)
    return 0 if finished else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def interrupt(signum, _frame):
        raise InterruptedError("Controller signal "+str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output))
