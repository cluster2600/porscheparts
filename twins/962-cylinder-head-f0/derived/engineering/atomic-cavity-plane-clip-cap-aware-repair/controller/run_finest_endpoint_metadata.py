"""Fixture-only optional-field companion; preserve the frozen execution core."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve()
BASE = HERE.with_name("run_finest_endpoint_preflight.py")
BASE_SHA = "b214e1cece8dbf66be6071199cbdf1a8e22a2a59328888011de17492f923c86b"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
    raise ValueError("Frozen cleanup core changed before import")
SPEC = importlib.util.spec_from_file_location("frozen_finest_optional_metadata_core", BASE)
CORE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(CORE)
OLD = '{{json .HostConfig.Tmpfs}}'
NEW = '{{json (index .HostConfig "Tmpfs")}}'
ORIGINAL_FORMAT = CORE.INSPECT
if ORIGINAL_FORMAT.count(OLD) != 1:
    raise ValueError("Exact original optional-field access required")
CORRECTED_FORMAT = ORIGINAL_FORMAT.replace(OLD, NEW)
TEST = "tests/test_962_finest_endpoint_metadata.py"
REFUSAL = "work/962-engineering/finest-surface-endpoint-fixtures-001/common-neighbor-source001.execution.json"
CLEANUP = "work/962-engineering/finest-surface-endpoint-fixture-launch-001/root-setup-cleanup.json"


def companion_binding():
    pins = {str(HERE.relative_to(ROOT)): CORE.digest(HERE), TEST: CORE.digest(ROOT/TEST),
            REFUSAL: "2e1778acd9f2c3dbcdc6290dc5ed0b05c232f9738877f7e03cc0965e49355e52",
            CLEANUP: "45728ad4d49a4e732a45bfb689d42e2de0a755d34f5ec469d64e97647907cfa6"}
    return dict(base_controller_sha256=BASE_SHA, substitution=dict(old=OLD, new=NEW), input_sha256=pins,
                provenance="The exact frozen core source remains the recorded controller; this separately hash-bound wrapper changes only the optional Tmpfs lookup at runtime. Core cleanup, limits, source guards and compiled binaries remain unchanged.")


def observed(pins):
    result = {}
    for name in pins:
        path = ROOT/name
        try:
            result[name] = CORE.digest(path) if path.is_file() and not path.is_symlink() else None
        except OSError:
            result[name] = None
    return result


def run(path, expected, output):
    if CORE.digest(path) != expected:
        raise ValueError("Exact separate metadata child required")
    child = json.loads(path.read_text()); binding = companion_binding()
    if (child.get("phase") != "fixtures" or child.get("root_authorized") is not True
            or child.get("metadata_companion") != binding):
        raise ValueError("Separately authorized fixture-only metadata child required")
    if output.exists() or output.is_symlink():
        raise ValueError("Existing fixture output preserved before invoking the core")
    before = observed(binding["input_sha256"])
    if before != binding["input_sha256"] or CORE.INSPECT != ORIGINAL_FORMAT:
        raise ValueError("Metadata companion/source/refusal evidence drift before output")
    error = None; failure = None; code = None
    CORE.INSPECT = CORRECTED_FORMAT
    try:
        code = CORE.run(path, expected, output)
    except BaseException as exc:
        failure = exc; error = type(exc).__name__+": "+str(exc)
    finally:
        CORE.INSPECT = ORIGINAL_FORMAT
        after = observed(binding["input_sha256"])
        unchanged = after == binding["input_sha256"] and CORE.digest(path) == expected
        frozen = output/"frozen-execution-contract.json"; executed = output/"controller-executed.py"
        if (frozen.is_file() and executed.is_file() and CORE.digest(frozen) == expected
                and CORE.digest(executed) == BASE_SHA):
            with (output/"metadata-companion-executed.py").open("xb") as stream:
                stream.write(HERE.read_bytes())
            summary = output/"phase-summary.json"
            CORE.save(output/"metadata-companion-receipt.json", dict(
                schema="962-finest-optional-metadata-companion/v1", execution_contract_sha256=expected,
                metadata_companion=binding, actual_before_sha256=before, actual_after_sha256=after,
                all_additional_inputs_unchanged=unchanged, core_returncode=code, error=error,
                original_format_sha256=hashlib.sha256(ORIGINAL_FORMAT.encode()).hexdigest(),
                corrected_format_sha256=hashlib.sha256(CORRECTED_FORMAT.encode()).hexdigest(),
                companion_snapshot_sha256=CORE.digest(output/"metadata-companion-executed.py"),
                core_phase_summary_sha256=CORE.digest(summary) if summary.is_file() else None,
                source_attribution="core.controller_sha256 denotes the preserved base bytes; this receipt binds the actual one-field metadata companion. Freeze both receipts for any later use.",
                compiled_binaries_replaced=False, head_trial_authorized=False, solver_admission_established=False))
    if failure is not None:
        raise failure
    return code if unchanged else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def interrupt(signum, _frame):
        raise InterruptedError("Controller signal "+str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(run(args.contract.resolve(), args.contract_sha256, args.output))
