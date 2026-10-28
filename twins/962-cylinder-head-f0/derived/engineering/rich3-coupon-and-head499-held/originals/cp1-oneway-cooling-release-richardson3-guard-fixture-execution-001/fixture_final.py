"""One finite pure-validator fixture; no whole target import or native invocation."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import traceback

R = Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
P = R / "work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-prep-001"
PINS = {'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-prep-001/run_native_capture.py': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-prep-001/run_native_capture.py', 'sha256': '4d8465d99200d4fc2545e7396f375850387d1c898c191e78ba28b8ec048b7699', 'bytes': 48904}, 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-prep-001/run_root_once.py': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-prep-001/run_root_once.py', 'sha256': '44506e8b3129ffe2cc6fc03cdc8826a93381292abd28990008570e77644c63c6', 'bytes': 64699}, 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004/actual-contract.json': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004/actual-contract.json', 'sha256': 'a5e35548cacd4f2abfd4f0d29e5aeb738ce16bdc814f642e016851c3450f1986', 'bytes': 273368}, 'work/962-engineering/cp1-oneway-cooling-release-richardson3-four-input-staging-root-001/staging-receipt.json': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson3-four-input-staging-root-001/staging-receipt.json', 'sha256': '9f4d533da7da07b0c95054076b6fa4ec455f0f283f7b875aa53ad57f9e734f1c', 'bytes': 3966}, 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-host-registration-check-prep-001/thermoelastic-birth-observer-registration.i': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-host-registration-check-prep-001/thermoelastic-birth-observer-registration.i', 'sha256': '190296e6c2ad1627feca4b374efd2c49739e0c2628764cd92388392a78fd2682', 'bytes': 15537}, 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001/thermoelastic-birth-observer-registration.i': {'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001/thermoelastic-birth-observer-registration.i', 'sha256': 'e351ee1be793120084464edab51fc96d36e5677e6bb8d2e05caccc1fa85cdbbd', 'bytes': 15537}}
NAME = "thermoelastic-birth-observer-registration.i"
OLD_ACTUAL = "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-execution-prep-004/actual-contract.json"
STAGING = "work/962-engineering/cp1-oneway-cooling-release-richardson3-four-input-staging-root-001/staging-receipt.json"
OLD_DECK = "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-host-registration-check-prep-001/thermoelastic-birth-observer-registration.i"
NEW_DECK = "work/962-engineering/cp1-oneway-cooling-release-richardson3-observer004-native-measurement-001/thermoelastic-birth-observer-registration.i"

def exact_bytes(relative):
    pin = PINS[relative]
    data = (R / relative).read_bytes()
    assert len(data) == pin["bytes"] and hashlib.sha256(data).hexdigest() == pin["sha256"]
    return data

old_actual = json.loads(exact_bytes(OLD_ACTUAL))
staging = json.loads(exact_bytes(STAGING))
baseline_profile = old_actual["solver_profile"]
current_profile = copy.deepcopy(baseline_profile)
assert baseline_profile["petsc_options_iname"].index("-ksp_max_it") == 7
current_profile["petsc_options_value"][7] = "3"
current_profile["linear_updates_per_regular_solve"] = 3
current_profile["linear_stopping"] = "KSPConvergedSkip count completion after exactly3 updates, not residual-accuracy acceptance"
baseline_stage = old_actual["staged_inputs"]
current_stage = staging["staged_inputs"]
buffers = {OLD_DECK: exact_bytes(OLD_DECK), NEW_DECK: exact_bytes(NEW_DECK)}
assert [(i,a,b) for i,(a,b) in enumerate(zip(buffers[OLD_DECK],buffers[NEW_DECK])) if a != b] == [(14954,50,51)]
assert len(buffers[OLD_DECK]) == len(buffers[NEW_DECK]) == 15537
assert set(current_stage) == set(baseline_stage) and len(current_stage) == 4
for name in current_stage:
    if name != NAME:
        assert (current_stage[name]["sha256"],current_stage[name]["bytes"]) == (baseline_stage[name]["sha256"],baseline_stage[name]["bytes"])

rows = []
extracted = []
requests = []
active_buffers = dict(buffers)

class MemorySource:
    def __init__(self, path):
        self.path = path
    def read_bytes(self):
        return active_buffers[self.path]

def selected(pin):
    assert pin["path"] in buffers, "Only the two explicitly pinned source buffers are available"
    expected = PINS[pin["path"]]
    assert pin == expected, "Selected source descriptor must be exact"
    requests.append(pin["path"])
    return MemorySource(pin["path"])

def call(until, label, function):
    assert until is None and label in {"rich3-baseline-deck-buffer","rich3-current-deck-buffer"}
    return function()

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def exercise(unit, case, function, current, baseline, refused, changed_buffer=False):
    global active_buffers
    active_buffers = dict(buffers)
    if changed_buffer:
        raw = buffers[NEW_DECK]
        active_buffers[NEW_DECK] = raw[:100] + bytes([raw[100] ^ 1]) + raw[101:]
    before = copy.deepcopy((current, baseline))
    try:
        result = function(current, baseline)
    except AssertionError:
        if not refused:
            raise
        observation = "refused"
    else:
        assert not refused, "Mutation unexpectedly accepted"
        assert result is True
        observation = "accepted"
    assert (current, baseline) == before, "Validator mutated its inputs"
    rows.append({"unit":unit,"case":case,"expected":"refused" if refused else "accepted","observed":observation,"pass":True})

for name, assertion_name in [("run_native_capture.py","need"),("run_root_once.py","require")]:
    path = str((P/name).relative_to(R))
    text = exact_bytes(path).decode("utf-8")
    tree = ast.parse(text, filename=path)
    functions = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {"validate_rich3_profile","validate_rich3_staged"}]
    assert len(functions) == 2 and {n.name for n in functions} == {"validate_rich3_profile","validate_rich3_staged"}
    scope = {"__builtins__":{"dict":dict,"list":list,"len":len,"set":set,"type":type,"int":int},assertion_name:require,"hashlib":hashlib,"selected":selected,"call":call}
    exec(compile(ast.Module(body=functions,type_ignores=[]),path+":EXTRACTED_VALIDATORS_ONLY","exec"),scope)
    extracted.append({"unit":name,"functions":[{"name":n.name,"first_line":n.lineno,"last_line":n.end_lineno} for n in functions]})
    profile = scope["validate_rich3_profile"]
    staged = scope["validate_rich3_staged"]
    exercise(name,"profile_exact_RICH3",profile,copy.deepcopy(current_profile),copy.deepcopy(baseline_profile),False)
    for label,value in [("count_2",2),("count_bool",True),("count_float",3.0)]:
        bad = copy.deepcopy(current_profile); bad["linear_updates_per_regular_solve"] = value
        exercise(name,"profile_"+label,profile,bad,copy.deepcopy(baseline_profile),True)
    bad = copy.deepcopy(current_profile); bad["petsc_options_value"][baseline_profile["petsc_options_iname"].index("-pc_type")] = "jacobi"
    exercise(name,"profile_PC_change",profile,bad,copy.deepcopy(baseline_profile),True)
    bad = copy.deepcopy(current_profile); bad["linear_stopping"] += " drift"
    exercise(name,"profile_description_drift",profile,bad,copy.deepcopy(baseline_profile),True)
    bad = copy.deepcopy(current_profile); bad["unexpected"] = True
    exercise(name,"profile_unexpected_key",profile,bad,copy.deepcopy(baseline_profile),True)
    badbase = copy.deepcopy(baseline_profile); badbase["petsc_options_value"][7] = "3"
    exercise(name,"profile_bad_baseline",profile,copy.deepcopy(current_profile),badbase,True)
    exercise(name,"staged_exact_RICH3",staged,copy.deepcopy(current_stage),copy.deepcopy(baseline_stage),False)
    bad = copy.deepcopy(current_stage); bad[NAME]["sha256"] = baseline_stage[NAME]["sha256"]
    exercise(name,"staged_old_deck_hash",staged,bad,copy.deepcopy(baseline_stage),True)
    bad = copy.deepcopy(current_stage); bad["old-end.grid"]["sha256"] = "0"*64
    exercise(name,"staged_wrong_grid_hash",staged,bad,copy.deepcopy(baseline_stage),True)
    bad = copy.deepcopy(current_stage); del bad["born-begin80.grid"]
    exercise(name,"staged_missing_basename",staged,bad,copy.deepcopy(baseline_stage),True)
    bad = copy.deepcopy(current_stage); bad["extra.grid"] = copy.deepcopy(bad["old-end.grid"])
    exercise(name,"staged_extra_basename",staged,bad,copy.deepcopy(baseline_stage),True)
    bad = copy.deepcopy(current_stage); bad[NAME]["bytes"] += 1
    exercise(name,"staged_wrong_bytes",staged,bad,copy.deepcopy(baseline_stage),True)
    badbase = copy.deepcopy(baseline_stage); badbase[NAME]["sha256"] = current_stage[NAME]["sha256"]
    exercise(name,"staged_bad_baseline",staged,copy.deepcopy(current_stage),badbase,True)
    exercise(name,"staged_changed_returned_buffer",staged,copy.deepcopy(current_stage),copy.deepcopy(baseline_stage),True,True)

assert len(rows) == 32 and all(r["pass"] for r in rows)
assert set(requests) == {OLD_DECK,NEW_DECK}
print(json.dumps({"schema":"962-rich3-pure-validator-fixture/v1","status":"ALL_32_FINITE_CASES_PASS","rows":rows,"extracted":extracted,"selected_buffer_paths":sorted(set(requests)),"expectation_source":"Frozen oldactual004 solver/stage metadata and separate root RICH3 staging receipt; independently pinned whole deck buffers.","whole_target_module_executed":False,"grid_or_native_or_runtime_provider_body_read":False,"native_execution_or_scientific_qualification":False},indent=2,allow_nan=False))
