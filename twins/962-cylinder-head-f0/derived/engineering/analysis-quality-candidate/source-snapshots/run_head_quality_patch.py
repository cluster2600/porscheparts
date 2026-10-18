"""One reviewed original-source quality pass; retain failures and never retry."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
FAMILY = ROOT/"twins/962-cylinder-head-f0"
CONTRACT = FAMILY/"engineering/analysis-quality-head-contract.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output):
    contract = json.loads(CONTRACT.read_text())
    if output.exists() or output.is_symlink():
        raise ValueError("Fresh quality output required; no retry or overwrite")
    verify = lambda: all(digest(ROOT/p) == h for p, h in contract["input_hashes"].items())
    if not verify() or not contract["root_authorised_single_head_pass"]:
        raise ValueError("Reviewed source, binary, identity or fixture binding changed")
    if contract["resources"] != dict(cpus=2, memory_bytes=4294967296,
                                    memory_swap_bytes=4294967296, swap_bytes=0,
                                    hard_wall_seconds=300, network="none"):
        raise ValueError("Predeclared resource cap changed")
    output.mkdir(parents=True)
    (output/"frozen-execution-contract.json").write_bytes(CONTRACT.read_bytes())
    (output/"source-executed.py").write_bytes(Path(__file__).read_bytes())
    source = ROOT/contract["original_indexed_input"]
    binary = ROOT/contract["native_binary"]
    name = "962-original-quality-head-001"
    command = ["docker", "run", "--name", name, "--network", "none", "--read-only",
               "--cpus", "2", "--memory", "4294967296", "--memory-swap", "4294967296",
               "--mount", f"type=bind,src={binary},dst=/quality-patch,readonly",
               "--mount", f"type=bind,src={source},dst=/original.bin,readonly",
               "--mount", f"type=bind,src={output.resolve()},dst=/out",
               "--entrypoint", "/quality-patch", contract["toolchain_image_id"],
               "/original.bin", "/out/native"]
    record = dict(status="single_quality_pass_running", command=command,
                  contract_sha256=digest(CONTRACT), input_sha256=digest(source),
                  binary_sha256=digest(binary), head_solver_executed=False,
                  engineering_accepted=False, manufacturing_authorized=False)
    (output/"running-receipt.json").write_text(json.dumps(record, indent=2)+"\n")
    started = time.monotonic()
    with (output/"native.log").open("x") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        deadline = False
        try:
            process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            deadline = True
            subprocess.run(["docker", "kill", name], capture_output=True, timeout=10)
            process.wait(timeout=10)
    state = subprocess.run(["docker", "inspect", name, "--format", "{{json .State}}"],
                           capture_output=True, text=True, timeout=10)
    record.update(status="single_quality_pass_finished_all_independent_gates_pending",
                  native_returncode=process.returncode, deadline_exceeded=deadline,
                  wall_seconds=time.monotonic()-started,
                  container_state=json.loads(state.stdout) if state.returncode == 0 else state.stderr,
                  all_bound_inputs_unchanged=verify(),
                  output_sha256={str(p.relative_to(output)): digest(p)
                                 for p in (output/"native").glob("*") if p.is_file()},
                  native_log_sha256=digest(output/"native.log"))
    with (output/"execution-receipt.json").open("x") as stream:
        json.dump(record, stream, indent=2); stream.write("\n")
    # Remove only this stopped, task-owned container after preserving its state.
    if isinstance(record["container_state"], dict) and not record["container_state"].get("Running", True):
        cleaned = subprocess.run(["docker", "rm", name], capture_output=True, text=True, timeout=10)
        with (output/"owned-container-cleanup.json").open("x") as stream:
            json.dump(dict(returncode=cleaned.returncode, stdout=cleaned.stdout, stderr=cleaned.stderr), stream, indent=2)
    print(json.dumps(record, indent=2))
    return 0 if process.returncode in (0, 3) and record["all_bound_inputs_unchanged"] and not deadline else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
