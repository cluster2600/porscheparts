"""Independently integrate physical boundary fluxes on the verified uniform grid."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def text(path):
    value = Path(path).read_text()
    assert re.search(r"\bformat\s+ascii\s*;", value[:3000]), path
    return value


def block(value, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*\{", value)
    assert match, name
    start = match.end()
    depth = 1
    for end in range(start, len(value)):
        depth += (value[end] == "{") - (value[end] == "}")
        if depth == 0:
            return value[start:end]
    raise ValueError("Unclosed dictionary")


def values(value, key, count=None, vector=False):
    match = re.search(r"\b" + key + r"\s+(uniform|nonuniform)\s+", value)
    assert match, key
    tail = value[match.end():]
    width = 3 if vector else 1
    if match[1] == "uniform":
        assert count is not None
        raw = tail.split(";", 1)[0].translate(str.maketrans("", "", "()"))
        sample = np.fromstring(raw, sep=" ")
        assert sample.size == width
        result = np.tile(sample, (count, 1))
    else:
        header = re.match(r"List<(scalar|vector)>\s+(\d+)\s*\(", tail)
        assert header
        n = int(header[2])
        assert count is None or n == count, (n, count)
        closing = re.search(r"\n\s*\)\s*;", tail[header.end():])
        assert closing
        raw = tail[header.end():header.end() + closing.start()]
        result = np.fromstring(raw.translate(str.maketrans("", "", "()")), sep=" ")
        assert result.size == n * width
        result = result.reshape(n, width)
    assert np.isfinite(result).all()
    return result if vector else result[:, 0]


def owners(path):
    raw = text(path)
    tail = raw[raw.index("}", raw.index("FoamFile")) + 1:]
    tail = re.sub(r"//[^\n]*", "", tail).strip()
    header = re.match(r"(\d+)\s*\(", tail)
    assert header
    data = np.fromstring(tail[header.end():tail.rindex(")")], sep=" ", dtype=np.int64)
    assert len(data) == int(header[1])
    return data


def patches(path):
    result = {}
    for name, body in re.findall(r"(\w+)\s*\{([^{}]*)\}", text(path)):
        n = re.search(r"\bnFaces\s+(\d+)\s*;", body)
        start = re.search(r"\bstartFace\s+(\d+)\s*;", body)
        if n:
            assert start
            result[name] = (int(start[1]), int(n[1]))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("case", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--time", required=True)
    p.add_argument("--previous", required=True)
    p.add_argument("--ranks", type=int, default=28)
    p.add_argument("--mesh-check", type=Path, required=True)
    a = p.parse_args()
    check = a.mesh_check.read_text()
    assert "Mesh OK." in check
    assert "Minimum face area = 4e-06. Maximum face area = 4e-06." in check
    assert "Min volume = 8e-09. Max volume = 8e-09." in check
    assert "Max aspect ratio = 1 OK." in check
    # Verify parser and flux signs on a one-cell Fourier example.
    assert np.array_equal(values("value nonuniform List<scalar> 2\n(\n1\n2\n);", "value", 2), [1, 2])
    assert np.array_equal(values("value uniform (1 2 3);", "value", 2, True), [[1, 2, 3], [1, 2, 3]])
    rho_cp = 1.177 * 1005.0
    nu, pr, pr_t, pitch = 1.8e-5, .71, .85, .002
    diffusion_factor = pitch ** 2 / (pitch / 2)
    q = rho_cp * (nu / pr) * (400 - 300) * diffusion_factor
    assert np.isclose(q, .011995453521126762, rtol=1e-12)
    physical = {k: {"faces": 0, "volume_flux_m3_s": 0., "advective_heat_out_W": 0., "diffusive_heat_in_W": 0.} for k in ("head", "inlet", "outlet", "farfield")}
    totals = dict(cells=0, u_change_squared=0., u_squared=0., t_change_squared=0., u_change_max=0., t_change_max=0., u_max=0., t_min=float("inf"), t_max=-float("inf"))
    for rank in range(a.ranks):
        case = a.case / f"processor{rank}"
        owner = owners(case / "constant/polyMesh/owner")
        now = case / a.time
        before = case / a.previous
        t_raw, u_raw, nut_raw, phi_raw = [text(now / name) for name in ("T", "U", "nut", "phi")]
        for raw, expected in [(t_raw,[0,0,0,1,0,0,0]),(u_raw,[0,1,-1,0,0,0,0]),(nut_raw,[0,2,-1,0,0,0,0]),(phi_raw,[0,3,-1,0,0,0,0])]:
            dimensions=re.search(r"\bdimensions\s*\[([^]]+)\]\s*;",raw)
            assert dimensions and np.array_equal(np.fromstring(dimensions[1],sep=" ",dtype=int),expected)
        t = values(t_raw, "internalField")
        u = values(u_raw, "internalField", len(t), True)
        prev_t = values(text(before / "T"), "internalField", len(t))
        prev_u = values(text(before / "U"), "internalField", len(t), True)
        du2 = np.sum((u - prev_u) ** 2, axis=1)
        dt2 = (t - prev_t) ** 2
        totals["cells"] += len(t)
        totals["u_change_squared"] += float(du2.sum())
        totals["u_squared"] += float(np.sum(u * u))
        totals["t_change_squared"] += float(dt2.sum())
        totals["u_change_max"] = max(totals["u_change_max"], float(np.sqrt(du2.max())))
        totals["t_change_max"] = max(totals["t_change_max"], float(np.sqrt(dt2.max())))
        totals["u_max"] = max(totals["u_max"], float(np.linalg.norm(u, axis=1).max()))
        totals["t_min"] = min(totals["t_min"], float(t.min()))
        totals["t_max"] = max(totals["t_max"], float(t.max()))
        for name, (start, n) in patches(case / "constant/polyMesh/boundary").items():
            if name.startswith("procBoundary") or n == 0:
                continue
            assert name in physical, name
            ti = t[owner[start:start + n]]
            t_patch = block(block(t_raw, "boundaryField"), name)
            if re.search(r"\btype\s+zeroGradient\s*;", t_patch):
                tb = ti
            else:
                tb = values(t_patch, "value", n)
            nut = values(block(block(nut_raw, "boundaryField"), name), "value", n)
            phi = values(block(block(phi_raw, "boundaryField"), name), "value", n)
            assert float(nut.min()) >= -1e-12
            row = physical[name]
            row["faces"] += n
            row["volume_flux_m3_s"] += float(phi.sum())
            row["advective_heat_out_W"] += float(rho_cp * np.sum(phi * (tb - 300)))
            row["diffusive_heat_in_W"] += float(rho_cp * np.sum((nu / pr + nut / pr_t) * (tb - ti)) * diffusion_factor)
    assert totals["cells"] == 6593936
    q_in = sum(r["diffusive_heat_in_W"] for r in physical.values())
    q_out = sum(r["advective_heat_out_W"] for r in physical.values())
    mass_error = abs(sum(r["volume_flux_m3_s"] for r in physical.values())) / abs(physical["inlet"]["volume_flux_m3_s"])
    heat_error = abs(q_in - q_out) / max(abs(q_out), abs(physical["head"]["diffusive_heat_in_W"]))
    u_change = np.sqrt(totals["u_change_squared"] / totals["u_squared"])
    t_change = np.sqrt(totals["t_change_squared"] / totals["cells"]) / 100
    gates = {"mass_balance_below_1e_minus_3": mass_error < 1e-3, "heat_balance_below_1e_minus_2": heat_error < 1e-2, "velocity_l2_change_below_1e_minus_3": u_change < 1e-3, "temperature_rms_change_over_100K_below_1e_minus_3": t_change < 1e-3, "temperature_bounds_300_to_400K": totals["t_min"] >= 300 - 1e-6 and totals["t_max"] <= 400 + 1e-6}
    result = {"scope": "Steady external-air/passive-temperature hypothesis; not engine CHT", "iteration": a.time, "previous_iteration": a.previous, "iteration_is_physical_time": False, "rho_kg_m3": 1.177, "cp_J_kg_K": 1005, "pitch_m": pitch, "nu_m2_s": nu, "Pr": pr, "Pr_t": pr_t, "mesh_check_sha256": hashlib.sha256(a.mesh_check.read_bytes()).hexdigest(), "physical_boundary_fluxes": physical, "relative_volume_flux_imbalance": mass_error, "relative_heat_imbalance": heat_error, "velocity_relative_l2_change": float(u_change), "temperature_rms_change_over_100K": float(t_change), "field_statistics": totals, "gates": {k: bool(v) for k, v in gates.items()}, "numerical_gates_passed": all(gates.values()), "spatial_convergence_established": False, "engine_qualified": False}
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
