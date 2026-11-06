"""Prepare a held source generation; never issue admission or execute it."""
import ast
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HISTORICAL = Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
ENGINEERING = HISTORICAL / "work/962-engineering"
OLD_PREP = "head-star-current24-qfnra-five-toy-owner-prep-005"
NEW_PREP = "head-star-current24-qfnra-five-toy-owner-rebind-20261107"
OLD_OUTPUT = "head-star-current24-qfnra-five-toy-root-execution-002"
NEW_OUTPUT = "head-star-current24-qfnra-five-toy-root-execution-20261107"
SOLVER = Path("/Users/maxime/Developer/PorschePartsArtifacts/962-z3-recovery-20261106/z3")
SOLVER_SHA = "b9a2c3a7dc833da652955116ad743cc733aa7938dbe64f528f71cb09066e2512"
OLD_TRANSPORT = "3619b5316cf23398ed479ebf724a1159bb816ce3bafb85ad93c40b67b7df4990"
OLD_CHOICE = "e515e203bf928a57efbe44ebfb2c20da2e127dbfae5b690897175c0b86db0322"
PUBLIC = REPO / "twins/962-cylinder-head-f0/derived/engineering"
OWNER_PUBLIC = PUBLIC / "current24-parser003-and-five-toy-second-attempt/originals" / OLD_PREP
SOURCES = {
    "run_owner_once.py": (OWNER_PUBLIC / "run_owner_once.py", "a78c546e2fd343a46f712e84e47132774abf046736177f7cb8eeea2958375fa8"),
    "run_fixed_adapter.py": (OWNER_PUBLIC / "run_fixed_adapter.py", "587110ffc30b47a6e367f050b7c3316a32169ad67cc2602ddf527c7a9d3a2e5f"),
    "stopped_exec_wrapper.py": (OWNER_PUBLIC / "stopped_exec_wrapper.py", "62294417b7a293b85eaa142a6743b7ba8c3ffb14a70555644e4137f4c6a627bc"),
    "check_toy_sessions.py": (PUBLIC / "current24-toy-model-parser003-held/originals/head-star-current24-qfnra-toy-transport-prep-003/check_toy_sessions.py", OLD_TRANSPORT),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def rebind(raw, expected, replacements):
    if digest(raw) != expected:
        raise ValueError("Frozen source hash mismatch")
    text = raw.decode()
    for old, new in replacements:
        if text.count(old) != 1 or new in text:
            raise ValueError("Nonunique or preexisting source replacement")
        text = text.replace(old, new, 1)
    inverse = text
    for old, new in reversed(replacements):
        if inverse.count(new) != 1:
            raise ValueError("Ambiguous inverse replacement")
        inverse = inverse.replace(new, old, 1)
    if inverse.encode() != raw:
        raise ValueError("Source inverse differs")
    ast.parse(text)
    return text.encode()


def render():
    source = {name: path.read_bytes() for name, (path, _) in SOURCES.items()}
    changes = {"check_toy_sessions.py": [
        ("ARGV = ['/opt/homebrew/bin/z3','-in','-smt2']",
         "ARGV = [" + repr(str(SOLVER)) + ",'-in','-smt2']"),
    ]}
    files = {"check_toy_sessions.py": rebind(source["check_toy_sessions.py"],
             OLD_TRANSPORT, changes["check_toy_sessions.py"])}
    transport = files["check_toy_sessions.py"]
    choice = {
        "schema": "962-owner005-runtime-rebind-choice/v1",
        "status": "HELD_SOURCE_ONLY_PENDING_INDEPENDENT_REVIEW",
        "predecessor_source_choice_sha256": OLD_CHOICE,
        "permitted_delta": "Fresh prep/output paths, explicit identical Z3 body route, derived transport hash/size and source-choice digest only.",
        "solver_sha256": SOLVER_SHA,
        "transport_sha256": digest(transport),
        "transport_bytes": len(transport),
        "normal_TERM_KILL_whole_seconds": [40, 48, 56, 60],
        "independent_source_review_complete": False,
        "runtime_execution_authorized": False,
        "engineering_phase_accepted": False,
        "manufacturing_authorized": False,
    }
    files["source-choice.json"] = (json.dumps(choice, indent=2) + "\n").encode()
    common = [
        ("P=E/" + repr(OLD_PREP), "P=E/" + repr(NEW_PREP)),
        ("D=E/" + repr(OLD_OUTPUT), "D=E/" + repr(NEW_OUTPUT)),
    ]
    changes["run_owner_once.py"] = common + [
        ("CHOICE_SHA=" + repr(OLD_CHOICE), "CHOICE_SHA=" + repr(digest(files["source-choice.json"]))),
        ("actual['transport']['sha256']==" + repr(OLD_TRANSPORT),
         "actual['transport']['sha256']==" + repr(digest(transport))),
        ("actual['transport']['bytes']==22291", "actual['transport']['bytes']==" + str(len(transport))),
        ("actual['Z3_body']['path']=='/opt/homebrew/Cellar/z3/5.1.0/bin/z3'",
         "actual['Z3_body']['path']==" + repr(str(SOLVER))),
        ("need('/opt/homebrew/bin/z3' in actual['expected_aliases']",
         "need(" + repr(str(SOLVER)) + " in actual['expected_aliases']"),
        ("actual['expected_aliases']['/opt/homebrew/bin/z3']['resolved']",
         "actual['expected_aliases'][" + repr(str(SOLVER)) + "]['resolved']"),
    ]
    changes["run_fixed_adapter.py"] = common + [
        ("TRANSPORT=E/'head-star-current24-qfnra-toy-transport-prep-003/check_toy_sessions.py'",
         "TRANSPORT=E/" + repr(NEW_PREP + "/check_toy_sessions.py")),
        ("TRANSPORT_SHA=" + repr(OLD_TRANSPORT), "TRANSPORT_SHA=" + repr(digest(transport))),
        ("before['transport']['bytes']==22291", "before['transport']['bytes']==" + str(len(transport))),
        ("module.ARGV==['/opt/homebrew/bin/z3','-in','-smt2']",
         "module.ARGV==[" + repr(str(SOLVER)) + ",'-in','-smt2']"),
    ]
    changes["stopped_exec_wrapper.py"] = [
        ("ADAPTER=" + repr(str(ENGINEERING / OLD_PREP / "run_fixed_adapter.py")),
         "ADAPTER=" + repr(str(ENGINEERING / NEW_PREP / "run_fixed_adapter.py"))),
    ]
    for name in ("run_owner_once.py", "run_fixed_adapter.py", "stopped_exec_wrapper.py"):
        files[name] = rebind(source[name], SOURCES[name][1], changes[name])
    receipt = {
        "schema": "962-owner005-held-source-rebind/v1",
        "status": "HELD_UNRUN_NO_ACTUAL_NO_ADMISSION",
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "future_preparation_directory": str(ENGINEERING / NEW_PREP),
        "future_output_directory": str(ENGINEERING / NEW_OUTPUT),
        "sources": {name: {"path": str(path.relative_to(REPO)), "sha256": sha}
                    for name, (path, sha) in SOURCES.items()},
        "outputs": {name: {"sha256": digest(raw), "bytes": len(raw)} for name, raw in files.items()},
        "literal_replacements": changes,
        "exact_inverse_bytes_verified": True,
        "independent_source_review_complete": False,
        "runtime_execution_authorized": False,
        "engineering_phase_accepted": False,
        "manufacturing_authorized": False,
    }
    files["bindings.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    return files


if __name__ == "__main__":
    if not SOLVER.is_file() or SOLVER.is_symlink() or SOLVER.resolve() != SOLVER:
        raise ValueError("Recovered solver must be a canonical regular file")
    if SOLVER.stat().st_size != 16244496 or digest(SOLVER.read_bytes()) != SOLVER_SHA:
        raise ValueError("Recovered solver differs from accepted body")
    files = render()
    target = ENGINEERING / NEW_PREP
    if ENGINEERING.resolve(strict=True) != ENGINEERING or (ENGINEERING / NEW_OUTPUT).exists():
        raise ValueError("Changed preparation parent or existing future output")
    target.mkdir(mode=0o700)
    for name, raw in files.items():
        with (target / name).open("xb") as stream:
            stream.write(raw)
    print("Prepared held source only; no actual, admission, output or execution.")
