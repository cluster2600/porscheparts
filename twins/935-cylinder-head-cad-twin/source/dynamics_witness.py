#!/usr/bin/env python3
"""Dynamics tool witness of the 935 head twin (#699): MuJoCo against closed forms.

A witness of the tool, not a run of the head. The head's cam, rocker, spring
and masses are unknown (params/valve-train-parameters.json); every number
below comes from the acceptance file, whose witness inputs are round numbers
chosen for closed forms.

Cases, each against its closed form:

1. Spring-mass free oscillation: f = sqrt(k / m) / (2 pi).
2. Two masses in a chain (ground - k1 - m1 - k2 - m2): the two natural
   frequencies and mode shapes of det(K - w^2 M) = 0, each mode started pure.
3. A flat-faced follower pushed by a preloaded spring onto a cam whose lift is
   simple harmonic, y = e (1 - cos theta): in contact,
   N = F0 + k e (1 - cos theta) + m e w^2 cos theta.
4. The follower leaves the cam when N first reaches zero, at theta = pi:
   w_float = sqrt((F0 + 2 k e) / (m e)). Bisection on the cam speed.

The cam is entered in one of two ways (``--cam``):

- ``rotating``: an eccentric circle turning on a hinge (the first declared
  attempt). It failed: MuJoCo's constraint does not see the acceleration of a
  contact point on a rotating body, so the follower floats wherever the cam
  surface accelerates away from it.
- ``lift-law``: a tappet on a slide joint, put on y(t) at the end of every step
  by a generalised force, carrying the circle that touches the follower (the
  second declared attempt, params/dynamics-witness-attempt-2.json).

Three planted faults must fail the same comparison (a witness that cannot fail
proves nothing). The acceptance, settings and inputs were committed before the
first run; this script only reads them.

Usage (in the locked environment, see dynamics-requirements.lock.txt):

    MUJOCO_GL=disable python -I dynamics_witness.py <acceptance.json> --cam lift-law \\
        --declaration <attempt.json> --output <record.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TWIN = HERE.parent
ROOT = TWIN.parents[1]
LOCK = HERE / "dynamics-requirements.lock.txt"
# the wheel the lock admits for CPython 3.12 on x86_64 Linux (PyPI, 2026-05-27)
WHEEL = {
    "file": "mujoco-3.9.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
    "sha256": "f8c6769ac1463752ff392d8c4d20014e54220112d772e6ccecdf6bcdb6d43e07",
}
TAPPET_MASS_KG = 1.0e6  # second attempt: a contact force of 1 kN moves it by 1e-3 m/s2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


# ------------------------------------------------------------- closed forms
def natural_frequency_hz(m: float, k: float) -> float:
    return math.sqrt(k / m) / (2 * math.pi)


def two_mass_modes(m1: float, k1: float, m2: float, k2: float) -> list[dict]:
    """Frequencies and shapes x2/x1 of ground - k1 - m1 - k2 - m2."""
    # det([[k1 + k2 - l m1, -k2], [-k2, k2 - l m2]]) = 0, l = w^2
    a = m1 * m2
    b = -((k1 + k2) * m2 + k2 * m1)
    c = k1 * k2
    root = math.sqrt(b * b - 4 * a * c)
    modes = []
    for lam in sorted(((-b - root) / (2 * a), (-b + root) / (2 * a))):
        modes.append({"frequency_hz": math.sqrt(lam) / (2 * math.pi),
                      "shape_x2_over_x1": (k1 + k2 - lam * m1) / k2})
    return modes


def shm_lift(e: float, theta: float) -> float:
    return e * (1 - math.cos(theta))


def shm_contact_force(f0: float, k: float, m: float, e: float, omega: float, theta: float) -> float:
    """Follower held on the cam: m y'' = N - F0 - k y, y = e (1 - cos theta)."""
    return f0 + k * e * (1 - math.cos(theta)) + m * e * omega ** 2 * math.cos(theta)


def float_speed_rad_s(f0: float, k: float, m: float, e: float) -> float:
    """N(pi) = F0 + 2 k e - m e w^2 = 0."""
    return math.sqrt((f0 + 2 * k * e) / (m * e))


# ------------------------------------------------------------------ models
def option_xml(settings: dict) -> str:
    g = " ".join(repr(float(v)) for v in settings["gravity_m_per_s2"])
    integrator = settings["integrator"].split()[0]
    return (f'<option timestep="{settings["timestep_s"]!r}" integrator="{integrator}" '
            f'solver="{settings["solver"]}" tolerance="{settings["solver_tolerance"]!r}" '
            f'iterations="{settings["solver_iterations"]}" gravity="{g}"/>')


def spring_mass_xml(settings: dict, m: float, k: float) -> str:
    return f"""<mujoco model="spring-mass">
  {option_xml(settings)}
  <worldbody>
    <body name="mass">
      <joint name="x" type="slide" axis="0 0 1" stiffness="{k!r}" springref="0" damping="0"/>
      <inertial pos="0 0 0" mass="{m!r}" diaginertia="1e-4 1e-4 1e-4"/>
    </body>
  </worldbody>
</mujoco>"""


def two_mass_xml(settings: dict, chain: dict) -> str:
    return f"""<mujoco model="two-mass-chain">
  {option_xml(settings)}
  <worldbody>
    <body name="m1">
      <joint name="q1" type="slide" axis="0 0 1" stiffness="{chain['k1_N_per_m']!r}" springref="0" damping="0"/>
      <inertial pos="0 0 0" mass="{chain['m1_kg']!r}" diaginertia="1e-4 1e-4 1e-4"/>
      <body name="m2">
        <joint name="q2" type="slide" axis="0 0 1" stiffness="{chain['k2_N_per_m']!r}" springref="0" damping="0"/>
        <inertial pos="0 0 0" mass="{chain['m2_kg']!r}" diaginertia="1e-4 1e-4 1e-4"/>
      </body>
    </body>
  </worldbody>
</mujoco>"""


def cam_follower_xml(settings: dict, inputs: dict, cam: str, *, preload: bool = True,
                     contact: dict | None = None) -> str:
    """Follower on a slide joint over a circle that is either turned (rotating) or translated (lift-law)."""
    m = inputs["follower_mass_kg"]
    k = inputs["spring_rate_N_per_m"]
    f0 = inputs["spring_preload_N"] if preload else 0.0
    e = inputs["cam_eccentricity_m"]
    r = inputs["cam_circle_radius_m"]
    c = contact or settings["contact"]
    solref = " ".join(repr(float(v)) for v in c["solref"])
    solimp = " ".join(repr(float(v)) for v in c["solimp"])
    half = 0.005  # half-thickness of the follower's face block
    contact_attrs = (f'condim="{c["condim"]}" solref="{solref}" solimp="{solimp}" '
                     f'margin="{c["margin_m"]!r}" contype="1" conaffinity="1"')
    if cam == "rotating":
        # a circle of radius r whose centre turns at e about the hinge (the y axis);
        # at theta = 0 its centre is at z = -e, so its top is at r - e: zero lift
        cam_body = f"""<body name="cam">
      <joint name="cam" type="hinge" axis="0 1 0" damping="0"/>
      <inertial pos="0 0 0" mass="1" diaginertia="1000 1000 1000"/>
      <geom name="cam" type="sphere" size="{r!r}" pos="0 0 {-e!r}" {contact_attrs}/>
    </body>"""
        face_z = r - e
    elif cam == "lift-law":
        # a tappet carrying the same circle, translated along z by the lift law
        cam_body = f"""<body name="cam">
      <joint name="cam" type="slide" axis="0 0 1" damping="0"/>
      <inertial pos="0 0 0" mass="{TAPPET_MASS_KG!r}" diaginertia="1 1 1"/>
      <geom name="cam" type="sphere" size="{r!r}" pos="0 0 0" {contact_attrs}/>
    </body>"""
        face_z = r
    else:
        raise ValueError(cam)
    return f"""<mujoco model="cam-follower-{cam}">
  <compiler angle="radian"/>
  {option_xml(settings)}
  <worldbody>
    {cam_body}
    <body name="follower" pos="0 0 {face_z + half!r}">
      <joint name="lift" type="slide" axis="0 0 1" stiffness="{k!r}" springref="{-f0 / k!r}" damping="0"/>
      <inertial pos="0 0 0" mass="{m!r}" diaginertia="1e-4 1e-4 1e-4"/>
      <geom name="face" type="box" size="0.03 0.01 {half!r}" {contact_attrs}/>
    </body>
  </worldbody>
</mujoco>"""


# ------------------------------------------------------------------- runs
def upward_crossings(times, values) -> list[float]:
    out = []
    for i in range(1, len(values)):
        if values[i - 1] < 0.0 <= values[i]:
            t0, t1, v0, v1 = times[i - 1], times[i], values[i - 1], values[i]
            out.append(t0 + (t1 - t0) * (-v0) / (v1 - v0))
    return out


def measured_frequency(times, values) -> float:
    ups = upward_crossings(times, values)
    if len(ups) < 2:
        raise RuntimeError("fewer than two upward zero crossings")
    return (len(ups) - 1) / (ups[-1] - ups[0])


def run_free(mj, xml: str, q0: list[float], seconds: float) -> dict:
    model = mj.MjModel.from_xml_string(xml)
    data = mj.MjData(model)
    data.qpos[:] = q0
    mj.mj_forward(model, data)
    n = int(round(seconds / model.opt.timestep))
    times, qs = [0.0] * (n + 1), [list(q0)] + [None] * n
    for i in range(n):
        mj.mj_step(model, data)
        times[i + 1] = data.time
        qs[i + 1] = [float(v) for v in data.qpos]
    return {"times": times, "q": qs}


def cam_run(mj, xml: str, inputs: dict, omega: float, cycles: int, cam: str) -> dict:
    """Step the cam case; pair each contact force with the state it was computed at."""
    import numpy as np

    model = mj.MjModel.from_xml_string(xml)
    data = mj.MjData(model)
    jc = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "cam")
    cam_q, cam_v = model.jnt_qposadr[jc], model.jnt_dofadr[jc]
    lift_q = model.jnt_qposadr[mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "lift")]
    pair = {mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "cam"), mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, "face")}
    e = inputs["cam_eccentricity_m"]
    if cam == "rotating":
        data.qvel[cam_v] = omega
    mj.mj_forward(model, data)
    h = model.opt.timestep
    n = int(round(cycles * 2 * math.pi / omega / h))
    f6 = np.zeros(6)
    t, lift, normal, drive = [], [], [], []
    for i in range(n):
        t.append(data.time)
        lift.append(float(data.qpos[lift_q]))
        if cam == "rotating":
            drive.append(float(data.qvel[cam_v]))  # the cam speed, to check it holds
        else:
            # the force that lands the tappet on y(t) at the end of this step (semi-implicit Euler)
            drive.append(float(data.qpos[cam_q]) - shm_lift(e, omega * data.time))
            v_next = (shm_lift(e, omega * (i + 1) * h) - data.qpos[cam_q]) / h
            data.qfrc_applied[cam_v] = TAPPET_MASS_KG * (v_next - data.qvel[cam_v]) / h
        mj.mj_step(model, data)  # forces of this step belong to the state recorded above
        total = 0.0
        for j in range(data.ncon):
            con = data.contact[j]
            if {int(con.geom1), int(con.geom2)} == pair:
                mj.mj_contactForce(model, data, j, f6)
                total += float(f6[0])
        normal.append(total)
    return {"t": t, "lift": lift, "normal": normal, "drive": drive, "period": 2 * math.pi / omega}


def cam_case_errors(run: dict, inputs: dict, omega: float, preload_in_closed_form: float, cam: str) -> dict:
    """Compare the last full cycle with the closed form at theta = omega t."""
    e, m, k = inputs["cam_eccentricity_m"], inputs["follower_mass_kg"], inputs["spring_rate_N_per_m"]
    start = run["t"][-1] - run["period"]
    lift_err, force_err, n_min, n_cf_min, n_cf_max, n_tool_max = 0.0, 0.0, math.inf, math.inf, 0.0, 0.0
    for t, x, n in zip(run["t"], run["lift"], run["normal"]):
        if t < start:
            continue
        theta = omega * t
        ncf = shm_contact_force(preload_in_closed_form, k, m, e, omega, theta)
        lift_err = max(lift_err, abs(x - shm_lift(e, theta)))
        force_err = max(force_err, abs(n - ncf))
        n_min, n_tool_max = min(n_min, n), max(n_tool_max, n)
        n_cf_min, n_cf_max = min(n_cf_min, ncf), max(n_cf_max, ncf)
    out = {"lift_error_m": lift_err, "lift_error_over_full_lift": lift_err / (2 * e),
           "contact_force_error_N": force_err, "contact_force_error_over_peak": force_err / n_cf_max,
           "closed_form_force_min_N": n_cf_min, "closed_form_force_max_N": n_cf_max,
           "tool_force_min_N": n_min, "tool_force_max_N": n_tool_max}
    if cam == "rotating":
        out["cam_speed_drift_relative"] = max(abs(w - omega) for w in run["drive"]) / omega
    else:
        out["tappet_off_lift_law_over_full_lift"] = max(abs(d) for d in run["drive"]) / (2 * e)
    return out


def float_state(run: dict, inputs: dict, omega: float) -> dict:
    """Over the last two cycles: was contact ever lost, and how far did the follower leave the cam?"""
    e = inputs["cam_eccentricity_m"]
    start = run["t"][-1] - 2 * run["period"]
    lost, gap, first = False, -math.inf, None
    for t, x, n in zip(run["t"], run["lift"], run["normal"]):
        if t < start:
            continue
        if n <= 0.0 and first is None:
            first = (omega * t) % (2 * math.pi)
        lost = lost or n <= 0.0
        gap = max(gap, x - shm_lift(e, omega * t))
    return {"contact_lost": lost, "largest_separation_m": gap, "first_zero_force_cam_angle_rad": first}


# ------------------------------------------------------------------- main
def check(checks: list, name: str, value: float, limit: float) -> bool:
    passed = bool(value <= limit)
    checks.append({"check": name, "value": value, "limit": limit, "passed": passed})
    return passed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("acceptance", type=Path)
    parser.add_argument("--cam", choices=("rotating", "lift-law"), required=True)
    parser.add_argument("--declaration", type=Path, help="the declared attempt this run carries out, if not the first")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    os.environ.setdefault("MUJOCO_GL", "disable")
    import mujoco as mj
    import numpy

    acceptance = json.loads(args.acceptance.read_text())
    if mj.__version__ != acceptance["tool"]["version"]:
        raise SystemExit(f"MuJoCo {mj.__version__} is not the declared {acceptance['tool']['version']}")
    declaration = json.loads(args.declaration.read_text()) if args.declaration else None
    if declaration and declaration["cam"] != args.cam:
        raise SystemExit(f"the declaration is for the {declaration['cam']} cam")
    settings, inputs, accept = acceptance["settings"], acceptance["witness_inputs"], acceptance["accept_when"]
    speeds = inputs["speeds_as_fraction_of_closed_form_float_speed"]
    m, k, f0, e = (inputs["follower_mass_kg"], inputs["spring_rate_N_per_m"], inputs["spring_preload_N"],
                   inputs["cam_eccentricity_m"])
    started = time.monotonic()
    checks, cases, controls, limitations = [], [], [], []

    # 1. spring-mass natural frequency
    fn = natural_frequency_hz(m, k)
    amp = inputs["free_oscillation_amplitude_m"]
    periods = settings["free_oscillation_periods"]
    run = run_free(mj, spring_mass_xml(settings, m, k), [amp], periods / fn)
    f_tool = measured_frequency(run["times"], [q[0] for q in run["q"]])
    last = [abs(q[0]) for q, t in zip(run["q"], run["times"]) if t >= run["times"][-1] - 1 / fn]
    err = abs(f_tool - fn) / fn
    cases.append({"case": "spring-mass natural frequency", "closed_form": {"frequency_hz": fn},
                  "tool": {"frequency_hz": f_tool, "amplitude_last_period_m": max(last)},
                  "relative_error": err, "periods": periods})
    check(checks, "natural frequency within the declared relative error", err,
          accept["natural_frequency_relative_error_within"])

    # 2. two-mass chain, each mode started pure
    chain = inputs["two_mass_chain"]
    for idx, mode in enumerate(two_mass_modes(chain["m1_kg"], chain["k1_N_per_m"], chain["m2_kg"],
                                              chain["k2_N_per_m"]), 1):
        phi = mode["shape_x2_over_x1"]
        run = run_free(mj, two_mass_xml(settings, chain), [amp, (phi - 1) * amp], periods / mode["frequency_hz"])
        x1 = [q[0] for q in run["q"]]
        x2 = [q[0] + q[1] for q in run["q"]]
        f1 = measured_frequency(run["times"], x1)
        f2 = measured_frequency(run["times"], x2)
        scale = max(amp, abs(phi) * amp)
        shape_dev = max(abs(b - phi * a) for a, b in zip(x1, x2)) / scale
        err = max(abs(f1 - mode["frequency_hz"]), abs(f2 - mode["frequency_hz"])) / mode["frequency_hz"]
        cases.append({"case": f"two-mass chain, mode {idx}",
                      "closed_form": {"frequency_hz": mode["frequency_hz"], "shape_x2_over_x1": phi},
                      "tool": {"frequency_hz_from_m1": f1, "frequency_hz_from_m2": f2,
                               "largest_shape_deviation_over_amplitude": shape_dev},
                      "relative_error": err, "periods": periods})
        check(checks, f"two-mass mode {idx}: frequency within the declared relative error", err,
              accept["two_mass_mode_frequency_relative_error_within"])
        check(checks, f"two-mass mode {idx}: stays in its shape", shape_dev,
              accept["two_mass_mode_shape_deviation_within"])

    # 3. cam follower in contact: lift and contact force over the last cycle
    wf = float_speed_rad_s(f0, k, m, e)
    cycles = settings["cycles_per_cam_case"]
    cam = args.cam
    xml = cam_follower_xml(settings, inputs, cam)
    for frac in speeds["contact_force_cases"]:
        omega = frac * wf
        res = cam_case_errors(cam_run(mj, xml, inputs, omega, cycles, cam), inputs, omega, f0, cam)
        tool = {"force_min_N": res["tool_force_min_N"], "force_max_N": res["tool_force_max_N"],
                "largest_lift_error_m": res["lift_error_m"], "largest_force_error_N": res["contact_force_error_N"]}
        drive_key = "cam_speed_drift_relative" if cam == "rotating" else "tappet_off_lift_law_over_full_lift"
        tool[drive_key] = res[drive_key]
        cases.append({"case": f"cam follower at {frac} of the float speed", "cam_speed_rad_s": omega,
                      "closed_form": {"force_min_N": res["closed_form_force_min_N"],
                                      "force_max_N": res["closed_form_force_max_N"], "lift_max_m": 2 * e},
                      "tool": tool})
        check(checks, f"cam at {frac}: follower lift within the declared share of the full lift",
              res["lift_error_over_full_lift"], accept["follower_lift_error_over_full_lift_within"])
        check(checks, f"cam at {frac}: contact force within the declared share of the peak force",
              res["contact_force_error_over_peak"], accept["contact_force_error_over_peak_closed_form_force_within"])
        if cam == "rotating":
            check(checks, f"cam at {frac}: cam speed held", res[drive_key], accept["cam_speed_drift_relative_within"])
        else:
            check(checks, f"cam at {frac}: tappet on the lift law", res[drive_key],
                  declaration["added_check"]["tappet_off_lift_law_over_full_lift_within"])

    # 4. float: the detector must be able to say both things, then bisect
    w_stay = speeds["float_detector_must_stay_in_contact"] * wf
    w_leave = speeds["float_detector_must_separate"] * wf
    stay = float_state(cam_run(mj, xml, inputs, w_stay, cycles, cam), inputs, w_stay)
    leave = float_state(cam_run(mj, xml, inputs, w_leave, cycles, cam), inputs, w_leave)
    checks.append({"check": f"float detector: contact kept at {speeds['float_detector_must_stay_in_contact']} of the float speed",
                   "passed": not stay["contact_lost"], "detail": stay})
    checks.append({"check": f"float detector: contact lost and the follower more than 0.01 mm off the cam at {speeds['float_detector_must_separate']}",
                   "passed": leave["contact_lost"] and leave["largest_separation_m"] > 1e-5, "detail": leave})
    lo, hi = (f * wf for f in speeds["float_bisection_bracket"])
    at_lo = float_state(cam_run(mj, xml, inputs, lo, cycles, cam), inputs, lo)
    at_hi = float_state(cam_run(mj, xml, inputs, hi, cycles, cam), inputs, hi)
    float_case = {"case": "float speed", "closed_form": {"float_speed_rad_s": wf, "float_speed_cam_rpm": wf * 30 / math.pi},
                  "detector": "contact force zero or no contact at any step of the last two cycles"}
    if at_lo["contact_lost"] or not at_hi["contact_lost"]:
        float_case["tool"] = {"bracket_holds": False, "at_bracket_low": at_lo, "at_bracket_high": at_hi}
        checks.append({"check": "float speed: the declared bracket holds the tool's float speed", "passed": False})
    else:
        steps = 0
        while (hi - lo) / wf > 1e-4:
            mid = (lo + hi) / 2
            if float_state(cam_run(mj, xml, inputs, mid, cycles, cam), inputs, mid)["contact_lost"]:
                hi = mid
            else:
                lo = mid
            steps += 1
        w_tool = (lo + hi) / 2
        err = abs(w_tool - wf) / wf
        float_case["tool"] = {"bracket_holds": True, "float_speed_rad_s": w_tool,
                              "float_speed_cam_rpm": w_tool * 30 / math.pi,
                              "bracket_rad_s": [lo, hi], "bisection_steps": steps}
        float_case["relative_error"] = err
        check(checks, "float speed within the declared relative error", err, accept["float_speed_relative_error_within"])
    cases.append(float_case)

    # planted faults: each must fail the comparison that the witness passed
    run = run_free(mj, spring_mass_xml(settings, 1.1 * m, k), [amp], periods / fn)
    err = abs(measured_frequency(run["times"], [q[0] for q in run["q"]]) - fn) / fn
    controls.append({"control": "natural frequency with the model's mass 10% above the declared mass",
                     "value": err, "limit": accept["natural_frequency_relative_error_within"],
                     "caught": err > accept["natural_frequency_relative_error_within"]})
    limit = accept["contact_force_error_over_peak_closed_form_force_within"]
    res = cam_case_errors(cam_run(mj, cam_follower_xml(settings, inputs, cam, preload=False), inputs, w_stay,
                                  cycles, cam), inputs, w_stay, f0, cam)
    controls.append({"control": "cam case at 0.9 of the float speed with the spring preload left out of the model",
                     "value": res["contact_force_error_over_peak"], "limit": limit,
                     "caught": res["contact_force_error_over_peak"] > limit})
    default_contact = dict(settings["contact"], solref=[0.02, 1.0], solimp=[0.9, 0.95, 0.001, 0.5, 2.0])
    res = cam_case_errors(cam_run(mj, cam_follower_xml(settings, inputs, cam, contact=default_contact), inputs,
                                  w_stay, cycles, cam), inputs, w_stay, f0, cam)
    lift_limit = accept["follower_lift_error_over_full_lift_within"]
    controls.append({"control": "cam case at 0.9 of the float speed with MuJoCo's default contact (solref 0.02 s 1, solimp 0.9 0.95 0.001 0.5 2)",
                     "value": {"contact_force_error_over_peak": res["contact_force_error_over_peak"],
                               "lift_error_over_full_lift": res["lift_error_over_full_lift"]},
                     "limit": {"contact_force_error_over_peak": limit, "lift_error_over_full_lift": lift_limit},
                     "caught": res["contact_force_error_over_peak"] > limit or res["lift_error_over_full_lift"] > lift_limit})
    for c in controls:
        checks.append({"check": f"control: {c['control']}: caught", "passed": bool(c["caught"])})

    # what the second attempt keeps from the first: a rotating cam is not admissible
    if cam == "lift-law":
        w = speeds["contact_force_cases"][0] * wf
        rot_xml = cam_follower_xml(settings, inputs, "rotating")
        rot = cam_run(mj, rot_xml, inputs, w, cycles, "rotating")
        state = float_state(rot, inputs, w)
        res = cam_case_errors(rot, inputs, w, f0, "rotating")
        limitations.append({
            "limitation": "a follower on a rotating cam floats in MuJoCo where the cam surface accelerates away from it",
            "cam_speed_rad_s": w, "closed_form_force_min_N": res["closed_form_force_min_N"],
            "tool_force_min_N": res["tool_force_min_N"], "contact_lost": state["contact_lost"],
            "first_zero_force_cam_angle_rad": state["first_zero_force_cam_angle_rad"],
            "largest_separation_m": state["largest_separation_m"],
            "reading": "rerun of the first attempt's rotating cam at 0.5 of the float speed, where the closed form keeps the contact force at 350 N or more"})

    record = {
        "schema": "935-cad-twin-dynamics-witness/1",
        "date": time.strftime("%Y-%m-%d"),
        "attempt": declaration["attempt"] if declaration else 1,
        "cam": cam,
        "scope": ("MuJoCo against closed forms: a spring-mass natural frequency, the two modes of a two-mass "
                  "chain, a preloaded follower on a simple-harmonic cam (lift and contact force) and its float "
                  "speed. A witness of the tool with round witness inputs, not a run of the head; "
                  "docs/TOOLCHAIN.md assigns the tool on it"),
        "tool": {"name": "MuJoCo", "version": mj.__version__, "engine": mj.mj_versionString(),
                 "licence": "Apache-2.0", "maintainer": "Google DeepMind",
                 "source": "https://github.com/google-deepmind/mujoco", "wheel": WHEEL,
                 "lock": rel(LOCK), "lock_sha256": sha256(LOCK),
                 "environment": "private venv built with uv from the lock (--require-hashes); never committed"},
        "acceptance_file": rel(args.acceptance), "acceptance_sha256": sha256(args.acceptance),
        "acceptance": accept, "settings": settings, "witness_inputs": inputs,
        "script": rel(Path(__file__)), "script_sha256": sha256(Path(__file__)),
        "runtime": {"python": platform.python_version(), "numpy": numpy.__version__,
                    "machine": platform.machine(), "system": platform.system(),
                    "wall_time_s": round(time.monotonic() - started, 1)},
        "cases": cases, "controls": controls, "checks": checks,
        "passed": all(c["passed"] for c in checks),
    }
    if declaration:
        record["declaration_file"] = rel(args.declaration)
        record["declaration_sha256"] = sha256(args.declaration)
        record["limitations"] = limitations
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": record["passed"], "checks": [(c["check"], c["passed"]) for c in checks]}, indent=1))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
