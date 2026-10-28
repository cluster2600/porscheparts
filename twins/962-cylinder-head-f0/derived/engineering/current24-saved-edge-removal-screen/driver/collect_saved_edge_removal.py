"""HELD saved-only fixed23-input complete55-edge driver functions; no CLI or authority.

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
WORKER=ROOT/"work/962-engineering/head-star-current24-edge-removal-prep-001/propose_saved_edge_removal.py"
WORKER_HELD=WORKER.parent/"held-preparation.json"
REPORT_REL="work/962-engineering/head-star-current110-pass62-application-001/worker-report.json"
PARENT_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/result-peer-acceptance.json"
CLOSED_REL="work/962-engineering/head-star-current110-pass62-application-root-execution-001/closed-result.json"
MANIFEST_REL="work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json"
SELECTED_REL="work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json"
CAP=32*1024**2


PRIOR_HELD_REL="work/962-engineering/head-star-current24-interior-flip-prep-001/held-preparation.json"
COUNTS_REL="work/962-engineering/head-star-current24-edge-star-next-step-assessment-001/reason-counts.json"
PRIOR_REPORT_REL="work/962-engineering/head-star-current24-interior-flip-saved-root-execution-001/report.json"
PRIOR_ACCEPTANCE_REL="work/962-engineering/head-star-current24-interior-flip-independent-verifier-root-review-001/result-peer-acceptance.json"


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


def exact23_inputs(pins):
    """Read only the fixed23 first-party input names, preserving every identity."""
    if len(pins)!=23:raise ValueError("Exact23 held inputs required")
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
    """Future exactly one complete55-edge family; no subset/application or new kernel."""
    held=strict_json(HELD.read_bytes());worker_held_raw=WORKER_HELD.read_bytes()
    if identity(WORKER_HELD,worker_held_raw)!=held["worker_held"]:
        raise ValueError("Worker held identity changed")
    worker_held=strict_json(worker_held_raw)
    if worker_held["input_records"]!=held["input_records"] or len(held["input_records"])!=23:
        raise ValueError("Same exact23 worker metadata inputs required")
    raw=WORKER.read_bytes()
    if identity(WORKER,raw)!=held["worker_source"]:raise ValueError("Worker source changed")
    inputs,before_inputs=exact23_inputs(held["input_records"])
    inherited=worker_held["inherited_intake_input_records"]
    if len(inherited)!=15 or any(held["input_records"].get(k)!=v for k,v in inherited.items()):
        raise ValueError("Original15 intake descriptors must be preserved inside23")
    if inputs[PRIOR_HELD_REL]["input_records"]!=inherited:
        raise ValueError("Original worker held15 intake association changed")
    counts=inputs[COUNTS_REL];prior_acceptance=inputs[PRIOR_ACCEPTANCE_REL]
    if (counts["source_report"]!=held["input_records"][PRIOR_REPORT_REL]
            or counts["root_finite_refusal_acceptance"]!=held["input_records"][PRIOR_ACCEPTANCE_REL]
            or prior_acceptance["saved_producer_report"]!=held["input_records"][PRIOR_REPORT_REL]
            or prior_acceptance["schema"]!="962-current24-finite-saved-flip-root-result-acceptance/v1"
            or prior_acceptance["finite_family_local_refusals_accepted"] is not True
            or prior_acceptance["independent_kernel_completion_accepted"] is not True):
        raise ValueError("Accepted204/report/reason-accounting descriptor joins required")
    # Deferred import only after a separately admitted future saved-metadata call.
    spec=importlib.util.spec_from_file_location("held_saved_edge_removal_worker",WORKER)
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    expected={name.replace("3_to_2:","edge:"):int(degree)
              for degree,names in counts["selected_next_source_scope"]["case_membership_by_degree"].items()
              for name in names}
    if expected!=worker.EXPECTED_EDGE_DEGREES or len(expected)!=55:
        raise ValueError("Exact55 saved case/degree identities required")
    context=worker.prepare_context(inputs[REPORT_REL],inputs[PARENT_REL],inputs[CLOSED_REL],
                                  inputs[MANIFEST_REL],inputs[SELECTED_REL],worker_held)
    before=context_snapshot(context);before_bytes=canonical_bytes(before)
    prior=inputs[PRIOR_REPORT_REL]
    if (prior["procedure_preservation_passed"] is not True
            or prior["complete_context_byte_identical"] is not True
            or canonical_bytes(prior["complete_context_before"])!=before_bytes
            or canonical_bytes(prior["complete_context_after"])!=before_bytes
            or prior["before_snapshot_sha256"]!=hashlib.sha256(before_bytes).hexdigest()
            or prior["after_snapshot_sha256"]!=hashlib.sha256(before_bytes).hexdigest()):
        raise ValueError("Exact accepted prior271/499/24/16 context association required")
    result=worker.screen_complete_saved_family(context) # Exactly ONE full family call.
    after=context_snapshot(context);after_bytes=canonical_bytes(after)
    _,after_inputs=exact23_inputs(held["input_records"])
    source_after=identity(WORKER,WORKER.read_bytes());worker_held_after=identity(WORKER_HELD,WORKER_HELD.read_bytes())
    unchanged=(before_bytes==after_bytes and before_inputs==after_inputs
               and source_after==held["worker_source"] and worker_held_after==held["worker_held"])
    if (canonical_bytes(result["context_before"])!=before_bytes
            or canonical_bytes(result["context_after"])!=after_bytes
            or result["complete_context_byte_identical"] is not True):
        raise ValueError("Worker/external complete context snapshots disagree")
    if (result["selected_case_count"]!=55 or len(result["selected_complete_edge_stars"])!=55
            or result["candidate_count"]!=len(result["all_candidate_rows"])
            or not 0<=result["candidate_count"]<=1033
            or result["all_failed_unavailable_and_outside_rows_retained"] is not True
            or result["conflicts"]["all_pairs_represented_without_truncation"] is not True):
        raise ValueError("Complete finite case/candidate/conflict rows required")
    if (result["complete_application_eligibility"] is not None
            or result["mesh_application_authorized"] is not False
            or result["whole_head_embedding_or_nonoverlap_accepted"] is not False
            or any(r["complete_application_eligibility"] is not None
                   or r["mesh_application_authorized"] is not False for r in result["all_candidate_rows"])):
        raise ValueError("No complete eligibility, whole-head or application acceptance allowed")
    stars=inputs[REPORT_REL]["after"]["complete_native_census"]["complete_seed_star_census"]
    result.update(all_finite_rows_retained=True,procedure_preservation_passed=unchanged,
        input_records_before=before_inputs,input_records_after=after_inputs,
        worker_source=held["worker_source"],worker_source_after=source_after,
        worker_held=held["worker_held"],worker_held_after=worker_held_after,
        before_snapshot_sha256=hashlib.sha256(before_bytes).hexdigest(),
        after_snapshot_sha256=hashlib.sha256(after_bytes).hexdigest(),
        accepted_prior_flip_report=held["input_records"][PRIOR_REPORT_REL],
        accepted_prior_flip_root=held["input_records"][PRIOR_ACCEPTANCE_REL],
        all23_descriptor_and_original15_intake_joins_checked=True,
        full_saved_native_cell_rows=copy.deepcopy(stars["complete_incident_tetrahedra"]),
        full_saved_coordinate_classification_rows=copy.deepcopy(stars["unique_incident_nodes"]),
        serialization="Complete canonical compact JSON, all logical fields/rows/types unchanged; no truncation",
        raw_MSH_BIN_native_fields_or_runtime_body_read=False,automatic_retry=False)
    # Whitespace-only capacity reduction; complete values/arrays and rational strings remain.
    encoded=canonical_bytes(result)+b"\n"
    if len(encoded)>CAP:raise ValueError("Complete saved edge screen exceeds32MiB; refuse without truncation")
    return result,encoded
