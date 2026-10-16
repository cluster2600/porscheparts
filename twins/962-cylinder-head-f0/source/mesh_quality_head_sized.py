"""Admission-guarded raw HXT head with one explicit feature-derived size cap.

The cube proves insertion control only: its capped SICN fails the head gate.
This entrypoint preserves the frozen seed/core audits and resource stops.
Source preparation is not authorization to launch a native head case.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

WRAPPER_PATH = Path(__file__).resolve()
ROOT = WRAPPER_PATH.parents[3]
SEED_PATH = WRAPPER_PATH.with_name("mesh_quality_head_seed.py")
SEED_SHA256 = "e3576d5847922e950e21cf0d003a6869262fae21df6d6715d3b6bac3e2d01ad2"
FIXTURE_RESULT = "work/962-engineering/hxt-size-cap-fixture-001/receipt.json"
FIXTURE_HASHES = {
    FIXTURE_RESULT: "b6a86b49044636685365708cce66c7d8d4b43c4d296e26918b285866310675d7",
    "work/962-engineering/hxt-size-cap-fixture-001/contract.json": "af201485b13f8f548854a5bd42777b1d3d3a7903988c31b254fc1cf3dad1ec27",
    "work/962-engineering/hxt-size-cap-fixture-001/uncapped/worker-report.json": "fd884b116d6e8d492d2724431996e68c65a925d78b1b3972a68f1118abfd9e97",
    "work/962-engineering/hxt-size-cap-fixture-001/capped-1p75/worker-report.json": "9bf0ad68350f10682965bc43e83860afadf0a435fae5d795cd97322e568dbaf3",
    "work/962-engineering/hxt-size-cap-fixture-001/uncapped/cube.msh": "1d7e2a5139c2ed0b2c85233f4a1d45fe9daebb4ed0f2782c561cb582a3e185e6",
    "work/962-engineering/hxt-size-cap-fixture-001/capped-1p75/cube.msh": "e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1"}
SIZING = {"Mesh.MeshSizeMax": 1.75, "Mesh.MeshSizeMin": 0, "Mesh.MeshSizeFactor": 1}


def require_frozen_seed():
    if hashlib.sha256(SEED_PATH.read_bytes()).hexdigest() != SEED_SHA256:
        raise ValueError("Exact reviewed frozen raw-seed companion required")


def require_fixture():
    for name, expected in FIXTURE_HASHES.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Bound software size-cap fixture evidence changed")
    result = json.loads((ROOT/FIXTURE_RESULT).read_text())
    if result.get("software_fixture_passed") is not True or result.get("head_accepted") is not False:
        raise ValueError("Software-only insertion control evidence required")
    return dict(input_sha256s=FIXTURE_HASHES, insertion_control_demonstrated=True,
        capped_cube_minimum_SICN=0.027175498119979526, capped_cube_passes_head_SICN_gate=False,
        head_resolution_or_quality_established=False)


def configure_core():
    require_frozen_seed(); require_fixture()
    spec = importlib.util.spec_from_file_location("_962_frozen_sized_seed", SEED_PATH)
    seed = importlib.util.module_from_spec(spec); spec.loader.exec_module(seed)
    core = seed.configure_core()
    sources = tuple(core.source_files()); original_save = core.save
    def save_sized_report(path, report):
        report["sized_companion"] = dict(
            wrapper_source_sha256=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest(),
            frozen_seed_sha256=SEED_SHA256, sizing_options=SIZING,
            sizing_basis="Coarse hypothesis: nominal assumed 3.5 mm BCC beam diameter / 2; no feature-resolution proof",
            fixture=require_fixture(), observed_previous_head_RSS_bytes=6416138240,
            observed_margin_below_sampled_RSS_stop_bytes=2173796352,
            sampled_RSS_is_not_a_hard_peak_limit=True,
            cap_may_exceed_existing_resource_stop=True, automatic_retry=False,
            head_thermal_resolution_established=False, actual_minimum_SICN_gate_unchanged=0.1)
        original_save(path, report)
    # The unchanged controller derives its worker command from this isolated
    # module's __file__; both processes must re-enter the sized companion.
    core.__file__ = str(WRAPPER_PATH)
    core.source_files = lambda: [WRAPPER_PATH, *sources]
    core.OUTPUT = core.ROOT / "work/962-engineering/quality-volume-hxt-sized-001"
    core.OPTIONS = {**core.OPTIONS, **SIZING}
    core.save = save_sized_report
    return core


def main(argv=None):
    require_frozen_seed(); require_fixture()
    core = configure_core()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return core.worker(args) if args.worker else core.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
