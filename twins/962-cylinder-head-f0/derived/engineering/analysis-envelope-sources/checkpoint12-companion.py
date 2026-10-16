"""Read-only companion audit for the final complete 12 GiB envelope checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import certify_fixed_face as exact
import recover_head_checkpoint as recovery
from mesh_head import ROOT, FAMILY, sha, save

TRIAL = ROOT / "work/962-engineering/analysis-envelope-025-003"
CONTRACT_SHA256 = "a045d3b509f7c33382c667b415245a4c1233bb5ceb74e89526798681cf8c7719"


def require_stopped_bound_trial(receipt):
    state = receipt.get("container_state")
    if (receipt.get("contract_sha256") != CONTRACT_SHA256
            or receipt.get("source_import_exact") is not True
            or receipt.get("bound_inputs_unchanged") is not True
            or type(receipt.get("native_returncode")) is not int
            or not isinstance(state, dict) or state.get("Running") is not False):
        raise ValueError("A stopped, source-exact, unchanged 12 GiB trial is required")


def run(output):
    trial_receipt = TRIAL / "receipt.json"
    require_stopped_bound_trial(json.loads(trial_receipt.read_text()))
    inputs = [trial_receipt, Path(__file__), Path(recovery.__file__),
              Path(exact.__file__), FAMILY / "source/gmsh_sicn_reference.json"]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    original_trial = recovery.TRIAL
    try:
        # Reuse the frozen audit implementation; bind this explicit override separately.
        recovery.TRIAL = TRIAL
        result = recovery.run(output)
    finally:
        recovery.TRIAL = original_trial
    (output / "companion-source.py").write_bytes(Path(__file__).read_bytes())
    (output / "exact-proof-source.py").write_bytes(Path(exact.__file__).read_bytes())
    report = dict(schema="962-envelope12GiB-checkpoint-companion/v1",
        status="checkpoint_audit_finished_independent_admission_pending", input_hashes=pins,
        explicit_frozen_recovery_module_override=dict(name="TRIAL", value=str(TRIAL.relative_to(ROOT))),
        recovery_receipt_sha256=sha(output / "receipt.json"), recovery_returncode=result,
        companion_source_sha256=sha(output / "companion-source.py"),
        exact_proof_source_sha256=sha(output / "exact-proof-source.py"),
        qualification=dict(solver_admission_established=False, engineering_accepted=False,
            strength_validated=False, manufacturing_authorized=False))
    audited = json.loads((output / "receipt.json").read_text())
    if (result == 0 and audited.get("all_source_inputs_unchanged") is True
            and audited.get("all_native_artifacts_unchanged") is True):
        data = np.load(output / "analysis-surface.npz")
        points, faces = data["points_mm"], data["triangles"]
        xyz = points[faces]
        u, v = xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]
        cross = np.cross(u, v)
        c = np.einsum("ij,ij->i", cross, cross)
        s = (np.einsum("ij,ij->i", u, u)+np.einsum("ij,ij->i", v, v)
             +np.einsum("ij,ij->i", v-u, v-u))
        # Floating search only selects a face; the decision uses exact rational arithmetic.
        index = int(np.argmin(c/s**2))
        coords = points[faces[index]]
        proof = exact.certificate(coords.tolist())
        report.update(selected_face_index_zero_based=index,
            selected_node_indices_zero_based=faces[index].tolist(), coordinates_mm=coords.tolist(),
            coordinate_binary64_hex=[[float(x).hex() for x in row] for row in coords],
            coordinate_bytes_sha256=hashlib.sha256(np.asarray(coords, dtype="<f8").tobytes()).hexdigest(),
            analysis_surface_npz_sha256=sha(output / "analysis-surface.npz"), certificate=proof)
        if proof["no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1"]:
            report["status"] = "exact_fixed_face_quality_rejection_no_solver_admission"
    else:
        report["status"] = "checkpoint_audit_failed_no_admission"
    report["all_companion_inputs_unchanged"] = all(sha(ROOT/p) == h for p, h in pins.items())
    if not report["all_companion_inputs_unchanged"]:
        report["status"] = "companion_input_drift_no_admission"
    target = output / "companion-receipt.json"
    if target.exists():
        raise ValueError("Companion receipt must be new")
    save(target, report)
    print(json.dumps({k: report.get(k) for k in ["status", "selected_face_index_zero_based",
        "all_companion_inputs_unchanged"]}))
    return result if report["all_companion_inputs_unchanged"] else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
