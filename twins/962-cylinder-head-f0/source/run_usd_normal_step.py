"""One hash-frozen, separately authorised USD step; no transport or workflow."""
import argparse, hashlib, json, math, os
from pathlib import Path
import resource, shutil, signal, subprocess, sys, time

SCRIPTS = {"author": "author_usd_face_normals.py", "check": "author_usd_face_normals.py",
           "preflight": "references/preflight/scripts/preflight.py",
           "minimum": "references/validate-usd-minimum/scripts/run.py",
           "generic": "references/omni-asset-validate/scripts/run.py",
           "geometry": "references/omni-asset-validate-geometry/scripts/run.py",
           "physics": "references/omni-asset-validate-physics/scripts/run.py",
           "profile": "references/simready-validate/scripts/run.py"}
ENV_KEYS = {"PATH", "LANG", "PYTHONDONTWRITEBYTECODE", "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS", "PHYSICAL_AI_PREFLIGHT_MANIFEST",
            "PHYSICAL_AI_REQUIRE_PREFLIGHT", "SIMREADY_FOUNDATION_ROOT",
            "PHYSICAL_AI_SIMREADY_VALIDATE_VENV", "LD_LIBRARY_PATH"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(pins):
    if not pins or any(not Path(p).is_absolute() or sha(p) != value for p, value in pins.items()):
        raise ValueError("Pinned input drift before output creation")


def validate(child_path, expected):
    if sha(child_path) != expected:
        raise ValueError("Child hash mismatch")
    d = json.loads(Path(child_path).read_text())
    if any(d.get(k) is not True for k in ["root_reviewed", "peer_reviewed", "execution_authorized"]):
        raise ValueError("Exact child needs root and peer execution clearance")
    expiry = d["not_after_epoch"]
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or time.time() > expiry:
        raise ValueError("Expired execution child")
    stage, pins = d["stage"], d["pins"]
    if stage not in SCRIPTS or not d["script"].endswith("/" + SCRIPTS[stage]):
        raise ValueError("One supported stage-specific script required")
    required = [str(Path(__file__).resolve()), d["controller_test"], d["interpreter"],
                d["script"], *d["input_paths"], *d["snapshot_paths"]]
    if (any(p not in pins for p in required)
            or not set(required[:2] + [d["script"]]).issubset(d["snapshot_paths"])):
        raise ValueError("All controller/test/runtime/script/inputs need pins")
    verify(pins)
    root, output = Path(d["owned_root"]), Path(d["step_dir"])
    if (not root.is_dir() or output.parent.resolve() != root.resolve()
            or output.exists() or output.is_symlink()):
        raise ValueError("Fresh immediate task-owned step directory required")
    args, env = d["args"], d["environment"]
    if (not isinstance(args, list) or any(not isinstance(v, str) for v in args)
            or any(v.startswith("--fix") for v in args) or set(env) - ENV_KEYS
            or any(not isinstance(v, str) for v in env.values())
            or any(env.get(k) != v for k, v in {"LANG": "C.UTF-8", "OMP_NUM_THREADS": "2",
                   "OPENBLAS_NUM_THREADS": "2", "PYTHONDONTWRITEBYTECODE": "1"}.items())
            or not env.get("PATH") or d.get("property_assignment_intent") != "skip"):
        raise ValueError("Explicit clean environment/arguments and skip intent required")
    if stage in ("author", "check") and (not args or args[0] != stage):
        raise ValueError("Author/check mode mismatch")
    if stage == "preflight":
        if not {"--check-only", "--no-update", "--skip-content-agents", "--skip-deploy",
                "--skip-uv-sync"}.issubset(args):
            raise ValueError("Preflight must be check-only without installs or services")
    elif (env.get("PHYSICAL_AI_REQUIRE_PREFLIGHT") != "1"
          or env.get("PHYSICAL_AI_PREFLIGHT_MANIFEST") not in pins
          or json.loads(Path(env["PHYSICAL_AI_PREFLIGHT_MANIFEST"]).read_text()).get("status") != "ready"):
        raise ValueError("Hash-bound genuine ready preflight required")
    if any(Path(p).suffix not in (".py", ".json") for p in d["snapshot_paths"]):
        raise ValueError("Only declared source/test/JSON snapshots allowed")
    return d


def stop(process):
    errors, killed = [], False
    try:
        os.killpg(process.pid, signal.SIGKILL); killed = True
    except ProcessLookupError:
        pass
    except OSError as exc:
        errors.append(type(exc).__name__)
    try:
        process.wait(timeout=5)
    except BaseException as exc:
        errors.append(type(exc).__name__)
        try:
            process.kill(); process.wait(timeout=5)
        except BaseException as exc:
            errors.append(type(exc).__name__)
    return {"group_SIGKILL_sent": killed, "worker_reaped": process.returncode is not None,
            "cleanup_errors": errors}


def execute(child_path, expected):
    d = validate(child_path, expected)
    output = Path(d["step_dir"]); output.mkdir()
    authoring = d["stage"] in ("author", "check")
    seconds, memory = (90, 6 * 1024**3) if authoring else (120, 4 * 1024**3)
    def limits():
        os.sched_setaffinity(0, {0, 1})
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    def interrupt(signum, frame):
        raise InterruptedError(f"Controller signal {signum}")
    old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    process, error, cleanup = None, None, {"worker_reaped": True, "process_created": False}
    started = time.monotonic()
    try:
        (output / "snapshots").mkdir()
        shutil.copyfile(child_path, output / "frozen-child.json")
        for number, path in enumerate(d["snapshot_paths"]):
            shutil.copyfile(path, output / "snapshots" / f"{number:02d}-{Path(path).name}")
        verify(d["pins"])
        if sha(child_path) != expected:
            raise ValueError("Child drift before process creation")
        for s in old:
            signal.signal(s, interrupt)
        with (output / "native.log").open("xb") as log:
            process = subprocess.Popen([d["interpreter"], "-B", d["script"], *d["args"]],
                cwd=output, env=d["environment"], stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, preexec_fn=limits)
            process.wait(timeout=max(0, seconds - (time.monotonic() - started)))
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        for s in old:
            signal.signal(s, signal.SIG_IGN)
        try:
            if process is not None:
                cleanup = stop(process)
        finally:
            for s, handler in old.items():
                signal.signal(s, handler)
    after = {}
    for path in [*d["pins"], str(child_path)]:
        try:
            after[path] = sha(path)
        except OSError:
            after[path] = None
    child_after = after.pop(str(child_path))
    receipt = {"stage": d["stage"], "child_sha256": expected, "controller_sha256": sha(__file__),
        "native_pid": process.pid if process else None,
        "native_returncode": process.returncode if process else None, "error": error,
        "wall_seconds": time.monotonic() - started, "wall_limit_seconds": seconds,
        "cpu_affinity": [0, 1], "RLIMIT_AS_bytes": memory, "cleanup": cleanup,
        "pins_before": d["pins"], "pins_after": after, "child_sha256_after": child_after,
        "all_pins_unchanged": after == d["pins"] and child_after == expected,
        "artifacts": {str(p.relative_to(output)): {"sha256": sha(p), "bytes": p.stat().st_size}
                      for p in sorted(output.rglob("*")) if p.is_file()},
        "stage_result_assessed": False, "property_assignment_intent": "skip",
        "physical_or_manufacturing_qualification": False}
    with (output / "execution.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write("\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("child", type=Path); parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    result = execute(args.child, args.sha256)
    print(json.dumps(result, allow_nan=False))
    sys.exit(0 if result["native_returncode"] == 0 and result["error"] is None
             and result["all_pins_unchanged"] and result["cleanup"]["worker_reaped"]
             and not result["cleanup"].get("cleanup_errors") else 2)
