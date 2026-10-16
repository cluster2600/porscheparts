"""Single tiny known-reader launch; frozen core cleanup, no dispatch modes."""
import argparse, hashlib, importlib.util, json, math, os, resource, shutil
import signal, subprocess, sys, time
from pathlib import Path

CORE_SHA = "178cb068556daa39c5e997cf9a5ea0ec32855bf0f4ff89ba1da1db5c79d2454c"
READER_SHA = "c99226ea0323965691f80595c39d8411dfd19b0cac69c57ccd03cdd25d604114"
SOURCE_SHA = "146cf436b5f42f2d53faae169e0aaedfbd8872b45af08501fb29b8785c73c55e"
EXPECTED_SHA = "af7a013f56b9b3bb6dc07a74f12e5ccd0e101d6d269211c3efe5255c47fe6d21"


def execute(child_path, expected_child):
    if hashlib.sha256(Path(child_path).read_bytes()).hexdigest() != expected_child:
        raise ValueError("Exact one-off child hash mismatch")
    d = json.loads(Path(child_path).read_text())
    if (any(d.get(k) is not True for k in ["root_reviewed", "peer_reviewed", "execution_authorized"])
            or type(d["not_after_epoch"]) not in (int, float)
            or not math.isfinite(d["not_after_epoch"]) or time.time() > d["not_after_epoch"]):
        raise ValueError("Current root and peer one-off authority required")
    if hashlib.sha256(Path(d["core"]).read_bytes()).hexdigest() != CORE_SHA:
        raise ValueError("Frozen cleanup core changed")
    spec = importlib.util.spec_from_file_location("known_reader_frozen_core", d["core"])
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    pins = d["pins"]; core.verify(pins)
    required = [str(Path(__file__).resolve()), d["test"], d["core"], d["reader"],
                d["interpreter"], d["source"], d["derivative"], d["expected"]]
    if (any(p not in pins for p in required) or pins[d["reader"]] != READER_SHA
            or pins[d["source"]] != SOURCE_SHA or pins[d["expected"]] != EXPECTED_SHA
            or d["property_assignment_intent"] != "skip"):
        raise ValueError("Exact source/runtime/reader/test and three input pins required")
    output = Path(d["step_dir"]); root = Path(d["owned_root"])
    if (not root.is_dir() or output.parent.resolve() != root.resolve()
            or output.exists() or output.is_symlink()):
        raise ValueError("Fresh owned one-off output required")
    env = d["environment"]
    if (set(env) - core.ENV_KEYS or any(not isinstance(v, str) for v in env.values())
            or any(env.get(k) != v for k, v in {"LANG": "C.UTF-8", "OMP_NUM_THREADS": "2",
                "OPENBLAS_NUM_THREADS": "2", "PYTHONDONTWRITEBYTECODE": "1"}.items())
            or not env.get("PATH")):
        raise ValueError("Explicit clean reader environment required")
    argv = [d["interpreter"], "-B", d["reader"], d["source"], d["derivative"],
            d["expected"], str(output / "readback-report.json"), "--source-sha256", SOURCE_SHA,
            "--derivative-sha256", pins[d["derivative"]], "--expected-sha256", EXPECTED_SHA]
    if d["argv"] != argv:
        raise ValueError("Only the exact known-reader argv is allowed")
    output.mkdir()
    def limits():
        os.sched_setaffinity(0, {0, 1})
        resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))
    def interrupt(signum, frame):
        raise InterruptedError(f"Reader launcher signal {signum}")
    old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    process, error, cleanup = None, None, {"worker_reaped": True, "process_created": False}
    started = time.monotonic()
    try:
        shutil.copyfile(child_path, output / "frozen-child.json")
        for number, path in enumerate(required[:4] + [d["source"], d["expected"]]):
            shutil.copyfile(path, output / f"{number:02d}-{Path(path).name}")
        core.verify(pins)
        if core.sha(child_path) != expected_child:
            raise ValueError("Child drift before process creation")
        for s in old:
            signal.signal(s, interrupt)
        with (output / "native.log").open("xb") as log:
            process = subprocess.Popen(argv, cwd=output, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=limits)
            process.wait(timeout=max(0, 35 - (time.monotonic() - started)))
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        for s in old:
            signal.signal(s, signal.SIG_IGN)
        try:
            if process is not None:
                cleanup = core.stop(process)
        finally:
            for s, handler in old.items():
                signal.signal(s, handler)
    after = {}
    for path in [*pins, str(child_path)]:
        try:
            after[path] = core.sha(path)
        except OSError:
            after[path] = None
    child_after = after.pop(str(child_path))
    result = {"child_sha256": expected_child, "child_sha256_after": child_after,
        "launcher_sha256": core.sha(__file__), "core_sha256": CORE_SHA,
        "native_pid": process.pid if process else None,
        "native_returncode": process.returncode if process else None, "error": error,
        "wall_seconds": time.monotonic() - started, "outer_wall_limit_seconds": 35,
        "cpu_affinity": [0, 1], "RLIMIT_AS_bytes": 4294967296, "cleanup": cleanup,
        "pins_before": pins, "pins_after": after,
        "all_pins_unchanged": after == pins and child_after == expected_child,
        "artifacts": {p.name: {"sha256": core.sha(p), "bytes": p.stat().st_size}
                      for p in sorted(output.iterdir()) if p.is_file()},
        "known_array_result_assessed": False, "head_or_physical_qualification": False}
    with (output / "execution.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("child", type=Path); parser.add_argument("--sha256", required=True)
    args = parser.parse_args(); result = execute(args.child, args.sha256)
    print(json.dumps(result, allow_nan=False))
    sys.exit(0 if result["native_returncode"] == 0 and result["error"] is None
        and result["all_pins_unchanged"] and result["cleanup"]["worker_reaped"]
        and not result["cleanup"].get("cleanup_errors") else 2)
