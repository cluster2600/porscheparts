#!/usr/bin/env python3
"""Layer-by-layer build screen of the print body in CalculiX.

Why CalculiX and not Adamantine. The Adamantine build of this repository only
integrates explicitly (forward Euler, RK3, RK4). On 4 mm cells its stable step
is about 0.02 s, and the build lasts some 150,000 s, so a real build time is
out of reach. CalculiX integrates heat transfer implicitly, activates elements
with *MODEL CHANGE and has temperature-dependent plasticity; the carrier's
print simulation (parts/993-eng-carrier-0001/source/bionic-20261011) already
uses its element activation.

What is modelled (every number is in params/build-sim-case.json):

  body      voxel hexahedra of the print-body occupancy, built along -y
            (flange y+ on the plate: the build the layer screen sliced);
  supports  columns of homogenised hexahedra under every voxel that has no
            solid voxel in the 3 x 3 cells below it (the 45 degree rule on a
            voxel grid), plus columns under any group of voxels that would
            otherwise hang free at some stage of the build. A level with
            "supports": "designed" takes instead the envelope laid out by
            support_design.py, at the melted share of its block supports;
  plate     a slab under the part, its lower face held at the plate
            temperature and kept plane;
  lumps     the real layers are grouped in lumps of a few cell rows; a lump
            is activated at once. A level may declare its own process
            value (the number of lasers);

  thermal   transient heat transfer. A lump arrives at the plate temperature
            and receives the absorbed laser energy of its real layers as a
            uniform body flux over the real time those layers take (exposure
            plus recoating). Powder and gas are adiabatic: all heat leaves
            through the plate. The result is the time-averaged temperature of
            the part during the build, not a melt pool and not a peak.
  mechanics static, small strain, perfect plasticity with temperature-
            dependent yield. A lump is born strain free at the declared
            stress-free temperature and cools to the temperature the thermal
            run gives for the end of its lump. After the last lump everything
            cools to room temperature; then plate and supports are removed.

Three software witnesses run first (`witness`): element activation in a
transient heat step against a closed-form mixing temperature, a body flux
against its energy, and a strain-free birth followed by cooling of a bar held
at both ends, elastic and perfectly plastic.

Found on the way (2026-11-12, ccx 2.21): a node that belongs only to elements
not yet active does not keep its initial condition. It holds 0 until a
*TEMPERATURE card names it, and then the value last prescribed. A strain-free
birth takes that value as its reference: with nothing prescribed the new
material came out in compression when it cooled. The birth step must
prescribe the temperature of the new nodes.

Sub-commands (CASE_DIR must be under /home; ccx runs in the cadsim image):

  witness  STUDY_DIR OUT.json
  prepare  OCC_DIR CASE.json LEVEL RUN_DIR [SUPPORT_DIR]   mesh, supports, plate, lumps
  thermal  RUN_DIR                              deck, run, read, energy audit
  mechanics RUN_DIR [--variant NAME] [--relax K]   deck, run, read
  summarize STUDY_DIR CASE.json WITNESS.json OUT.json

This is a screen under declared hypotheses. It qualifies no process, support
scheme, orientation, material or part.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

IMAGE = "3dprinting993-cadsim:dev"
HEX = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
K0 = 273.15


# --------------------------------------------------------------------------
# small helpers


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def chunks(ids, n=12):
    ids = list(ids)
    return [",".join(map(str, ids[i:i + n])) for i in range(0, len(ids), n)]


def named(kind: str, name: str, ids) -> list:
    return [f"*{kind},{kind}={name}"] + chunks(ids)


def ccx(case: Path, job: str, memory: str, timeout: int) -> dict:
    case = case.resolve()
    assert str(case).startswith("/home/"), "mount the case from /home, not from /tmp"
    cmd = ["docker", "run", "--rm", "--memory", memory, "--memory-swap", memory, "--cpus", "1",
           "--user", "%d:%d" % (os.getuid(), os.getgid()),
           "-e", "OMP_NUM_THREADS=1", "-e", "CCX_NPROC_EQUATION_SOLVER=1", "-e", "CCX_NPROC_STIFFNESS=1",
           "-v", f"{case}:/case", "-w", "/case", "--entrypoint", "ccx", IMAGE, "-i", job]
    started = time.time()
    with open(case / f"{job}.log", "w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
    log_text = (case / f"{job}.log").read_text(errors="replace")
    return {"returncode": rc, "wall_seconds": round(time.time() - started, 1), "memory_cap": memory,
            "threads": 1, "image": IMAGE,
            "ccx_version_line": next((l.strip() for l in log_text.splitlines() if "Version" in l), None),
            "errors_in_log": len(re.findall(r"\*ERROR", log_text)),
            "job_finished": "Job finished" in log_text}


def dat_blocks(path: Path, key: str, width: int) -> list:
    """Every block of a .dat file whose header starts with `key`: (time, array of rows)."""

    out = []
    text = path.read_text()
    for part in text.split("\n " + key)[1:]:
        head, _, rest = part.partition("\n")
        when = float(head.split("time")[1].split()[0].replace("D", "E"))
        end = re.search(r"\n\s*[A-Za-z]", rest)
        body = rest[:end.start()] if end else rest
        values = np.array(body.split(), dtype=float)
        out.append((when, values.reshape(-1, width)))
    return out


def frd_temperatures(path: Path) -> list:
    """Every nodal temperature block of an ASCII .frd file: (time, array of node, value)."""

    out, rows, when, reading = [], [], None, False
    with open(path) as f:
        for line in f:
            if line.startswith("  100CL"):
                when = float(line[12:24])
            elif line.startswith(" -4  NDTEMP"):
                reading, rows = True, []
            elif reading and line.startswith(" -1"):
                rows.append((int(line[3:13]), float(line[13:25])))
            elif reading and line.startswith(" -3"):
                out.append((when, np.array(rows, dtype=float)))
                reading = False
    return out


def von_mises(s: np.ndarray) -> np.ndarray:
    return np.sqrt(0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
                   + 3.0 * (s[:, 3:6] ** 2).sum(axis=1))


def box_mesh(nx, ny, nz, h):
    nid = lambda i, j, k: 1 + i + (nx + 1) * (j + (ny + 1) * k)
    lines = ["*NODE,NSET=ALLN"]
    lines += [f"{nid(i, j, k)},{i * h},{j * h},{k * h}"
              for k in range(nz + 1) for j in range(ny + 1) for i in range(nx + 1)]
    lines.append("*ELEMENT,TYPE=C3D8,ELSET=ALLE")
    row_of = {}
    e = 0
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                e += 1
                lines.append(",".join(map(str, [e] + [nid(i + a, j + b, k + c) for a, b, c in HEX])))
                row_of[e] = k
    plane = lambda ks: [nid(i, j, k) for k in ks for j in range(ny + 1) for i in range(nx + 1)]
    return lines, row_of, plane, nid


# --------------------------------------------------------------------------
# witnesses


def witness_thermal(case: Path) -> dict:
    """Two lumps added to a substrate, adiabatic; then a body flux in the last lump.

    Block 20 x 8 x 12 mm on 2 mm cells. Substrate 4 mm at 300 K; lumps of 4 mm
    whose own nodes are at 500 K, added at 1 s and 6 s. A nodal method gives
    the new nodes 500 K and leaves the interface nodes as they are, so the
    mixing temperatures are 375 and 406.25 K (the values Adamantine was held
    to in am_build.py). From 11 s to 16 s the last lump receives 2,000 mW/mm3:
    the mean must rise by q V_lump t / (rho c V_block).
    """

    case.mkdir(parents=True, exist_ok=False)
    rho, c, k, q = 2.67e-9, 9.0e8, 150.0, 2000.0
    lines, row_of, plane, _ = box_mesh(10, 4, 6, 2.0)
    for name, rows in (("SUB", (0, 1)), ("L1", (2, 3)), ("L2", (4, 5))):
        lines += named("ELSET", name, [e for e, r in row_of.items() if r in rows])
    lines += named("NSET", "COLD", plane([0, 1, 2])) + named("NSET", "HOT", plane([3, 4, 5, 6]))
    lines += ["*MATERIAL,NAME=AL", "*CONDUCTIVITY", f"{k}", "*SPECIFIC HEAT", f"{c}", "*DENSITY", f"{rho}",
              "*SOLID SECTION,ELSET=ALLE,MATERIAL=AL", "*INITIAL CONDITIONS,TYPE=TEMPERATURE", "COLD,300.", "HOT,500."]
    out = ["*NODE PRINT,NSET=ALLN,FREQUENCY=100000", "NT", "*END STEP"]
    lines += ["*STEP,INC=1000", "*HEAT TRANSFER,DIRECT", "0.1,1.", "*MODEL CHANGE,TYPE=ELEMENT,REMOVE", "L1,L2", *out,
              "*STEP,INC=1000", "*HEAT TRANSFER,DIRECT", "0.1,5.", "*MODEL CHANGE,TYPE=ELEMENT,ADD", "L1", *out,
              "*STEP,INC=1000", "*HEAT TRANSFER,DIRECT", "0.1,5.", "*MODEL CHANGE,TYPE=ELEMENT,ADD", "L2", *out,
              "*STEP,INC=1000", "*HEAT TRANSFER,DIRECT", "0.1,5.", "*DFLUX,OP=NEW", f"L2,BF,{q}", *out]
    (case / "w.inp").write_text("\n".join(lines) + "\n")
    run = ccx(case, "w", "2g", 600)
    blocks = dat_blocks(case / "w.dat", "temperatures for set ALLN", 2)
    rise = q * (20 * 8 * 4) * 5.0 / (rho * c * 20 * 8 * 12)
    expected = [None, 375.0, 406.25, 406.25 + rise]
    rows = []
    for (when, a), want, top in zip(blocks, expected, (2, 4, 6, 6)):
        active = a[(a[:, 0] - 1) // 55 <= top]
        plane_mean = np.array([active[(active[:, 0] - 1) // 55 == r, 1].mean() for r in range(top + 1)])
        weights = np.r_[1.0, 2.0 * np.ones(top - 1), 1.0]
        mean = float(np.dot(weights, plane_mean) / weights.sum())
        rows.append({"time_s": when, "volume_mean_K": round(mean, 4), "expected_K": None if want is None else round(want, 4),
                     "spread_K": round(float(np.ptp(active[:, 1])), 4)})
    errors = [abs(r["volume_mean_K"] - r["expected_K"]) for r in rows[1:]]
    return {"what": witness_thermal.__doc__.split("\n")[0], "solver": run, "outputs": rows,
            "largest_error_K": round(max(errors), 5),
            "passed": bool(run["returncode"] == 0 and len(rows) == 4 and max(errors) < 0.05 and rows[2]["spread_K"] < 0.5)}


def witness_bar(case: Path, yield_mpa: float | None, prescribe_new: bool = True) -> dict:
    """A bar held at both ends, the upper half born strain free and then cooled.

    Bar 20 x 4 x 8 mm on 2 mm cells, ends fixed along the bar, Poisson's ratio
    0, E = 70 GPa, expansion 2.3e-5 /K. Lower half at 500 K cools to 400 K:
    161 MPa (the step prescribes 400 K at every node, as the head deck does:
    ccx wants a temperature at every node of the model). The upper half is
    then added strain free, its own nodes at 800 K, the interface at 400 K. Everything cools to 300 K. Elastic: 322 MPa in the
    lower half, 805 MPa in the upper row and 483 MPa in the row at the
    interface (mean of 100 and 500 K of cooling). With a yield of 200 MPa and
    no hardening the von Mises stress is 200 MPa everywhere.
    """

    case.mkdir(parents=True, exist_ok=False)
    lines, row_of, plane, nid = box_mesh(10, 2, 4, 2.0)
    lines += named("ELSET", "SUB", [e for e, r in row_of.items() if r < 2])
    lines += named("ELSET", "L1", [e for e, r in row_of.items() if r >= 2])
    lines += named("NSET", "OLD", plane([0, 1, 2])) + named("NSET", "NEW", plane([3, 4]))
    lines += named("NSET", "XEND", [nid(i, j, k) for k in range(5) for j in range(3) for i in (0, 10)])
    lines += ["*MATERIAL,NAME=AL", "*ELASTIC", "70000.,0."]
    # ccx only allows a strain-free addition in a nonlinear calculation: the elastic bar carries
    # a yield stress it never reaches.
    lines += ["*PLASTIC", f"{yield_mpa or 1.0e5},0."]
    lines += ["*EXPANSION", "2.3e-5", "*SOLID SECTION,ELSET=ALLE,MATERIAL=AL",
              "*INITIAL CONDITIONS,TYPE=TEMPERATURE", "OLD,500.", "NEW,800.",
              "*BOUNDARY", "XEND,1,1", f"{nid(0, 0, 0)},2,3", f"{nid(10, 0, 0)},3,3", f"{nid(0, 2, 0)},3,3"]
    out = ["*EL PRINT,ELSET=ALLE,FREQUENCY=100000", "S", "*END STEP"]
    birth = ["*TEMPERATURE", "NEW,800."] if prescribe_new else []
    lines += ["*STEP,INC=100", "*STATIC", "1.,1.", "*MODEL CHANGE,TYPE=ELEMENT,REMOVE", "L1", "*TEMPERATURE", "ALLN,400.", *out,
              "*STEP,INC=100", "*STATIC", "1.,1.", "*MODEL CHANGE,TYPE=ELEMENT,ADD=STRAIN FREE", "L1", *birth, *out,
              "*STEP,INC=100", "*STATIC", "0.25,1.", "*TEMPERATURE", "ALLN,300.", *out]
    (case / "w.inp").write_text("\n".join(lines) + "\n")
    run = ccx(case, "w", "2g", 600)
    blocks = dat_blocks(case / "w.dat", "stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set ALLE", 8)
    rows = []
    for when, a in blocks:
        row = np.array([row_of[int(e)] for e in a[:, 0]])
        rows.append({"time": when,
                     "sxx_MPa_by_cell_row": [[round(float(a[row == r, 2].min()), 2), round(float(a[row == r, 2].max()), 2)]
                                             for r in sorted(set(row.tolist()))],
                     "von_mises_MPa": [round(float(von_mises(a[:, 2:]).min()), 3), round(float(von_mises(a[:, 2:]).max()), 3)]})
    assert run["job_finished"] and run["errors_in_log"] == 0, run
    return {"solver": run, "steps": rows}


def witness(study, summary) -> None:
    study = Path(study)
    study.mkdir(parents=True, exist_ok=False)
    thermal = witness_thermal(study / "thermal")
    elastic = witness_bar(study / "bar-elastic", None)
    plastic = witness_bar(study / "bar-plastic", 200.0)
    forgotten = witness_bar(study / "bar-elastic-new-nodes-not-prescribed", None, prescribe_new=False)
    last = elastic["steps"][-1]["sxx_MPa_by_cell_row"]
    birth = elastic["steps"][1]["sxx_MPa_by_cell_row"]
    elastic["expected_sxx_MPa_by_cell_row_after_cooling"] = [322.0, 322.0, 483.0, 805.0]
    elastic["passed"] = bool(
        elastic["solver"]["returncode"] == 0
        and all(abs(v) < 0.01 for v in birth[2] + birth[3]) and all(abs(v - 161.0) < 0.01 for v in birth[0] + birth[1])
        and all(abs(lo - want) < 0.05 and abs(hi - want) < 0.05 for (lo, hi), want in zip(last, [322.0, 322.0, 483.0, 805.0])))
    vm = plastic["steps"][-1]["von_mises_MPa"]
    plastic["expected_von_mises_MPa_after_cooling"] = 200.0
    plastic["passed"] = bool(plastic["solver"]["returncode"] == 0 and abs(vm[0] - 200.0) < 0.05 and abs(vm[1] - 200.0) < 0.05)
    forgotten["reading"] = ("the same elastic bar without the temperature of the new nodes in the birth step: the upper "
                            "half is born at the 400 K last prescribed, not at its initial condition of 800 K, and ends at "
                            "161 MPa instead of 483 and 805. Kept as a record of the pitfall, not a check.")
    out = {"schema": "935-cad-twin-build-sim-witness/1", "date": time.strftime("%Y-%m-%d"),
           "thermal_activation_and_body_flux": thermal,
           "bar_elastic": {"what": witness_bar.__doc__.split("\n")[0], **elastic},
           "bar_perfectly_plastic": plastic,
           "bar_new_nodes_not_prescribed": forgotten,
           "passed": bool(thermal["passed"] and elastic["passed"] and plastic["passed"]),
           "claims": "software witnesses of element activation, body flux, strain-free birth and perfect plasticity in "
                     "ccx on blocks; no process, machine, material or part is qualified"}
    Path(summary).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k]["passed"] for k in ("thermal_activation_and_body_flux", "bar_elastic", "bar_perfectly_plastic")}))
    assert out["passed"]


# --------------------------------------------------------------------------
# prepare: voxels, supports, plate, lumps


def prepare(occ_dir, case_file, level, run_dir, support_dir=None) -> None:
    from scipy import ndimage

    occ_dir, run = Path(occ_dir), Path(run_dir)
    case = json.loads(Path(case_file).read_text())
    lv = case["levels"][level]
    pitch, rows_per_lump = float(lv["cell_mm"]), int(lv["cell_rows_per_lump"])
    run.mkdir(parents=True, exist_ok=False)
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    p = float(grid["pitch_mm"])
    k = int(round(pitch / p))
    assert abs(k * p - pitch) < 1e-9
    inside = np.load(occ_dir / grid["array"], mmap_mode="r") > 0.5
    assert case["build"]["direction"] == "-y"
    fine = np.ascontiguousarray(inside.transpose(0, 2, 1)[:, :, ::-1])      # axes: x, z, build height (-y)
    del inside
    where = np.argwhere(fine.any(axis=(1, 2))).ravel(), np.argwhere(fine.any(axis=(0, 2))).ravel(), \
        np.argwhere(fine.any(axis=(0, 1))).ravel()
    lo = [int(w[0]) for w in where]
    uncropped = list(fine.shape)
    fine = fine[lo[0]:, lo[1]:, lo[2]:]
    pad = [(-s) % k for s in fine.shape]
    fine = np.pad(fine, [(0, q) for q in pad])
    n = [s // k for s in fine.shape]
    frac = fine.reshape(n[0], k, n[1], k, n[2], k).mean(axis=(1, 3, 5), dtype=np.float32)
    designed = lv.get("supports") == "designed"
    assert designed or "supports" not in lv
    if designed:
        # The envelope of support_design.py, in this frame before the crop; a cell is a support cell
        # when at least half of it is envelope, the rule of the part.
        support_dir = Path(support_dir)
        laid = json.loads((support_dir / "support-envelope.json").read_text())
        assert laid["occupancy_sha256"] == sha256(occ_dir / grid["array"]), "the layout was made on another occupancy"
        assert laid["shape"] == uncropped and laid["pitch_mm"] == p
        env = np.load(support_dir / "support-envelope.npy", mmap_mode="r")[lo[0]:, lo[1]:, lo[2]:]
        designed_volume = float(env.sum()) * p ** 3
        env = np.pad(env, [(0, q) for q in pad])
        env_frac = env.reshape(n[0], k, n[1], k, n[2], k).mean(axis=(1, 3, 5), dtype=np.float32)
        del env
    fine_volume = float(fine.sum()) * p ** 3
    del fine
    solid = frac >= 0.5
    labels, count = ndimage.label(solid)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    part = labels == int(sizes.argmax())
    part = part[:, :, :int(np.argwhere(part.any(axis=(0, 1))).ravel()[-1]) + 1]
    assert part[:, :, 0].any(), "the lowest row of cells must hold the part"
    nz = part.shape[2]

    # Supports. A cell is self-supporting when one of the 3 x 3 cells below it is solid.
    below = np.zeros_like(part)
    below[:, :, 1:] = ndimage.maximum_filter(part[:, :, :-1], size=(3, 3, 1), mode="constant", cval=0)
    need = part & ~below
    need[:, :, 0] = False
    support = np.zeros_like(part)

    def drop_columns(seed: np.ndarray) -> None:
        carry = np.zeros(part.shape[:2], dtype=bool)
        for c in range(nz - 1, 0, -1):
            carry = (carry | seed[:, :, c]) & ~part[:, :, c - 1]
            support[:, :, c - 1] |= carry
    if designed:
        support |= (env_frac[:, :, :nz] >= 0.5) & ~part
        laid_cells = int(support.sum())
    else:
        drop_columns(need)
    # No group of cells may hang free at any stage of the build: every stage must be
    # face-connected to the plate.
    added_for_connection = 0
    lumps = int(np.ceil(nz / rows_per_lump))
    for _ in range(20):
        loose = np.zeros_like(part)
        for lump in range(lumps):
            top = min(nz, (lump + 1) * rows_per_lump)
            body = np.zeros((part.shape[0], part.shape[1], top + 1), dtype=bool)
            body[:, :, 0] = True                                           # the plate
            body[:, :, 1:] = part[:, :, :top] | support[:, :, :top]
            lab, _ = ndimage.label(body)
            free = body & (lab != lab[0, 0, 0])
            loose[:, :, :top] |= free[:, :, 1:]
        if not loose.any():
            break
        before = int(support.sum())
        drop_columns(loose & part)
        # a loose support column can only stand on a loose part cell; drop under it too
        drop_columns(loose & support)
        added_for_connection += int(support.sum()) - before
        assert int(support.sum()) > before, "a free group could not be supported"
    else:
        raise SystemExit("supports did not reach a connected build")
    assert not (support & part).any()

    margin, plate_rows = int(lv["plate_margin_cells"]), int(round(case["plate"]["thickness_mm"] / pitch))
    foot = (part | support).any(axis=2)
    ext = np.argwhere(foot)
    a0, b0 = ext.min(axis=0) - margin
    a1, b1 = ext.max(axis=0) + margin + 1
    shape = (a1 - a0, b1 - b0, plate_rows + nz)
    kind = np.zeros(shape, dtype=np.int8)                                   # 0 empty, 1 plate, 2 part, 3 support
    kind[:, :, :plate_rows] = 1
    sl = (slice(-a0, -a0 + part.shape[0]), slice(-b0, -b0 + part.shape[1]), slice(plate_rows, None))
    kind[sl][part] = 2
    kind[sl][support] = 3

    cells = np.argwhere(kind > 0)
    order = np.lexsort((cells[:, 0], cells[:, 1], cells[:, 2]))
    cells = cells[order]
    ckind = kind[cells[:, 0], cells[:, 1], cells[:, 2]]
    lump = np.where(ckind == 1, -1, (cells[:, 2] - plate_rows) // rows_per_lump).astype(np.int32)
    node_id = -np.ones(tuple(s + 1 for s in shape), dtype=np.int64)
    corner = (cells[:, None, :] + HEX[None]).reshape(-1, 3)
    node_id[corner[:, 0], corner[:, 1], corner[:, 2]] = 0
    used = np.argwhere(node_id == 0)
    used = used[np.lexsort((used[:, 0], used[:, 1], used[:, 2]))]
    node_id[used[:, 0], used[:, 1], used[:, 2]] = np.arange(len(used))
    conn = node_id[corner[:, 0], corner[:, 1], corner[:, 2]].reshape(-1, 8)
    xyz = used * pitch - np.array([0.0, 0.0, plate_rows * pitch])             # plate top at height 0
    # the lump in which a node first becomes active (-1: plate)
    node_lump = np.full(len(used), np.iinfo(np.int32).max, dtype=np.int32)
    np.minimum.at(node_lump, conn.ravel(), np.repeat(lump, 8))

    # frame: build coordinates (a, b, h) -> twin coordinates (x, y, z)
    origin_x = grid["x0"] - p / 2 + (lo[0] + a0 * k) * p
    origin_z = grid["z0"] - p / 2 + (lo[1] + b0 * k) * p
    y_top = grid["y0"] - p / 2 + grid["shape"][1] * p - lo[2] * p             # twin y of build height 0
    np.savez_compressed(run / "mesh.npz", xyz=xyz, conn=conn, kind=ckind, lump=lump, node_lump=node_lump,
                        cells=cells, pitch=pitch, plate_rows=plate_rows, rows_per_lump=rows_per_lump,
                        to_twin=np.array([origin_x, y_top, origin_z]))
    n_part, n_sup, n_plate = (int((ckind == v).sum()) for v in (2, 3, 1))
    exterior = 0
    padk = np.pad(kind == 2, 1)
    for axis in range(3):
        for sign in (-1, 1):
            exterior += int((padk & ~np.roll(padk, sign, axis=axis)).sum())
    rep = {
        "level": level, "cell_mm": pitch, "cell_rows_per_lump": rows_per_lump, "lump_height_mm": rows_per_lump * pitch,
        "lumps": lumps, "build_height_mm": nz * pitch,
        "solid_rule": "a cell is solid when at least half of its 0.25 mm voxels are inside; largest face-connected group kept",
        "components_before_selection": int(count),
        "hexahedra": {"part": n_part, "support": n_sup, "plate": n_plate}, "nodes": int(len(used)),
        "part_volume_mm3": n_part * pitch ** 3, "occupancy_volume_mm3": fine_volume,
        "part_exterior_area_mm2": exterior * pitch ** 2,
        "support_envelope_mm3": n_sup * pitch ** 3,
        "support_cells_added_for_connection": added_for_connection,
        "cells_needing_support": int(need.sum()),
        "supports": "the envelope of the support layout, a cell at half or more" if designed
                    else "a column under every cell with no solid cell among the nine below it",
        "support_solid_fraction": laid["melted_share_of_the_envelope"] if designed else case["supports"]["solid_fraction"],
        "plate_mm": [shape[0] * pitch, shape[1] * pitch, plate_rows * pitch],
        "occupancy_sha256": sha256(occ_dir / grid["array"]),
    }
    if designed:
        rep["support_layout"] = {"rules_sha256": laid["rules_sha256"], "envelope_mm3": designed_volume,
                                 "envelope_kept_in_cells_mm3": laid_cells * pitch ** 3,
                                 "share_kept_in_cells": laid_cells * pitch ** 3 / designed_volume}
    (run / "prepare.json").write_text(json.dumps(rep, indent=2) + "\n")
    (run / "case.json").write_text(json.dumps(case, indent=2) + "\n")
    (run / "level.txt").write_text(level)
    print(json.dumps(rep))


def load(run: Path):
    m = np.load(run / "mesh.npz")
    case = json.loads((run / "case.json").read_text())
    lv = case["levels"][(run / "level.txt").read_text().strip()]
    if "process" in lv:                                # a level may declare its own process values (number of lasers)
        assert set(lv["process"]) <= set(case["process"]), "a level can only change a declared process value"
        case["process"] = {**case["process"], **lv["process"]}
    if lv.get("supports") == "designed":               # the solid fraction of the layout, not the declared one
        case["supports"] = {**case["supports"],
                            "solid_fraction": json.loads((run / "prepare.json").read_text())["support_solid_fraction"]}
    return m, case, lv


def mesh_lines(m) -> list:
    lines = ["*NODE,NSET=ALLN"]
    lines += ["%d,%.6g,%.6g,%.6g" % (i + 1, *q) for i, q in enumerate(m["xyz"])]
    lines.append("*ELEMENT,TYPE=C3D8,ELSET=ALLE")
    lines += ["%d,%d,%d,%d,%d,%d,%d,%d,%d" % (i + 1, *(c + 1)) for i, c in enumerate(m["conn"])]
    kind, lump = m["kind"], m["lump"]
    lines += named("ELSET", "PLATE", np.flatnonzero(kind == 1) + 1)
    for j in range(int(lump.max()) + 1):
        for tag, value in (("P", 2), ("S", 3)):
            ids = np.flatnonzero((kind == value) & (lump == j)) + 1
            if len(ids):
                lines += named("ELSET", f"{tag}{j}", ids)
    lines += named("ELSET", "PART", np.flatnonzero(kind == 2) + 1)
    if (kind == 3).any():
        lines += named("ELSET", "SUPPORT", np.flatnonzero(kind == 3) + 1)
    lines += named("NSET", "PBOT", np.flatnonzero(np.isclose(m["xyz"][:, 2], m["xyz"][:, 2].min())) + 1)
    return lines


def lump_sets(m, j: int) -> list:
    kind, lump = m["kind"], m["lump"]
    return [f"{tag}{j}" for tag, value in (("P", 2), ("S", 3)) if ((kind == value) & (lump == j)).any()]


def schedule(m, case) -> list:
    """Real time and absorbed energy of every lump."""

    pr, pitch = case["process"], float(m["pitch"])
    kind, lump = m["kind"], m["lump"]
    f = case["supports"]["solid_fraction"]
    built_rows = int(m["cells"][:, 2].max()) + 1 - int(m["plate_rows"])
    rows = []
    for j in range(int(lump.max()) + 1):
        v_part = float(((kind == 2) & (lump == j)).sum()) * pitch ** 3
        v_sup = float(((kind == 3) & (lump == j)).sum()) * pitch ** 3
        melted = v_part + f * v_sup
        # the last lump holds fewer rows when the build height is not a whole number of lumps
        lump_rows = min(int(m["rows_per_lump"]), built_rows - j * int(m["rows_per_lump"]))
        assert lump_rows >= 1
        layers = lump_rows * pitch / pr["layer_thickness_mm"]
        exposure = melted * pr["volumetric_energy_density_J_mm3"] / (pr["laser_power_W"] * pr["lasers"])
        rows.append({"lump": j, "part_mm3": v_part, "support_envelope_mm3": v_sup, "melted_mm3": melted,
                     "real_layers": layers, "exposure_s": exposure, "recoating_s": layers * pr["recoating_s_per_layer"],
                     "duration_s": exposure + layers * pr["recoating_s_per_layer"],
                     "absorbed_J": pr["absorptivity"] * pr["volumetric_energy_density_J_mm3"] * melted})
    return rows


# --------------------------------------------------------------------------
# thermal


def thermal(run_dir) -> None:
    run = Path(run_dir)
    m, case, lv = load(run)
    mat, f, t_plate = case["material"], case["supports"]["solid_fraction"], case["plate"]["temperature_K"]
    rho, c, k = mat["density_kg_m3"] * 1e-12, mat["specific_heat_J_kgK"] * 1e6, mat["conductivity_W_mK"]
    plan = schedule(m, case)
    lines = mesh_lines(m)
    lines += ["*MATERIAL,NAME=AL", "*CONDUCTIVITY", f"{k}", "*SPECIFIC HEAT", f"{c}", "*DENSITY", f"{rho}",
              "*MATERIAL,NAME=SUP", "*CONDUCTIVITY", f"{k * f}", "*SPECIFIC HEAT", f"{c}", "*DENSITY", f"{rho * f}",
              "*SOLID SECTION,ELSET=PLATE,MATERIAL=AL", "*SOLID SECTION,ELSET=PART,MATERIAL=AL"]
    if (m["kind"] == 3).any():
        lines.append("*SOLID SECTION,ELSET=SUPPORT,MATERIAL=SUP")
    lines += ["*INITIAL CONDITIONS,TYPE=TEMPERATURE", f"ALLN,{t_plate}", "*BOUNDARY", f"PBOT,11,11,{t_plate}"]
    every_lump = [s for j in range(len(plan)) for s in lump_sets(m, j)]
    # Temperatures go to the .frd file at the end of each step; the heat flow at the plate face is
    # printed at every increment (a *NODE PRINT frequency applies to every *NODE PRINT of the step).
    out = ["*NODE FILE,FREQUENCY=100000", "NT", "*NODE PRINT,NSET=PBOT,TOTALS=ONLY,FREQUENCY=1", "RFL", "*END STEP"]
    lines += ["*STEP,INC=10", "*HEAT TRANSFER,DIRECT", "1.,1.", "*MODEL CHANGE,TYPE=ELEMENT,REMOVE", *chunks(every_lump, 8), *out]
    inc = int(lv["thermal_increments_per_lump"])
    for row in plan:
        j = row["lump"]
        lines += [f"*STEP,INC={inc * 4}", "*HEAT TRANSFER,DIRECT", f"{row['duration_s'] / inc:.9g},{row['duration_s']:.9g}",
                  "*MODEL CHANGE,TYPE=ELEMENT,ADD", *chunks(lump_sets(m, j), 8), "*DFLUX,OP=NEW"]
        # absorbed energy of the lump, spread over its melted volume and its real time (mJ/s/mm3)
        q = row["absorbed_J"] * 1e3 / row["duration_s"] / row["melted_mm3"]
        for s in lump_sets(m, j):
            lines.append(f"{s},BF,{q * (1.0 if s[0] == 'P' else f):.9g}")
        lines += out
    (run / "thermal.inp").write_text("\n".join(lines) + "\n")
    rep = {"solver": ccx(run, "thermal", lv["memory_cap"], 24 * 3600)}
    (run / "thermal-run.json").write_text(json.dumps(rep, indent=2) + "\n")
    assert rep["solver"]["returncode"] == 0 and rep["solver"]["job_finished"], rep
    thermal_read(run)


def thermal_read(run_dir) -> None:
    run = Path(run_dir)
    m, case, lv = load(run)
    plan = schedule(m, case)
    mat, f, t_plate = case["material"], case["supports"]["solid_fraction"], case["plate"]["temperature_K"]
    # ccx writes the field at every increment (the frequency of the heat-flow print applies to the
    # file output as well): keep the block at the end of each step.
    every = frd_temperatures(run / "thermal.frd")
    ends = np.cumsum([1.0] + [row["duration_s"] for row in plan])
    stamps = np.array([t for t, _ in every])
    blocks = [every[int(np.argmin(np.abs(stamps - end)))] for end in ends]
    assert all(abs(b[0] - end) < 1e-3 * end for b, end in zip(blocks, ends)), "a step end is missing from the .frd file"
    temps = np.full((len(plan), len(m["xyz"])), np.nan, dtype=np.float32)
    kind, lump, conn, node_lump, pitch = m["kind"], m["lump"], m["conn"], m["node_lump"], float(m["pitch"])
    heat_capacity = np.where(kind == 3, f, 1.0) * mat["density_kg_m3"] * 1e-9 * mat["specific_heat_J_kgK"] * pitch ** 3   # J/K per cell
    flow = dat_blocks(run / "thermal.dat", "total heat generation for set PBOT", 1)
    times = np.array([t for t, _ in flow])
    power = np.array([float(a[0, 0]) for _, a in flow]) * 1e-3                                                             # W into the model at the plate face
    rows, clock, absorbed = [], 1.0, 0.0
    for row, (when, a) in zip(plan, blocks[1:]):
        j = row["lump"]
        field = np.full(len(m["xyz"]), np.nan, dtype=np.float32)
        field[a[:, 0].astype(int) - 1] = a[:, 1]
        field[node_lump > j] = np.nan
        temps[j] = field
        active = (kind == 1) | (lump <= j)
        cell_t = field[conn[active]].mean(axis=1)
        stored = float(np.dot(heat_capacity[active], cell_t - t_plate))
        absorbed += row["absorbed_J"]
        clock += row["duration_s"]
        # backward Euler: the heat that leaves in an increment is its end value times its length
        upto = times <= clock * (1.0 + 1e-5)        # the print carries seven digits
        left = float(-np.dot(power[upto][1:], np.diff(times[upto])))
        part_now = (kind == 2) & (lump <= j)
        new = (kind == 2) & (lump == j)
        rows.append({"lump": j, "end_time_s": round(clock, 1), "duration_s": round(row["duration_s"], 1),
                     "mean_absorbed_power_W": round(row["absorbed_J"] / row["duration_s"], 2),
                     "plate_sink_power_at_end_W": round(float(-power[upto][-1]), 2),
                     "absorbed_J": round(absorbed, 1), "left_through_plate_J": round(left, 1), "stored_J": round(stored, 1),
                     "energy_imbalance": round((stored + left - absorbed) / absorbed, 5),
                     "rise_K": {"new_lump_mean": round(float(field[conn[new]].mean() - t_plate), 2),
                                "new_lump_max": round(float(np.nanmax(field[conn[new]]) - t_plate), 2),
                                "part_mean": round(float(field[conn[part_now]].mean() - t_plate), 2),
                                "part_max": round(float(np.nanmax(field[conn[part_now]]) - t_plate), 2)}})
    np.save(run / "thermal-end-of-lump.npy", temps)
    hottest = max(rows, key=lambda r: r["rise_K"]["part_max"])
    where = int(np.nanargmax(temps[hottest["lump"]]))
    out = {"build_time_s": round(clock, 1), "build_time_h": round(clock / 3600.0, 2),
           "exposure_h": round(sum(r["exposure_s"] for r in plan) / 3600.0, 2),
           "recoating_h": round(sum(r["recoating_s"] for r in plan) / 3600.0, 2),
           "absorbed_MJ": round(absorbed / 1e6, 3),
           "largest_rise_over_plate_K": hottest["rise_K"]["part_max"], "at_lump": hottest["lump"],
           "at_build_coordinates_mm": [round(float(v), 2) for v in m["xyz"][where]],
           "largest_new_lump_mean_rise_K": max(r["rise_K"]["new_lump_mean"] for r in rows),
           "largest_energy_imbalance": max(abs(r["energy_imbalance"]) for r in rows),
           "lumps": rows}
    (run / "thermal.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "lumps"}))


# --------------------------------------------------------------------------
# mechanics


def mechanics(run_dir, *options) -> None:
    run = Path(run_dir)
    m, case, lv = load(run)
    mat, f = case["material"], case["supports"]["solid_fraction"]
    t_plate, t_room = case["plate"]["temperature_K"], case["cooldown"]["room_temperature_K"]
    tag = "mechanics"
    if "--variant" in options:                       # a named change of material values, declared in the case file
        name = options[options.index("--variant") + 1]
        mat = {**mat, **{k: v for k, v in case["variants"][name].items() if k in mat}}
        tag += "-" + name
    t_relax = mat["stress_free_temperature_K"]
    if "--relax" in options:
        t_relax = float(options[options.index("--relax") + 1])
        tag += f"-relax{int(round(t_relax))}"
    temps = np.load(run / "thermal-end-of-lump.npy")
    kind, lump, node_lump, xyz = m["kind"], m["lump"], m["node_lump"], m["xyz"]
    lumps = int(lump.max()) + 1
    lines = mesh_lines(m)
    nu, alpha = mat["poisson_ratio"], mat["thermal_expansion_per_K"]
    hardening = mat["hardening_modulus_MPa"]
    for name, scale in (("AL", 1.0), ("SUP", f)):
        lines += [f"*MATERIAL,NAME={name}", "*ELASTIC"]
        lines += [f"{e * scale:.9g},{nu},{t + K0:.6g}" for t, e in mat["youngs_modulus_MPa_by_temperature_C"]]
        lines += ["*PLASTIC"]
        for t, y in mat["yield_MPa_by_temperature_C"]:
            lines += [f"{y * scale:.9g},0.,{t + K0:.6g}", f"{(y + hardening) * scale:.9g},1.,{t + K0:.6g}"]
        lines += ["*EXPANSION,ZERO=293.15", f"{alpha}"]
    pl = case["plate"]
    lines += ["*MATERIAL,NAME=PLATE", "*ELASTIC", f"{pl['youngs_modulus_MPa']},{pl['poisson_ratio']}",
              "*EXPANSION,ZERO=293.15", f"{pl['thermal_expansion_per_K']}",
              "*SOLID SECTION,ELSET=PLATE,MATERIAL=PLATE", "*SOLID SECTION,ELSET=PART,MATERIAL=AL"]
    if (kind == 3).any():
        lines.append("*SOLID SECTION,ELSET=SUPPORT,MATERIAL=SUP")
    # plate: lower face kept plane, free to shrink in its plane
    bottom = np.flatnonzero(np.isclose(xyz[:, 2], xyz[:, 2].min()))
    a = bottom[np.lexsort((xyz[bottom, 1], xyz[bottom, 0]))[0]]
    b = bottom[np.lexsort((xyz[bottom, 1], -xyz[bottom, 0]))[0]]
    lines += ["*INITIAL CONDITIONS,TYPE=TEMPERATURE", f"ALLN,{t_plate}",
              "*BOUNDARY", "PBOT,3,3", f"{a + 1},1,2", f"{b + 1},2,2"]
    watch = int(np.flatnonzero(kind == 2)[0]) + 1
    quiet = ["*NODE PRINT,NSET=ALLN,FREQUENCY=100000", "U", f"*ELSET,ELSET=WATCH\n{watch}", "*EL PRINT,ELSET=WATCH,FREQUENCY=100000", "S"]
    quiet_again = ["*NODE PRINT,NSET=ALLN,FREQUENCY=100000", "U", "*EL PRINT,ELSET=WATCH,FREQUENCY=100000", "S"]
    full = ["*NODE PRINT,NSET=ALLN,FREQUENCY=100000", "U", "*EL PRINT,ELSET=PART,FREQUENCY=100000", "S,PEEQ"]
    static = ["*STATIC", "0.5,1.,1.e-6,1."]
    every_lump = [s for j in range(lumps) for s in lump_sets(m, j)]
    lines += ["*STEP,INC=200", "*STATIC", "1.,1.", "*MODEL CHANGE,TYPE=ELEMENT,REMOVE", *chunks(every_lump, 8),
              "*TEMPERATURE", f"ALLN,{t_plate}", *quiet, "*END STEP"]
    stages = ["plate only"]
    for j in range(lumps):
        new = np.flatnonzero(node_lump == j) + 1
        active = np.flatnonzero((node_lump <= j) & (node_lump >= 0)) + 1
        lines += ["*STEP,INC=200", "*STATIC", "1.,1.", "*MODEL CHANGE,TYPE=ELEMENT,ADD=STRAIN FREE", *chunks(lump_sets(m, j), 8),
                  "*TEMPERATURE"] + [f"{n},{t_relax:.6g}" for n in new] + [*quiet_again, "*END STEP"]
        stages.append(f"birth {j}")
        lines += ["*STEP,INC=400", *static, "*TEMPERATURE"]
        lines += [f"{n},{temps[j, n - 1]:.6g}" for n in active]
        lines += [*(full if j == lumps - 1 else quiet_again), "*END STEP"]
        stages.append(f"cool {j}")
    lines += ["*STEP,INC=400", *static, "*TEMPERATURE", f"ALLN,{t_room}", *full, "*END STEP"]
    stages.append("room temperature, on the plate")
    # Release: plate and supports go, and the part is held statically determinate (3-2-1) at the
    # displacements it has, so that no reaction builds up between the held nodes.
    part_nodes = np.unique(m["conn"][kind == 2])
    q = xyz[part_nodes]
    n1 = part_nodes[np.lexsort((q[:, 1], q[:, 0], q[:, 2]))[0]]                 # lowest, then smallest a, then b
    n2 = part_nodes[np.argmax(np.abs(q[:, 0] - xyz[n1, 0]) - 0.01 * np.abs(q[:, 2] - xyz[n1, 2]))]   # far along a
    n3 = part_nodes[np.argmax(np.abs(q[:, 1] - xyz[n1, 1]) - 0.01 * np.abs(q[:, 2] - xyz[n1, 2]))]   # far along b
    assert len({int(n1), int(n2), int(n3)}) == 3
    assert abs(xyz[n2, 0] - xyz[n1, 0]) > 20.0 and abs(xyz[n3, 1] - xyz[n1, 1]) > 20.0
    gone = ["PLATE"] + (["SUPPORT"] if (kind == 3).any() else [])
    lines += ["*STEP,INC=400", *static, "*MODEL CHANGE,TYPE=ELEMENT,REMOVE", *gone,
              "*BOUNDARY,FIXED", f"{n1 + 1},1,3", f"{n2 + 1},2,3", f"{n3 + 1},3,3", *full, "*END STEP"]
    stages.append("released from plate and supports")
    (run / f"{tag}.inp").write_text("\n".join(lines) + "\n")
    (run / f"{tag}-stages.json").write_text(json.dumps({"stages": stages, "stress_free_temperature_K": t_relax,
                                                        "yield_MPa_by_temperature_C": mat["yield_MPa_by_temperature_C"],
                                                        "held_nodes_at_release": [int(n1) + 1, int(n2) + 1, int(n3) + 1]}) + "\n")
    rep = {"solver": ccx(run, tag, lv["memory_cap"], 24 * 3600)}
    (run / f"{tag}-run.json").write_text(json.dumps(rep, indent=2) + "\n")
    assert rep["solver"]["returncode"] == 0 and rep["solver"]["job_finished"], rep
    mechanics_read(run, tag)


def remove_rigid(xyz: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Least-squares removal of a small rigid motion."""

    r = xyz - xyz.mean(axis=0)
    basis = np.zeros((len(r), 3, 6))
    basis[:, :, :3] = np.eye(3)
    basis[:, 0, 4], basis[:, 0, 5] = r[:, 2], -r[:, 1]
    basis[:, 1, 3], basis[:, 1, 5] = -r[:, 2], r[:, 0]
    basis[:, 2, 3], basis[:, 2, 4] = r[:, 1], -r[:, 0]
    flat = basis.reshape(-1, 6)
    return u - (flat @ np.linalg.lstsq(flat, u.ravel(), rcond=None)[0]).reshape(-1, 3)


def mechanics_read(run_dir, tag="mechanics") -> None:
    run = Path(run_dir)
    m, case, lv = load(run)
    stages = json.loads((run / f"{tag}-stages.json").read_text())
    names = stages["stages"]
    kind, xyz, conn = m["kind"], m["xyz"], m["conn"]
    part_nodes = np.unique(conn[kind == 2])
    u_blocks = dat_blocks(run / f"{tag}.dat", "displacements (vx,vy,vz) for set ALLN", 4)
    s_blocks = dat_blocks(run / f"{tag}.dat", "stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set PART", 8)
    p_blocks = dat_blocks(run / f"{tag}.dat", "equivalent plastic strain (elem, integ.pnt.,pe)for set PART", 3)
    assert len(u_blocks) == len(names), (len(u_blocks), len(names))
    assert len(s_blocks) == 3, len(s_blocks)

    def field(block):
        u = np.zeros((len(xyz), 3))
        u[block[:, 0].astype(int) - 1] = block[:, 1:4]
        return u

    growth = []
    for name, (_, block) in zip(names, u_blocks):
        if name.startswith("cool"):
            u = field(block)
            j = int(name.split()[1])
            live = part_nodes[m["node_lump"][part_nodes] <= j]
            growth.append({"lump": j, "largest_displacement_mm": round(float(np.linalg.norm(u[live], axis=1).max()), 4)})
    yield_room = stages["yield_MPa_by_temperature_C"][0][1]
    states = {}
    saved = {}
    for label, u_block, (_, s), (_, pe) in zip(("end_of_build_hot", "room_temperature_on_plate", "released"),
                                               u_blocks[-3:], s_blocks, p_blocks):
        u = field(u_block[1])
        vm = von_mises(s[:, 2:])
        cell_vm = np.zeros(len(conn))
        np.maximum.at(cell_vm, s[:, 0].astype(int) - 1, vm)
        mean_vm = np.bincount(s[:, 0].astype(int) - 1, weights=vm, minlength=len(conn))[kind == 2] / 8.0
        states[label] = {
            "largest_displacement_mm": round(float(np.linalg.norm(u[part_nodes], axis=1).max()), 4),
            "von_mises_MPa": {"cell_mean_median": round(float(np.median(mean_vm)), 1),
                              "cell_mean_p95": round(float(np.quantile(mean_vm, 0.95)), 1),
                              "integration_point_max": round(float(vm.max()), 1)},
            "share_of_part_cells_within_5_percent_of_room_yield": round(float((mean_vm > 0.95 * yield_room).mean()), 4),
            "equivalent_plastic_strain": {"median": round(float(np.median(pe[:, 2])), 5),
                                          "p95": round(float(np.quantile(pe[:, 2], 0.95)), 5),
                                          "max": round(float(pe[:, 2].max()), 5)}}
        saved[label + "_u"] = u.astype(np.float32)
        saved[label + "_vm"] = (np.bincount(s[:, 0].astype(int) - 1, weights=vm, minlength=len(conn)) / 8.0).astype(np.float32)
    change = saved["released_u"][part_nodes] - saved["room_temperature_on_plate_u"][part_nodes]
    shape = remove_rigid(xyz[part_nodes], change.astype(np.float64))
    total = remove_rigid(xyz[part_nodes], saved["released_u"][part_nodes].astype(np.float64))
    # uniform shrinkage is not distortion: remove the best-fit isotropic scale as well
    r = xyz[part_nodes] - xyz[part_nodes].mean(axis=0)
    scale = float((total * r).sum() / (r * r).sum())
    warp = remove_rigid(xyz[part_nodes], total - scale * r)
    norm = np.linalg.norm(warp, axis=1)
    worst = int(np.argmax(norm))
    saved["released_warp"] = np.zeros((len(xyz), 3), dtype=np.float32)
    saved["released_warp"][part_nodes] = warp
    np.savez_compressed(run / f"{tag}-fields.npz", **saved)
    out = {"stress_free_temperature_K": stages["stress_free_temperature_K"],
           "yield_MPa_by_temperature_C": stages["yield_MPa_by_temperature_C"],
           "solver": json.loads((run / f"{tag}-run.json").read_text())["solver"],
           "states": states,
           "release": {"change_of_shape_at_release_largest_mm": round(float(np.linalg.norm(shape, axis=1).max()), 4),
                       "best_fit_uniform_shrinkage": round(scale, 6),
                       "distortion_after_release_rigid_motion_and_uniform_shrinkage_removed_mm": {
                           "largest": round(float(norm.max()), 4), "p95": round(float(np.quantile(norm, 0.95)), 4),
                           "median": round(float(np.median(norm)), 4),
                           "largest_at_build_coordinates_mm": [round(float(v), 2) for v in xyz[part_nodes][worst]]}},
           "largest_displacement_during_the_build_by_lump": growth}
    (run / f"{tag}.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("largest_displacement_during_the_build_by_lump", "solver")}))


# --------------------------------------------------------------------------
# summarize


USED_BY_A_RUN = ("build", "process", "plate", "supports", "material", "variants", "cooldown")


def summarize(study, case_file, witness_file, out) -> None:
    study, case = Path(study), json.loads(Path(case_file).read_text())
    levels = {}
    for name in case["levels"]:
        run = study / name
        if not (run / "thermal.json").exists():
            continue
        # a run stands when every value it used is unchanged: the physical blocks of the case and its own level
        ran = json.loads((run / "case.json").read_text())
        assert (all(ran[k] == case[k] for k in USED_BY_A_RUN) and ran["levels"][name] == case["levels"][name]), \
            f"{name} was run on another case"
        assert (run / "thermal.inp").stat().st_mtime >= (run / "mesh.npz").stat().st_mtime, f"{name}: thermal deck older than its mesh"
        thermal = json.loads((run / "thermal.json").read_text())
        thermal["solver"] = json.loads((run / "thermal-run.json").read_text())["solver"]
        thermal["lumps"] = [{"lump": r["lump"], "end_time_h": round(r["end_time_s"] / 3600.0, 2),
                             "mean_absorbed_power_W": r["mean_absorbed_power_W"],
                             "plate_sink_power_at_end_W": r["plate_sink_power_at_end_W"],
                             "new_lump_mean_rise_K": r["rise_K"]["new_lump_mean"], "part_max_rise_K": r["rise_K"]["part_max"]}
                            for r in thermal["lumps"]]
        entry = {"model": json.loads((run / "prepare.json").read_text()), "thermal": thermal, "mechanics": {}}
        for path in sorted(run.glob("mechanics*.json")):
            if path.name.endswith(("-run.json", "-stages.json")):
                continue
            assert path.stat().st_mtime >= (run / "thermal-end-of-lump.npy").stat().st_mtime, f"{path}: older than its thermal field"
            entry["mechanics"][path.stem] = json.loads(path.read_text())
        levels[name] = entry
    witness_record = json.loads(Path(witness_file).read_text())
    assert witness_record["passed"]
    out_record = {
        "schema": "935-cad-twin-build-sim/1", "date": time.strftime("%Y-%m-%d"),
        "scope": "layer-by-layer build screen of the print body under declared hypotheses: time-averaged temperature during "
                 "the build, then stress and distortion from strain-free birth and cooling, on voxel cells with homogenised "
                 "supports (columns under a 45 degree rule, or the envelope of a layout by rule). No melt pool, scan path, "
                 "support prepared in a build processor, creep or calibration against a printed coupon",
        "case_file": "params/build-sim-case.json", "case_sha256": sha256(Path(case_file)),
        "witness_file": "params/build-sim-witness.json", "witnesses_passed": True,
        "tool": "CalculiX 2.21 in the cadsim image, one thread, SPOOLES; element activation with *MODEL CHANGE",
        "levels": levels,
        "gates": {"process_parameters_published_by_the_machine_maker": False, "heat_input_calibrated": False,
                  "supports_prepared_in_a_build_processor": False, "distortion_compared_with_a_printed_part": False,
                  "metal_print_authorized": False},
        "claims": "a screen. It qualifies no process, orientation, support scheme, material or part, and its distortion is "
                  "not a compensation field",
    }
    Path(out).write_text(json.dumps(out_record, indent=1) + "\n")
    print(json.dumps({name: {"rise_K": e["thermal"]["largest_rise_over_plate_K"], "mechanics": sorted(e["mechanics"])}
                      for name, e in levels.items()}))


if __name__ == "__main__":
    {"witness": witness, "prepare": prepare, "thermal": thermal, "thermal-read": thermal_read,
     "mechanics": mechanics, "mechanics-read": mechanics_read, "summarize": summarize}[sys.argv[1]](*sys.argv[2:])
