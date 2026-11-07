"""Run a Linux PicoGK assembly with the shared lock and a bounded process group."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time

LOCK = Path(tempfile.gettempdir()) / "picogk-catalog.lock"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@contextmanager
def native_lock(seconds):
    deadline = time.monotonic() + seconds
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("Shared PicoGK lock is held; no stale lock was removed")
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
    identity = os.fstat(fd)
    try:
        os.write(fd, f"{os.getpid()} {time.time()}".encode())
        yield
    finally:
        os.close(fd)
        try:
            current = LOCK.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                LOCK.unlink()
        except FileNotFoundError:
            pass


def run(dotnet, assembly, native, output, seconds=120, inputs=None):
    if platform.system() != "Linux":
        raise ValueError("This wrapper requires native Linux")
    if not math.isfinite(seconds) or not 0 < seconds <= 600:
        raise ValueError("Execution limit must be greater than zero and at most 600 seconds")
    dotnet, assembly, native = (Path(p).resolve(strict=True) for p in (dotnet, assembly, native))
    if not os.access(dotnet, os.X_OK) or not assembly.is_file() or not native.is_file():
        raise ValueError("Executable, assembly and native library must be regular accessible files")
    with native.open("rb") as stream:
        header = stream.read(20)
    machine = {"x86_64": 62, "aarch64": 183}.get(platform.machine())
    if (machine is None or len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
            or int.from_bytes(header[18:20], "little") != machine):
        raise ValueError("Native library must be a host-matching little-endian ELF64 binary")
    output = Path(output).absolute()
    input_hashes = {}
    if inputs is not None:
        inputs = Path(inputs).resolve(strict=True)
        for name in ("solid.json", "coolant.json", "dry-passages.json"):
            path = inputs / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Study input must contain the three explicit regular domain files")
            input_hashes[name] = sha(path)
    output.mkdir(parents=True, exist_ok=False)
    command = [str(dotnet), str(assembly)]
    if inputs is not None:
        command.append(str(inputs))
    command.append(str(output / "native"))
    receipt = {"argv": command, "timeout_seconds": seconds, "shared_native_lock": str(LOCK),
               "runtime_sha256": {str(p): sha(p) for p in (dotnet, assembly, native)},
               "input_sha256": input_hashes, "platform": platform.machine(),
               "exit_code": None, "timed_out": False, "descendants_terminated": False,
               "process_group_absent": False,
               "status": "failed", "manufacturing_authorized": False}
    environment = dict(os.environ)
    environment["LD_LIBRARY_PATH"] = str(native.parent)
    started = time.monotonic()
    try:
        with native_lock(min(seconds, 30)), (output / "native.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            try:
                receipt["exit_code"] = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                receipt["timed_out"] = True
            finally:
                # A successful parent may still leave children; do not release the lock first.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    receipt["descendants_terminated"] = not receipt["timed_out"]
                except ProcessLookupError:
                    pass
                receipt["exit_code"] = process.wait()
                for _ in range(40):
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        receipt["process_group_absent"] = True
                        break
                    time.sleep(0.05)
            if (receipt["exit_code"] == 0 and not receipt["timed_out"]
                    and not receipt["descendants_terminated"] and receipt["process_group_absent"]):
                receipt["status"] = "executed"
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    finally:
        receipt["elapsed_seconds"] = time.monotonic() - started
        (output / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dotnet", type=Path)
    parser.add_argument("assembly", type=Path)
    parser.add_argument("native_library", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--inputs", type=Path,
                        help="Three study-domain inputs; omit for the synthetic qualification assembly")
    args = parser.parse_args()
    result = run(args.dotnet, args.assembly, args.native_library, args.output, args.seconds, args.inputs)
    print(json.dumps(result))
    raise SystemExit(0 if result["status"] == "executed" else 1)
