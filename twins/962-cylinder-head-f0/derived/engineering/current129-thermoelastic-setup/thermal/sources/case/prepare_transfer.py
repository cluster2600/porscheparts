"""Held fixed-coupon data preparation only; no solver or native module imports."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

PREP = Path(__file__).resolve().parent
ROOT = PREP.parent.parent.parent
SOURCE = ROOT / "work/962-engineering/cp1-assumed-thermal-birth-linear-001"
OUTPUT = ROOT / "work/962-engineering/cp1-oneway-thermoelastic-transfer-inputs-001"
DT = 0.0025
STEPS = 160
BIRTH_STEP = 80
HISTORY_TOL_K = 1e-10
AXES = (tuple(i / 8 for i in range(17)), tuple(i / 4 for i in range(5)),
        tuple(i / 4 for i in range(5)))
SUPPORTS = ((0, (0., 0., 0.), (0, 1, 2)),
            (32, (1., 0., 0.), (1, 2)), (137, (0., 1., 0.), (2,)))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_files():
    return [(0, "end", "thermal_end_0000.csv")] + [
        (step, phase, f"thermal_{phase}_{step:04d}.csv")
        for step in range(1, STEPS + 1) for phase in ("begin", "end")]


def parse_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    need(reader.fieldnames == ["id", "temperature", "x", "y", "z"], "Exact source CSV columns required")
    rows = {}
    last = -1
    for row in reader:
        need(set(row) == set(reader.fieldnames) and all(isinstance(v, str) and v for v in row.values()),
             "Complete source row required")
        need(row["id"].isascii() and row["id"].isdigit(), "Canonical nonnegative source ID required")
        tag = int(row["id"])
        need(str(tag) == row["id"] and tag > last, "Strict original source ID ordering required")
        values = tuple(float(row[k]) for k in ("temperature", "x", "y", "z"))
        need(all(math.isfinite(v) for v in values), "Finite source words required")
        need(all(not any(c.isspace() for c in row[k]) for k in ("temperature", "x", "y", "z")),
             "One numeric token per value required")
        rows[tag] = {"position": values[1:], "temperature": values[0], "token": row["temperature"]}
        last = tag
    need(rows, "Nonempty source sample required")
    return rows


def join_rows(rows, geometry, expected_ids):
    need(set(rows) == set(expected_ids), "Complete active source ID set required")
    for tag, row in rows.items():
        need(tuple(v.hex() for v in row["position"]) == tuple(v.hex() for v in geometry[tag]),
             "Source ID/coordinate binary64 association changed")


def phase_join(step, begin, previous_end, old_ids, new_ids):
    need(set(begin) == (set(old_ids) if step < BIRTH_STEP else set(old_ids) | set(new_ids)),
         "Begin-phase active membership changed")
    errors = [abs(begin[tag]["temperature"] - row["temperature"])
              for tag, row in previous_end.items()]
    need(max(errors, default=0.) <= HISTORY_TOL_K, "Begin does not preserve previous END")
    if step == BIRTH_STEP:
        need(all(begin[tag]["temperature"] == 350. for tag in new_ids), "New born nodes must use accepted BEGIN80")
    return max(errors, default=0.)


def table_text(axes, values):
    need(len(axes) in (3, 4), "Only the fixed 3D/4D transfer tables exist")
    need([name for name, _ in axes] == (["X", "Y", "Z"] if len(axes) == 3 else ["X", "Y", "Z", "T"]),
         "X-fastest XYZ[T] axis order required")
    count = 1
    lines = []
    for name, axis in axes:
        need(axis and all(math.isfinite(v) for v in axis)
             and all(a < b for a, b in zip(axis, axis[1:])), "Strict finite independent axes required")
        count *= len(axis)
        lines += ["AXIS " + name, " ".join(format(v, ".17g") for v in axis)]
    need(len(values) == count and all(math.isfinite(float(v)) for v in values), "Complete finite grid product required")
    return "\n".join(lines + ["DATA"] + list(values)) + "\n"


def spatial_tokens(rows, by_position, xs):
    # MOOSE first axis varies fastest: x + y*Nx + z*Nx*Ny [+ time*Nx*Ny*Nz].
    return [rows[by_position[(x, y, z)]]["token"] for z in AXES[2] for y in AXES[1] for x in xs]


def assemble(samples):
    need(list(samples) == [(s, p) for s, p, _ in expected_files()], "Exact321 step/phase order required")
    final = samples[(STEPS, "end")]
    geometry = {tag: row["position"] for tag, row in final.items()}
    grid = {(x, y, z) for x in AXES[0] for y in AXES[1] for z in AXES[2]}
    need(len(geometry) == 425 and set(geometry.values()) == grid, "Exact425-node SI grid required")
    by_position = {position: tag for tag, position in geometry.items()}
    old = {tag for tag, p in geometry.items() if p[0] <= 1.}
    born = {tag for tag, p in geometry.items() if p[0] >= 1.}
    shared = old & born
    new = born - old
    need((len(old), len(born), len(shared), len(new)) == (225, 225, 25, 200), "Fixed birth partition required")
    for tag, position, _ in SUPPORTS:
        need(geometry.get(tag) == position and tag in old, "Accepted source support ID changed")
    initial = samples[(0, "end")]
    join_rows(initial, geometry, old)
    need(all(r["temperature"] == 400. for r in initial.values()), "Old material starts at400K")
    previous = initial
    maximum = 0.
    for step in range(1, STEPS + 1):
        begin, end = samples[(step, "begin")], samples[(step, "end")]
        active = old if step < BIRTH_STEP else set(geometry)
        join_rows(begin, geometry, active)
        join_rows(end, geometry, active)
        maximum = max(maximum, phase_join(step, begin, previous, old, new))
        previous = end
    old_x, born_x = AXES[0][:9], AXES[0][8:]
    old_values = [v for step in range(STEPS + 1)
                  for v in spatial_tokens(samples[(step, "end")], by_position, old_x)]
    born_values = [v for step in range(BIRTH_STEP, STEPS + 1)
                   for v in spatial_tokens(samples[(step, "end")], by_position, born_x)]
    birth_values = spatial_tokens(samples[(BIRTH_STEP, "begin")], by_position, born_x)
    tables = {
        "old-end.grid": table_text((("X", old_x), ("Y", AXES[1]), ("Z", AXES[2]),
                                    ("T", tuple(i / 400 for i in range(161)))), old_values),
        "born-end.grid": table_text((("X", born_x), ("Y", AXES[1]), ("Z", AXES[2]),
                                     ("T", tuple(i / 400 for i in range(80, 161)))), born_values),
        "born-begin80.grid": table_text((("X", born_x), ("Y", AXES[1]), ("Z", AXES[2])), birth_values)}
    mapping = [{"source_node_id": tag, "coordinates_m": list(p), "binary64_hex": [v.hex() for v in p],
                "old2": tag in old, "born3": tag in born, "shared": tag in shared}
               for tag, p in sorted(geometry.items())]
    return tables, {"node_rows": mapping, "old_node_count": 225, "born_reference_DOF_count": 225,
                    "shared_node_count": 25, "genuinely_new_node_count": 200,
                    "maximum_previous_END_to_BEGIN_error_K": maximum,
                    "table_value_counts": dict(zip(tables, (36225, 18225, 225))),
                    "native_connectivity_or_ID_bijection_proven": False}


def checked_pins(pins):
    for name, digest in pins.items():
        path = Path(name)
        need(not path.is_absolute() and ".." not in path.parts, "Relative source input required")
        path = ROOT / path
        need(path.is_file() and not path.is_symlink() and sha(path) == digest, "Frozen source input changed")


def prepare(contract, expected):
    contract = Path(contract)
    need(contract.is_file() and not contract.is_symlink() and contract.resolve() == contract
         and sha(contract) == expected, "Exact external data-preparation actual required")
    c = json.loads(contract.read_text())
    need(c.get("schema") == "962-oneway-thermoelastic-data-preparation-actual/v1"
         and c.get("root_and_peer_review_complete") is True and c.get("data_preparation_authorized") is True
         and all(c.get(k) is False for k in ("native_execution_authorized", "head_execution_authorized",
                                            "engineering_accepted", "physics_qualified", "material_qualified",
                                            "process_calibrated", "manufacturing_authorized", "automatic_retry")),
         "Data-only reviewed authority required")
    held = json.loads((PREP / "held-preparation.json").read_text())
    pins = c["input_sha256"]
    need(pins.get(str((PREP / "held-preparation.json").relative_to(ROOT))) == sha(PREP / "held-preparation.json")
         and all(pins.get(k) == v for k, v in held["input_sha256"].items()), "Held inputs must be directly bound")
    checked_pins(pins)
    index = json.loads((PREP / "thermal-input-index.json").read_text())
    receipt = json.loads((SOURCE / "native-execution.json").read_text())
    need(receipt.get("native_execution_completed") is True and receipt.get("inputs_unchanged") is True
         and receipt.get("binary_and_runtime_unchanged") is True and receipt.get("returncode") == 0,
         "Accepted thermal source must remain completed")
    need(index["selected"] == [{"step": s, "phase": p, "filename": n,
                               "sha256": receipt["artifact_sha256"][n]} for s, p, n in expected_files()],
         "Exact321 source artifact associations required")
    need(OUTPUT.parent.is_dir() and not OUTPUT.exists() and not OUTPUT.is_symlink()
         and OUTPUT.resolve() == OUTPUT and c.get("output") == str(OUTPUT), "Fresh fixed raw output required")
    samples = {}
    for item in index["selected"]:
        path = SOURCE / item["filename"]
        need(path.is_file() and not path.is_symlink() and sha(path) == item["sha256"], "Thermal CSV drift")
        samples[(item["step"], item["phase"])] = parse_rows(path.read_text())
    tables, association = assemble(samples)
    checked_pins(pins)
    need(sha(contract) == expected and all(sha(SOURCE / i["filename"]) == i["sha256"]
                                         for i in index["selected"]), "Input drift during preparation")
    OUTPUT.mkdir()
    for name, text in tables.items():
        with (OUTPUT / name).open("x") as stream:
            stream.write(text)
    manifest = {"schema": "962-oneway-thermoelastic-prepared-transfer/v1", "source_receipt_sha256": sha(SOURCE / "native-execution.json"),
                "data_actual_sha256": expected, "selected321": index["selected"], **association,
                "table_sha256": {name: sha(OUTPUT / name) for name in tables},
                "same_native_geometry_association_still_required": True,
                "birth_reference_phase": "BEGIN80_all225_born_DOFs_including25shared",
                "history": "Current selected shared u/T restored; affected old/older vectors intentionally rebased",
                "source_off_cooling_history_present": False,
                "native_execution_authorized": False, "engineering_accepted": False,
                "physics_qualified": False, "material_qualified": False, "process_calibrated": False,
                "manufacturing_authorized": False}
    with (OUTPUT / "transfer-manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("contract_sha256")
    args = parser.parse_args()
    prepare(args.contract, args.contract_sha256)
