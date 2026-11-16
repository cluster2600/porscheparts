#!/usr/bin/env python3
"""One laser track on a solid block with the GO-MELT kernel: melt-pool width and depth.

A single-level, explicit, matrix-free heat conduction run built from three functions of the
reviewed GO-MELT revision (computeStateProperties, computeSourcesL3, solveMatrixFreeFE). Half of
the track is modelled: the plane y = 0 through the laser path is a plane of symmetry, and every
face of the block is adiabatic. Units are GO-MELT's: mm, s, K, W.

  block     x along the track, y across it from the symmetry plane, z down from the top face;
  source    GO-MELT's Gaussian volumetric source, centred on the top face, travelling along +x;
  result    the largest temperature every node reaches; the melt pool is where it passes the
            melting temperature. Width and depth are read in the middle of the track, and the
            energy put in is compared with the heat stored at the end.

Usage: melt_pool_track.py GO_MELT_DIR CASE.json OUT_DIR
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("JAX_ENABLE_X64", "true")
KERNEL_SHA256 = "cf1889dfb41e11591e4245a9199262e66ae972e3a75e2c00baddd30f32851176"


def main(go_melt_dir, case_file, out_dir) -> None:
    source = Path(go_melt_dir) / "go_melt" / "computeFunctions.py"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == KERNEL_SHA256, "not the reviewed GO-MELT kernel revision"
    sys.path.insert(0, str(source.parent))
    import jax
    import jax.numpy as jnp
    import numpy as np
    import computeFunctions as kernel

    case = json.loads(Path(case_file).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    h = case["element_mm"]
    lx, ly, lz = case["block_mm"]
    ne = [int(round(lx / h)), int(round(ly / h)), int(round(lz / h))]
    nn = [n + 1 for n in ne]
    coords, connect = kernel.createMesh3D((0.0, lx, nn[0]), (0.0, ly, nn[1]), (-lz, 0.0, nn[2]))
    level = {"node_coords": coords, "connect": connect, "elements": ne, "nodes": nn}
    n_el, n_no = ne[0] * ne[1] * ne[2], nn[0] * nn[1] * nn[2]
    ne_nn = (0, n_el, 0, 0, n_no)

    mat, laser = case["material"], case["laser"]
    props = kernel.SetupProperties({
        "thermal_conductivity_bulk_a0": mat["conductivity_W_mK"], "thermal_conductivity_bulk_a1": 0.0,
        "thermal_conductivity_fluid_a0": mat.get("conductivity_liquid_W_mK", mat["conductivity_W_mK"]),
        "heat_capacity_solid_a0": mat["specific_heat_J_kgK"], "heat_capacity_solid_a1": 0.0,
        "heat_capacity_fluid": mat.get("specific_heat_liquid_J_kgK", mat["specific_heat_J_kgK"]),
        "heat_capacity_mushy": mat["specific_heat_J_kgK"] + mat.get("latent_heat_J_kg", 0.0) / max(mat["liquidus_K"] - mat["solidus_K"], 1e-9),
        "density": mat["density_kg_m3"] * 1e-9,
        "laser_radius": laser["radius_mm"], "laser_depth": laser["depth_mm"], "laser_power": laser["power_W"],
        "laser_absorptivity": laser["absorptivity"],
        "T_amb": case["start_temperature_K"], "T_solidus": mat["solidus_K"], "T_liquidus": mat["liquidus_K"],
    })
    speed = laser["speed_mm_s"]
    x0, travel = case["track_start_mm"], case["track_length_mm"]
    diffusivity = mat["conductivity_W_mK"] * 1e-3 / (mat["density_kg_m3"] * 1e-9 * mat["specific_heat_J_kgK"])     # mm2/s
    dt = case["stability_factor"] * h * h / (6.0 * diffusivity)
    chunk = int(case.get("steps_per_chunk", 200))
    # a whole number of chunks covers exactly the requested track: the step is shortened to fit
    steps = int(np.ceil(travel / speed / dt / chunk)) * chunk
    dt = travel / speed / steps
    t0 = case["start_temperature_K"]
    solid = jnp.ones(n_no)

    def step(carry, i):
        T, peak = carry
        _, _, k, rhocp = kernel.computeStateProperties(T, solid, props, n_no)
        position = jnp.array([x0 + speed * dt * (i + 0.5), 0.0, 0.0])
        F = kernel.computeSourcesL3(level, position, ne_nn, props, laser["power_W"])
        T = kernel.solveMatrixFreeFE(level, n_no, n_el, k, rhocp, dt, T, F, 0.0)
        return (T, jnp.maximum(peak, T)), F.sum()

    @jax.jit
    def advance(carry, first):
        return jax.lax.scan(step, carry, first + jnp.arange(chunk))

    T = jnp.full(n_no, t0)
    carry = (T, T)
    injected = 0.0
    frames_every = max(1, (steps // chunk) // int(case.get("frames", 60)))
    top, side, times = [], [], []
    shape = (nn[2], nn[1], nn[0])                             # node index = ix + iy nnx + iz nnx nny
    started = time.time()
    done = 0
    while done < steps:
        carry, sums = advance(carry, done)
        injected += float(sums.sum()) * dt
        done += chunk
        if (done // chunk) % frames_every == 0:
            field = np.asarray(carry[0]).reshape(shape)
            top.append(field[-1].astype(np.float32))          # the top face, y by x
            side.append(field[:, 0, :].astype(np.float32))    # the symmetry plane, z by x
            times.append(done * dt)
    wall = time.time() - started
    steps_run = done
    T, peak = (np.asarray(a).reshape(shape) for a in carry)

    # heat stored at the end: nodal volumes times the enthalpy rise (trapezoid weights of the regular grid)
    wx, wy, wz = (np.r_[0.5, np.ones(n - 2), 0.5] * h for n in nn)
    volume = wz[:, None, None] * wy[None, :, None] * wx[None, None, :]
    rho = mat["density_kg_m3"] * 1e-9
    cp_s, cp_l = mat["specific_heat_J_kgK"], mat.get("specific_heat_liquid_J_kgK", mat["specific_heat_J_kgK"])
    ts, tl, latent = mat["solidus_K"], mat["liquidus_K"], mat.get("latent_heat_J_kg", 0.0)
    cp_m = cp_s + latent / max(tl - ts, 1e-9)
    enthalpy = np.where(T <= ts, cp_s * (T - t0),
                        np.where(T < tl, cp_s * (ts - t0) + cp_m * (T - ts), cp_s * (ts - t0) + cp_m * (tl - ts) + cp_l * (T - tl)))
    stored = float((volume * rho * enthalpy).sum())
    expected = 0.5 * laser["absorptivity"] * laser["power_W"] * steps_run * dt     # half of the track is modelled

    # melt pool in the middle third of the track, from the largest temperature each node reached
    x = np.asarray(coords[0])
    y = np.asarray(coords[1])
    z = np.asarray(coords[2])
    middle = (x >= x0 + travel / 3.0) & (x <= x0 + 2.0 * travel / 3.0)
    t_melt = mat[case.get("pool_isotherm", "solidus_K")]

    def reach(profile, axis_values):
        """Distance from the laser path at which a monotonically falling profile crosses the melting temperature."""
        above = profile >= t_melt
        if not above.any():
            return 0.0
        k = int(np.flatnonzero(above).max())
        if k + 1 >= len(profile):
            return float(abs(axis_values[k]))
        a, b = profile[k], profile[k + 1]
        return float(abs(axis_values[k]) + (a - t_melt) / (a - b) * abs(axis_values[k + 1] - axis_values[k]))

    half_widths = [reach(peak[-1, :, i], y) for i in np.flatnonzero(middle)]
    depths = [reach(peak[::-1, 0, i], z[::-1]) for i in np.flatnonzero(middle)]
    report = {
        "schema": "melt-pool-track/1", "date": time.strftime("%Y-%m-%d"), "case": case["name"],
        "kernel_sha256": digest, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "backend": jax.default_backend(), "device": str(jax.devices()[0]), "jax": jax.__version__, "x64": bool(jax.config.jax_enable_x64),
        "case_sha256": hashlib.sha256(Path(case_file).read_bytes()).hexdigest(),
        "elements": ne, "nodes": int(n_no), "element_mm": h, "time_step_s": dt, "steps": int(steps_run), "wall_seconds": round(wall, 1),
        "track_length_run_mm": speed * dt * steps_run, "track_length_asked_mm": travel,
        "melt_pool": {"isotherm_K": t_melt,
                      "width_um": {"median": float(2e3 * np.median(half_widths)), "min": float(2e3 * np.min(half_widths)), "max": float(2e3 * np.max(half_widths))},
                      "depth_um": {"median": float(1e3 * np.median(depths)), "min": float(1e3 * np.min(depths)), "max": float(1e3 * np.max(depths))},
                      "stations_in_the_middle_third": int(middle.sum())},
        "largest_temperature_K": float(peak.max()),
        "energy": {"absorbed_by_the_half_model_J": expected, "source_integrated_J": injected, "stored_at_the_end_J": stored,
                   "source_over_absorbed": injected / expected, "stored_over_source": stored / injected},
        "far_face_temperature_rise_K": {"bottom": float(T[0].max() - t0), "side": float(T[:, -1, :].max() - t0), "ends": float(max(T[:, :, 0].max(), T[:, :, -1].max()) - t0)},
    }
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    np.savez_compressed(out / "fields.npz", top=np.array(top), side=np.array(side), times=np.array(times), x=x, y=y, z=z,
                        peak_top=peak[-1].astype(np.float32), peak_side=peak[:, 0, :].astype(np.float32),
                        centreline_end=T[-1, 0, :].astype(np.float32), laser_x_end=np.float32(x0 + speed * steps_run * dt))
    print(json.dumps({"case": case["name"], "device": report["device"], "nodes": report["nodes"], "steps": report["steps"], "wall_s": report["wall_seconds"],
                      "width_um": report["melt_pool"]["width_um"], "depth_um": report["melt_pool"]["depth_um"], "energy": report["energy"]}))


if __name__ == "__main__":
    main(*sys.argv[1:])
