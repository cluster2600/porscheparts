"""HELD saved-only fixed499/271 flip driver functions; no CLI or authority.

No function in this file has been executed. Root must separately admit a fixed
future caller, synthetic evidence and input/output/runtime/control closure.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[3]
PREP=Path(__file__).resolve().parent
HELD=PREP/"held-preparation.json"
WORKER=ROOT/"work/962-engineering/head-star-current24-interior-flip-prep-001/propose_saved_cavity_flips.py"
WORKER_HELD=WORKER.parent/"held-preparation.json"
REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
PARENT_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
MANIFEST_REL="work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json"
SELECTED_REL="work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json"
CAP=32*1024**2


def identity(path,data):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


def strict_json(data):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError("Duplicate JSON member: "+key)
            result[key]=value
        return result
    def constant(value):raise ValueError("Nonfinite JSON token: "+value)
    return json.loads(data,object_pairs_hook=pairs,parse_constant=constant)


def exact15_inputs(pins):
    """Read only the fixed15 first-party input names, preserving every identity."""
    if len(pins)!=15:raise ValueError("Exact15 held inputs required")
    data={};records={}
    for name,pin in sorted(pins.items()):
        path=ROOT/name
        if pin["path"]!=name or not name.startswith("work/962-engineering/"):
            raise ValueError("Fixed first-party relative input required")
        raw=path.read_bytes();got=identity(path,raw)
        if got!=pin:raise ValueError("Held input changed: "+name)
        records[name]=got
        # Source/rationale inputs are byte-associated, not imported or evaluated.
        data[name]=strict_json(raw) if path.suffix==".json" else raw
    return data,records


def context_snapshot(context):
    """Complete case-specific snapshot, including actual signed-zero word bits."""
    expected={"points","words","cells","poor","seeds","protected_cells",
              "protected_nodes","intake","classification_rows"}
    if set(context)!=expected:raise ValueError("Unexpected context field set")
    return dict(points=[dict(node_tag=t,coordinates_mm=list(p),
                    actual_coordinate_binary64_hex=[float(v).hex() for v in p],
                    actual_coordinate_words_le_hex=struct.pack("<3d",*p).hex())
                for t,p in sorted(context["points"].items())],
        words=[[t,list(w)] for t,w in sorted(context["words"].items())],
        cells=[dict(tetrahedron_tag=t,ordered_node_tags=list(c))
               for t,c in sorted(context["cells"].items())],
        poor=sorted(context["poor"]),seeds=sorted(context["seeds"]),
        protected_cells=sorted(context["protected_cells"]),
        protected_nodes=sorted(context["protected_nodes"]),
        intake=copy.deepcopy(context["intake"]),
        classification_rows=copy.deepcopy(context["classification_rows"]))


def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def build_saved_report():
    """Future fixed complete operation; no selection, application or new kernel."""
    held=strict_json(HELD.read_bytes());worker_held_raw=WORKER_HELD.read_bytes()
    if identity(WORKER_HELD,worker_held_raw)!=held["worker_held"]:
        raise ValueError("Worker held identity changed")
    worker_held=strict_json(worker_held_raw)
    if worker_held["input_records"]!=held["input_records"] or len(held["input_records"])!=15:
        raise ValueError("Same exact15 worker inputs required")
    raw=WORKER.read_bytes()
    if identity(WORKER,raw)!=held["worker_source"]:
        raise ValueError("Worker source changed")
    inputs,before_inputs=exact15_inputs(held["input_records"])
    # This import is deferred to a separately admitted future saved-data call.
    spec=importlib.util.spec_from_file_location("held_saved_flip_worker",WORKER)
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    context=worker.prepare_context(inputs[REPORT_REL],inputs[PARENT_REL],inputs[CLOSED_REL],
                                  inputs[MANIFEST_REL],inputs[SELECTED_REL],worker_held)
    before=context_snapshot(context);before_bytes=canonical_bytes(before)
    associations=worker.enumerate_associations(context)
    # Includes nonpatterns: the worker retains their explicit local refusal.
    local_results=[worker.screen_local_cavity(context,row) for row in associations]
    conflicts=worker.association_conflicts(associations)
    after=context_snapshot(context);after_bytes=canonical_bytes(after)
    _,after_inputs=exact15_inputs(held["input_records"])
    worker_source_after=identity(WORKER,WORKER.read_bytes())
    worker_held_after=identity(WORKER_HELD,WORKER_HELD.read_bytes())
    unchanged=(before_bytes==after_bytes and before_inputs==after_inputs
               and worker_source_after==held["worker_source"]
               and worker_held_after==held["worker_held"])
    if len(before["points"])!=271 or len(before["cells"])!=499 or len(before["poor"])!=24:
        raise ValueError("Full271/499/24 context required")
    if len(associations)!=len(local_results) or len({r["association_ID"] for r in associations})!=len(associations):
        raise ValueError("Every unique association needs one local disposition")
    if [r["association_ID"] for r in associations]!=[r["association_ID"] for r in local_results]:
        raise ValueError("Complete ordered association/disposition join required")
    if any(r["complete_flip_eligibility"] is not None or r["mesh_application_authorized"] is not False
           for r in local_results):raise ValueError("Eligibility must remain unresolved and application false")
    counts={}
    for row in local_results:counts[row["local_result"]]=counts.get(row["local_result"],0)+1
    stars=inputs[REPORT_REL]["after"]["complete_native_census"]["complete_seed_star_census"]
    result=dict(schema="962-current24-complete-saved-interior-flip-local-screen/v1",
        status="complete_saved_local_screen_only_eligibility_unavailable" if unchanged else "refused_context_or_input_change",
        all_finite_rows_retained=True,procedure_preservation_passed=unchanged,
        input_records_before=before_inputs,input_records_after=after_inputs,
        worker_source=held["worker_source"],worker_source_after=worker_source_after,
        worker_held=held["worker_held"],worker_held_after=worker_held_after,
        complete_context_before=before,complete_context_after=after,
        before_snapshot_sha256=hashlib.sha256(before_bytes).hexdigest(),
        after_snapshot_sha256=hashlib.sha256(after_bytes).hexdigest(),
        complete_context_byte_identical=before_bytes==after_bytes,
        full_saved_native_cell_rows=copy.deepcopy(stars["complete_incident_tetrahedra"]),
        full_saved_coordinate_classification_rows=copy.deepcopy(stars["unique_incident_nodes"]),
        association_count=len(associations),associations=associations,
        local_disposition_count=len(local_results),local_status_counts=counts,
        complete_local_dispositions=local_results,observed_pair_conflicts=conflicts,
        observed_pair_conflict_count=len(conflicts),complete_flip_eligibility=None,
        source_interface_region_exterior_or_BIN_evidence=None,
        global_embedding_or_nonoverlap_accepted=False,mesh_application_authorized=False,
        head_PDE_or_strength_or_material_or_LPBF_or_manufacturing_accepted=False,
        raw_MSH_BIN_or_native_runtime_body_read=False,optimizer_called=False,
        combined_subset_or_flip_sequence_selected=False,automatic_retry=False,
        limits="Finite known-context family only; missing owners/interfaces remain unavailable. No global infeasibility or topology necessity follows.")
    # Full serialization either fits or refuses. No truncation or empty inference.
    encoded=(json.dumps(result,indent=2,allow_nan=False)+"\n").encode("utf-8")
    if len(encoded)>CAP:raise ValueError("Complete saved screen exceeds32MiB; refuse without truncation")
    return result,encoded
