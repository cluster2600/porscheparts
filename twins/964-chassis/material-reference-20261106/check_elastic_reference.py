"""Check a documentary in-plane elastic reference, never a vehicle or cure model."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np


HELPER = "twins/964-chassis/fea/laminate.py"
HELPER_SHA = "c2c3358331ecdf28877ceccdd06dad0a89de2560de8162bf167e04cba7d9598b"
INPUT_ID = "CAM-RP-2009-015-RevB-Table2-1-RTD-measured"
MSI_TO_MPA = 4.4482216152605 / 0.0254**2
EPS = 1e-11


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values(data):
    if data["source_id"] != INPUT_ID or data["stress_unit"] != "Msi":
        raise ValueError("Unsupported source basis or units")
    keys = ("E1_tension", "E2_tension", "G12_shear", "nu12_tension")
    result = [data[k] for k in keys]
    if not all(type(v) in (float, int) and math.isfinite(v) for v in result):
        raise ValueError("Missing or nonfinite reference constant")
    e1, e2, g, nu = result
    if min(e1, e2, g) <= 0 or 1 - nu**2 * e2/e1 <= 0:
        raise ValueError("Reference compliance is not positive definite")
    return e1*MSI_TO_MPA, e2*MSI_TO_MPA, g*MSI_TO_MPA, nu


def rotate_tensor(q, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    rotation = np.array([[c, -s], [s, c]])
    columns = []
    for ex, ey, gamma in np.eye(3):
        strain = rotation.T @ np.array([[ex, gamma/2], [gamma/2, ey]]) @ rotation
        sx, sy, tau = q @ [strain[0, 0], strain[1, 1], 2*strain[0, 1]]
        stress = rotation @ np.array([[sx, tau], [tau, sy]]) @ rotation.T
        columns.append([stress[0, 0], stress[1, 1], stress[0, 1]])
    return np.array(columns).T


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--inputs-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module_path = args.repo / HELPER
    if sha(module_path) != HELPER_SHA or sha(args.inputs) != args.inputs_sha256:
        raise ValueError("Input or existing implementation hash changed")
    data = json.loads(args.inputs.read_text())
    e1, e2, g12, nu12 = values(data)
    spec = importlib.util.spec_from_file_location("existing_laminate", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    q = module.reduced_stiffness(e1, e2, g12, nu12)
    compliance = np.array([[1/e1, -nu12/e1, 0], [-nu12/e1, 1/e2, 0], [0, 0, 1/g12]])
    q_error = float(np.max(np.abs(q - np.linalg.inv(compliance)))/np.max(np.abs(q)))
    angles = [0, 45, -45, 90]
    averaged = sum(rotate_tensor(q, a) for a in angles)/len(angles)
    effective = np.linalg.inv(averaged)
    independent = np.array([1/effective[0, 0], -effective[0, 1]/effective[0, 0], 1/effective[2, 2]])
    existing = module.quasi_isotropic(q)
    reference = np.array([existing["E"], existing["nu"], existing["G"]])
    errors = np.abs(independent - reference)/np.maximum(np.abs(reference), 1e-300)
    assert q_error < EPS and np.max(errors) < EPS
    assert np.min(np.linalg.eigvalsh(q)) > 0 and np.min(np.linalg.eigvalsh(averaged)) > 0
    assert abs(averaged[0, 0]-averaged[1, 1])/averaged[0, 0] < EPS
    assert max(abs(averaged[0, 2]), abs(averaged[1, 2]))/averaged[0, 0] < EPS
    assert abs(reference[2] - reference[0]/(2*(1+reference[1])))/reference[2] < EPS
    iso_e, iso_nu = 12345.0, 0.29
    iso = module.reduced_stiffness(iso_e, iso_e, iso_e/(2*(1+iso_nu)), iso_nu)
    for angle in (0, 17, 45, 90):
        assert np.max(np.abs(rotate_tensor(iso, angle)-iso))/iso_e < EPS
    for key, bad in (("stress_unit", "MPa"), ("E2_tension", None), ("G12_shear", -1)):
        try:
            values(dict(data, **{key: bad}))
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid reference accepted")
    assert sha(module_path) == HELPER_SHA and sha(args.inputs) == args.inputs_sha256
    report = {"classification": "source_fed_2D_elastic_implementation_check_not_structural_qualification",
              "inputs_sha256": args.inputs_sha256, "existing_helper_sha256": HELPER_SHA,
              "executed_script_sha256": sha(Path(__file__)), "python": sys.version.split()[0], "numpy": np.__version__,
              "units": "MPa; engineering shear strain gamma_xy", "Msi_to_MPa": MSI_TO_MPA,
              "Q_MPa": q.tolist(), "A_divided_by_total_thickness_MPa": averaged.tolist(),
              "equal_orientation_fractions_deg": angles, "effective_E_MPa": float(reference[0]),
              "effective_nu": float(reference[1]), "effective_G_MPa": float(reference[2]),
              "compliance_inverse_relative_error": q_error, "independent_rotation_relative_errors": errors.tolist(),
              "numerical_relative_limit_not_material_uncertainty": EPS, "self_checks_passed": True,
              "scope": "Equal fractions at 0/+45/-45/90; normalized in-plane stiffness only. No physical ply thickness, bending D matrix, 3D constitutive law, failure, joint, cure, mould or vehicle model.",
              "material_allowables_or_process_qualified": False, "physical_validation": False,
              "coque_or_native_final_twin_validated": False, "manufacturing_authorized": False}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "result.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: report[k] for k in ("effective_E_MPa", "effective_nu", "effective_G_MPa", "self_checks_passed")}))


if __name__ == "__main__":
    main()
