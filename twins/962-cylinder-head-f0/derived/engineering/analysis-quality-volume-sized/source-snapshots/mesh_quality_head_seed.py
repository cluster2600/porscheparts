"""Save one unoptimized HXT seed through the unchanged, hash-pinned quality worker.

The frozen companion remains the implementation of admission, resource controls,
mesh audits and the actual minimum SICN >= 0.1 acceptance gate. This entrypoint
changes only the fresh output and Mesh.Optimize, and makes its ledger truthful.
Preparing this source does not authorize a native head run.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve()
CORE_PATH = WRAPPER_PATH.with_name("mesh_quality_head.py")
CORE_SHA256 = "6ba68df17ae41a55e98470c103c804c830b890256b936d3785ea8cc40cb55302"


def require_frozen_core():
    if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA256:
        raise ValueError("The exact reviewed frozen quality-volume companion is required")


def configure_core():
    require_frozen_core()
    # Do not register or modify an ordinary imported mesh_quality_head module.
    spec = importlib.util.spec_from_file_location("_962_frozen_seed_core", CORE_PATH)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    original_sources = tuple(core.source_files())
    if len(original_sources) != 5 or original_sources[0] != CORE_PATH:
        raise ValueError("Original frozen-core source bindings required before entrypoint redirection")
    original_save = core.save
    def save_seed_report(path, report):
        if report.get("stage") == "generating_and_standard_optimizing_HXT":
            report["stage"] = "generating_HXT_without_standard_optimization"
        report["seed_companion"] = dict(
            frozen_core_sha256=CORE_SHA256,
            wrapper_source_sha256=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest(),
            standard_optimization_enabled=False,
            actual_minimum_SICN_gate_unchanged=0.1,
            raw_mesh_export_does_not_establish_acceptance=True)
        original_save(path, report)
    # The frozen controller constructs its worker command from module __file__.
    # Both processes must re-enter this wrapper; source_files still binds the
    # original implementation and all four imports, as well as this entrypoint.
    core.__file__ = str(WRAPPER_PATH)
    core.source_files = lambda: [WRAPPER_PATH, *original_sources]
    core.OUTPUT = core.ROOT / "work/962-engineering/quality-volume-hxt-seed-001"
    core.OPTIONS = {**core.OPTIONS, "Mesh.Optimize": 0}
    core.save = save_seed_report
    return core


def main(argv=None):
    require_frozen_core()
    implementation = configure_core()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return implementation.worker(args) if args.worker else implementation.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
