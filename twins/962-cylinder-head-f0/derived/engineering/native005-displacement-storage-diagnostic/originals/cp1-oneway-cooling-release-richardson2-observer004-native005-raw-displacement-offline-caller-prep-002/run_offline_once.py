"""HELD/UNRUN fixed one-process offline caller; no subprocess/supervisor."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import types

ROOT=Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
D=ROOT/"work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-raw-displacement-diagnostic-execution-002"
CAP=33554432
SOURCES={
  "strict": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-field-collector-prep-001/collect_current_associations.py",
    "sha256": "e69fdefee51675c8747acf9ad55566de2797dac9740648a9f86d03349c626b68",
    "bytes": 19192
  },
  "parser": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-saved-measurement-parser-prep-003/parse_saved_measurement.py",
    "sha256": "3c5bfbc739bb796b6ea63f4373a8984f1702ec3cfdf4883f9903df9bf483e0f4",
    "bytes": 13219
  },
  "assessor": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/assess.py",
    "sha256": "aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5",
    "bytes": 46645
  },
  "diagnostic": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-raw-displacement-diagnostic-prep-003/diagnose_raw_displacements.py",
    "sha256": "9e9e08e518d2f84067cdf8535954928bcb172f9c3ef12d617da7c1a02041845e",
    "bytes": 15404
  }
}
RUNTIME={
  "path": "work/962-engineering/native005-raw-displacement-decoder-runtime-root-001/acceptance.json",
  "sha256": "5dbf28e11b6fcd7c4770bb40a042a58735ab98485a592b857e3293eb5dab8376",
  "bytes": 9673
}
DIAGNOSTIC_ROOT={"path":"work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-raw-displacement-diagnostic-root-source-review-003/review.json","sha256":"c62e6e795cbb6212210575808a736081de57585062f85b76fc26e71ec184cdfb","bytes":3988}
THREAD_ENV={k:"1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS")}
LAUNCH_ENV={"PATH":"/usr/bin:/bin","LANG":"C","LC_ALL":"C",**THREAD_ENV}
REQUIRED_ROLES={"diagnostic_source_peer","diagnostic_root_source_review","fixture_acceptance","caller_source_peer","caller_root_source_review","caller_METHOD","caller_bindings","caller_index","diagnostic_METHOD","diagnostic_bindings","diagnostic_index","operational_root"}


def need(ok,message):
    if not ok: raise ValueError(message)


def path(pin):
    p=Path(pin["path"]);p=p if p.is_absolute() else ROOT/p
    need(p.is_absolute() and ".." not in p.parts and p.resolve(strict=True)==p and p.is_file() and not p.is_symlink(),"Canonical admitted file required")
    return p


def read(pin):
    need(type(pin) is dict and set(pin)=={"path","sha256","bytes"} and type(pin["bytes"]) is int and 0<=pin["bytes"]<=CAP,"Finite exact descriptor required")
    p=path(pin)
    with p.open("rb") as f: raw=f.read(pin["bytes"]+1)
    need(len(raw)==pin["bytes"] and hashlib.sha256(raw).hexdigest()==pin["sha256"],"Admitted bytes changed: "+str(p))
    return raw


def load_source(key):
    pin=SOURCES[key];p=path(pin);name="native005_saved_"+key
    need(name not in sys.modules,"Fresh ordinary module alias required")
    module=types.ModuleType(name);module.__file__=str(p);module.__package__=""
    sys.modules[name]=module
    exec(compile(read(pin),str(p),"exec"),module.__dict__)
    return module


def union(pins):
    result={}
    for pin in pins:
        p=str(path(pin))
        need(p not in result or result[p]==pin,"Conflicting descriptor for one canonical path")
        result[p]=pin
    return result


def census(records,outer):
    selected=set(records)|{str(D/"binding.json")}|set(outer)
    for p in D.iterdir():
        need(p.is_file() and not p.is_symlink(),"Only fixed ordinary output files are supported")
        selected.add(str(p))
    rows=[{"path":p,"bytes":Path(p).stat().st_size} for p in sorted(selected)]
    need(sum(r["bytes"] for r in rows)<=CAP,"Complete scoped inclusive32MiB census exceeded")
    return {"paths":len(rows),"bytes":sum(r["bytes"] for r in rows),"rows":rows,"full_ABI_scope":False}


def main():
    start=time.monotonic()
    need(len(sys.argv)==2 and sys.version_info[:3]==(3,12,11) and sys.flags.isolated==1 and sys.dont_write_bytecode,"Fixed3.12.11 -B -I invocation required")
    binding_path=D/"binding.json"
    need(binding_path.resolve(strict=True)==binding_path and binding_path.is_file() and not binding_path.is_symlink(),"Canonical fixed binding path required")
    with binding_path.open("rb") as f: raw=f.read(1048577)
    need(0<len(raw)<=1048576 and hashlib.sha256(raw).hexdigest()==sys.argv[1],"Sole external binding digest required")
    helper=load_source("strict");binding=helper.strict_json(raw)
    need(binding["schema"]=="962-native005-raw-displacement-diagnostic-intake/v1" and binding["root_issued"] is True and binding["raw_saved_data_diagnostic_authorized"] is True and type(binding["invocations"]) is int and binding["invocations"]==1,"Separate fixed once-only root intake required")
    need(all(binding[k] is True for k in ("independent_source_review_complete","root_source_review_complete","selected_decoder_runtime_review_complete","control_role_semantics_accepted_by_root")),"Source/runtime/control semantics gates missing")
    need(all(binding[k] is False for k in ("native_execution_authorized","runtime_query_authorized","strict_semantic_acceptance","field_association_accepted","full_mechanical_assessment_authorized","physics_qualified","material_qualified","manufacturing_authorized","automatic_retry")) and "binding_sha256" not in binding,"No qualification/native/retry or self-hash authority")
    expected={k:v for k,v in helper.FILES.items() if k not in ("BEGIN80_nodal","BEGIN80_reference")}
    need(binding["captured_input_records"]==expected and len(expected)==12 and sum(p["bytes"] for p in expected.values())==16493574,"Exact12 captured inputs required")
    need(binding["source_dependencies"]=={"strict_helpers":SOURCES["strict"],"parser":SOURCES["parser"],"assessor":SOURCES["assessor"]} and binding["loaded_source_records"]==SOURCES and binding["operational_root"]==helper.OPERATIONAL_ROOT and binding["runtime_acceptance"]==RUNTIME,"Fixed source/operational/runtime identities required")
    need(REQUIRED_ROLES<=set(binding["control_records"]) and binding["control_records"]["operational_root"]==helper.OPERATIONAL_ROOT and binding["control_records"]["diagnostic_root_source_review"]==DIAGNOSTIC_ROOT,"Complete finite root-reviewed control roles required")
    need(all(str(path(p)).startswith(str(ROOT/"work/962-engineering")+"/") for p in binding["control_records"].values()),"Only named first-party engineering control records are supported")
    need(path(binding["caller"])==Path(__file__).resolve(strict=True) and binding["thread_environment"]==THREAD_ENV and binding["launch_environment"]==LAUNCH_ENV and all(os.environ.get(k)==v for k,v in LAUNCH_ENV.items()),"Fixed caller and minimal thread-one environment required")
    need(binding["lifecycle"]=={"parent_whole_seconds":60,"parent_wait_reap_required":True,"no_child_processes":True,"scoped_inclusive_bytes":CAP,"live_RSS_stop_claim":False,"retry":False},"Fixed external lifecycle/census scope required")
    rt=helper.strict_json(read(RUNTIME))
    need(rt["decision"]=="ACCEPT_SELECTED_IMPORT_READINESS_AND_22_CURRENT_MODULE_PINS_ONLY" and sys.executable==rt["python"]["executable"] and rt["python"]["version"]==[3,12,11] and binding["selected_runtime_records"]==rt["selected_module_records"] and len(rt["selected_module_records"])==22 and rt["complete_transitive_Python_native_library_ABI_proof"] is False,"Selected partial22-module runtime scope required")
    records=union([*SOURCES.values(),binding["caller"],RUNTIME,*expected.values(),*rt["selected_module_records"],*binding["control_records"].values()])
    need(str(binding_path) not in records,"Binding cannot require its own descriptor/hash")
    need(type(binding["initial_unique_records"]) is int and binding["initial_unique_records"]==len(records) and type(binding["initial_unique_bytes"]) is int and binding["initial_unique_bytes"]==sum(p["bytes"] for p in records.values()),"Exact initial finite union/count required")
    need(sum(p["bytes"] for p in records.values())+len(raw)<=CAP,"Initial admitted scoped bytes exceed32MiB")
    need(binding["outer_stream_paths"]==[str(D/"outer.stdout"),str(D/"outer.stderr")],"Fixed parent raw stream paths required")
    need(set(p.name for p in D.iterdir())<={"binding.json","outer.stdout","outer.stderr"},"Fresh output root required")
    for pin in records.values(): read(pin)
    census(records,binding["outer_stream_paths"])
    # Root parent exclusively captures outer streams and bounds the full process.
    with (D/"stdout.log").open("x") as out,(D/"stderr.log").open("x") as err,contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        try:
            import numpy
            import scipy
            from scipy.io import netcdf_file
            need(numpy.__version__=="2.2.6" and scipy.__version__=="1.17.1","Exact selected decoder versions required")
            admitted={p["path"] for p in rt["selected_module_records"]}
            need(all(str(Path(p).resolve(strict=True)) in admitted for p in (numpy.__file__,scipy.__file__,sys.modules[netcdf_file.__module__].__file__)),"Selected decoder module origins changed")
            parser=load_source("parser");assessor=load_source("assessor");diagnostic=load_source("diagnostic")
            report=diagnostic.diagnose_saved_displacements(raw,sys.argv[1],parser,assessor,helper)
            need(numpy.__version__=="2.2.6" and scipy.__version__=="1.17.1" and all(str(Path(p).resolve(strict=True)) in admitted for p in (numpy.__file__,scipy.__file__,sys.modules[netcdf_file.__module__].__file__)),"Selected decoder versions/origins changed during decode")
            encoded=(json.dumps(report,allow_nan=False)+"\n").encode("utf-8")
            need(len(encoded)<=CAP,"Complete diagnostic report exceeds capacity")
            with (D/"report.json").open("xb") as f: f.write(encoded)
            for pin in records.values(): read(pin)
            need(binding_path.read_bytes()==raw,"Binding changed during operation")
            metadata={"schema":"962-native005-offline-displacement-caller/v1","phase":"diagnostic_returned_pending_parent_final_acceptance","binding_sha256":sys.argv[1],"loaded_source_records":SOURCES,"selected_runtime_acceptance":RUNTIME,"numpy_version":numpy.__version__,"scipy_version":scipy.__version__,"selected_runtime_records":rt["selected_module_records"],"partial_runtime_only":True,"full_ABI_proved":False,"source_and_admitted_input_final_hashes_exact":True,"strict_dt_scaling_semantics_accepted":False,"field_or_physics_accepted":False,"live_RSS_stop_observed":False,"parent_wait_reap_and_whole60s_postchecks_required":True,"elapsed_before_receipt_seconds":time.monotonic()-start}
            with (D/"caller-result.json").open("x") as f: json.dump(metadata,f,allow_nan=False);f.write("\n")
            out.flush();err.flush()
            summary=census(records,binding["outer_stream_paths"])
            print(json.dumps({"scoped_final_paths":summary["paths"],"scoped_final_bytes":summary["bytes"],"field_or_physics_accepted":False}))
            out.flush();err.flush()
            census(records,binding["outer_stream_paths"])
            return 0
        except BaseException:
            text=traceback.format_exc()
            with (D/"traceback.log").open("x") as f: f.write(text)
            err.write(text);err.flush();out.flush()
            return 1


if __name__=="__main__":
    raise SystemExit(main())

