"""Bound one native Linux repository check without installing or changing services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--dotnet-root", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o022)
    sdk = subprocess.check_output([str(args.dotnet_root / "dotnet"), "--list-sdks"], text=True)
    if not any(line.startswith("9.") for line in sdk.splitlines()):
        raise SystemExit("Existing .NET 9 SDK required")
    if args.output.exists():
        raise SystemExit("Existing validation output refused")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repository, text=True).strip()
    status_command = ["git", "status", "--porcelain", "--untracked-files=no"]
    if head != args.commit or subprocess.check_output(status_command, cwd=args.repository):
        raise SystemExit("Expected exact commit and clean tracked source")
    if not {2, 3}.issubset(os.sched_getaffinity(0)):
        raise SystemExit("Required CPU affinity is unavailable")
    args.output.mkdir(mode=0o700, parents=True)
    command = ["/usr/bin/taskset", "-c", "2,3", "/usr/bin/make", "check"]
    environment = os.environ.copy()
    environment.update(PATH=str(Path(sys.executable).parent) + ":" + str(args.dotnet_root) + ":/usr/local/bin:/usr/bin:/bin",
                       DOTNET_ROOT=str(args.dotnet_root),
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       PYTHONDONTWRITEBYTECODE="1")
    plan = {"commit": head, "command": command, "python": sys.executable,
            "timeout_seconds": 900, "address_space_limit_bytes": 6 * 1024 ** 3,
            "cpu_affinity": [2, 3], "source_sha256": sha(__file__),
            "test_process_umask": "022", "output_directory_mode": "0700", "dotnet_sdks": sdk.splitlines(),
            "dotnet_executable_sha256": sha(args.dotnet_root / "dotnet"),
            "started_utc": datetime.now(timezone.utc).isoformat()}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")

    def restrict():
        resource.setrlimit(resource.RLIMIT_AS, (6 * 1024 ** 3, 6 * 1024 ** 3))

    start = time.monotonic()
    timed_out = False
    with (args.output / "make-check.log").open("xb") as stream:
        process = subprocess.Popen(command, cwd=args.repository, env=environment,
                                   stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=restrict)
        (args.output / "pid.json").write_text(json.dumps({"pid": process.pid}) + "\n")
        try:
            code = process.wait(timeout=900)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait(timeout=10)
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    state = subprocess.check_output(status_command, cwd=args.repository, text=True)
    (args.output / "tracked-state.txt").write_text(state)
    result = {"commit": head, "exit_code": code, "timed_out": timed_out,
              "elapsed_seconds": time.monotonic() - start,
              "peak_child_rss_kib": usage.ru_maxrss, "tracked_source_unchanged": not state,
              "log_sha256": sha(args.output / "make-check.log"),
              "finished_utc": datetime.now(timezone.utc).isoformat(),
              "physical_acceptance": False, "manufacturing_authorized": False}
    (args.output / "execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    raise SystemExit(0 if code == 0 and not timed_out and not state else 1)


if __name__ == "__main__":
    main()
