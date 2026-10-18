"""Record numerical CFD diagnostics and export actual cell-centre fields in explicit units."""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("flow_case_inputs", SOURCE / "build_flow_case.py")
case_inputs = importlib.util.module_from_spec(spec); spec.loader.exec_module(case_inputs)
spec = importlib.util.spec_from_file_location("poiseuille_postprocessing", ROOT / "outils/benchmarks/openfoam-poiseuille-f25/analyze_results.py")
benchmark = importlib.util.module_from_spec(spec); spec.loader.exec_module(benchmark)


def patch_flux(path, name, expected_faces):
    text = path.read_text()
    if not re.search(r"dimensions\s*\[0\s+3\s+-1\s+0\s+0\s+0\s+0\]", text):
        raise ValueError("Expected volumetric phi in m3/s")
    match = re.search(r"\b" + re.escape(name) + r"\s*\{([^}]+)\}", text)
    if not match:
        raise ValueError("Missing flux patch: " + name)
    body = match[1]
    values = re.search(r"value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;", body, re.DOTALL)
    if values:
        entries = [float(v) for v in values[2].split()]
        if len(entries) != int(values[1]) or len(entries) != expected_faces or not all(map(math.isfinite, entries)):
            raise ValueError("Flux face count or values invalid")
        return sum(entries)
    uniform = re.search(r"value\s+uniform\s+(" + benchmark.FLOAT_PATTERN + r")\s*;", body)
    if uniform:
        value = float(uniform[1]) * expected_faces
        if not math.isfinite(value):
            raise ValueError("Nonfinite uniform flux")
        return value
    raise ValueError("Unsupported flux patch values")


def analyze(case):
    import numpy as np
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    inputs = json.loads((case / "case-report.json").read_text())
    for name, digest in inputs["case_hashes"].items():
        if case_inputs.sha(case / name) != digest:
            raise ValueError("Solver input changed: " + name)
    expected_cells = inputs["cells"]
    if expected_cells is None:
        receipt = json.loads((case / "mesh-report.json").read_text())
        for name, digest in receipt["source_hashes"].items():
            path = SOURCE / name if name == "accept_mesh.py" else case / name
            if case_inputs.sha(path) != digest:
                raise ValueError("Accepted mesh changed: " + name)
        expected_cells = receipt["cells"]
    mesh = benchmark.read_check_mesh(case, expected_cells)
    solver = benchmark.read_solver_log(case)
    if not mesh["passed"] or not mesh["cell_count_matches"] or not solver["completed"] or not solver["openfoam_13_observed"]:
        raise ValueError("Missing successful OpenFOAM 13 execution/mesh checks")
    rho, q = inputs["water_density_kg_m3"], inputs["flow_m3_s"]
    log = (case / "log.simpleFoam").read_text()
    converged = "SIMPLE solution converged" in log
    times = re.findall(r"^Time = (" + benchmark.FLOAT_PATTERN + r")(?:s)?$", log, re.MULTILINE)
    if not times:
        raise ValueError("No completed solver iteration to compare with saved fields")
    reader = vtk.vtkOpenFOAMReader(); reader.SetFileName(str(case / "case.foam"))
    reader.SetUse64BitFloats(True)
    reader.UpdateInformation(); reader.SetTimeValue(float(benchmark.latest_time_dir(case).name))
    reader.EnableAllCellArrays(); reader.DisableAllPointArrays(); reader.Update()
    data = reader.GetOutput()
    internal = data.GetBlock(0)
    if not isinstance(internal, vtk.vtkUnstructuredGrid) or internal.GetNumberOfCells() != expected_cells:
        raise ValueError("Unexpected OpenFOAM internal mesh")
    latest = benchmark.latest_time_dir(case)
    patches = {}
    iterator = data.GetBlock(1).NewIterator(); iterator.VisitOnlyLeavesOn(); iterator.InitTraversal()
    while not iterator.IsDoneWithTraversal():
        name = iterator.GetCurrentMetaData().Get(vtk.vtkCompositeDataSet.NAME())
        if name in ("inlet", "outlet"):
            poly = iterator.GetCurrentDataObject()
            area_filter = vtk.vtkCellSizeFilter(); area_filter.SetInputData(poly); area_filter.ComputeAreaOn(); area_filter.Update()
            areas = vtk_to_numpy(area_filter.GetOutput().GetCellData().GetArray("Area"))
            pressure = vtk_to_numpy(poly.GetCellData().GetArray("p"))
            patches[name] = dict(faces=poly.GetNumberOfCells(), area_m2=float(areas.sum()),
                                 p=float(np.dot(areas, pressure) / areas.sum()))
        iterator.GoToNextItem()
    if set(patches) != {"inlet", "outlet"}:
        raise ValueError("Missing final pressure patches")
    inlet = patch_flux(latest / "phi", "inlet", patches["inlet"]["faces"])
    outlet = patch_flux(latest / "phi", "outlet", patches["outlet"]["faces"])
    p_in, p_out = patches["inlet"]["p"], patches["outlet"]["p"]
    imbalance, flow_error = abs(inlet + outlet) / q, abs(-inlet - q) / q
    drop_pa = (p_in - p_out) * rho
    if not all(math.isfinite(v) for v in (inlet, outlet, p_in, p_out, drop_pa)):
        raise ValueError("Nonfinite solver result")
    saved_final_iteration = bool(times) and float(latest.name) == float(times[-1])
    centre_filter = vtk.vtkCellCenters(); centre_filter.SetInputData(internal); centre_filter.Update()
    centres = vtk_to_numpy(centre_filter.GetOutput().GetPoints().GetData()) * 1000
    u = vtk_to_numpy(internal.GetCellData().GetArray("U"))
    p = vtk_to_numpy(internal.GetCellData().GetArray("p")) * rho
    if u.shape != centres.shape or p.shape != (len(centres),) or not all(np.isfinite(v).all() for v in (centres, u, p)):
        raise ValueError("Invalid cell-centre physics fields")
    sampling = dict(method="CFD cell centres", candidate_samples=len(centres), located_samples=len(centres))
    if "sampling_grid" in inputs:
        path = case / inputs["sampling_grid"]
        if case_inputs.sha(path) != inputs["sampling_grid_sha256"]:
            raise ValueError("Resampling locations changed")
        grid = json.loads(path.read_text())
        target = np.asarray(grid["origin_mm"]) + (np.asarray(grid["cells"]) + .5) * grid["voxel_mm"]
        locator = vtk.vtkStaticCellLocator(); locator.SetDataSet(internal); locator.BuildLocator()
        located = np.array([locator.FindCell(point * .001) for point in target])
        valid = located >= 0
        sampling = dict(method="piecewise-constant containing-tetrahedron value on native 1 mm sample grid",
                        candidate_samples=len(target), located_samples=int(valid.sum()),
                        outside_analysis_mesh_samples=int((~valid).sum()),
                        outside_samples_are_missing_not_filled=True, conservative_resampling=False)
        centres, u, p = target[valid], u[located[valid]], p[located[valid]]
    if not np.allclose(centres * 2, np.rint(centres * 2), atol=1e-4, rtol=0):
        raise ValueError("Sample positions do not align with the 0.5 mm VDB field frame")
    field_path = case / "cell-fields-mm-pa-m_s.csv"
    if field_path.exists() or (case / "flow-report.json").exists():
        raise ValueError("Do not replace prior analysis results")
    with field_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerow(("x_mm", "y_mm", "z_mm", "pressure_gauge_pa", "ux_m_s", "uy_m_s", "uz_m_s"))
        writer.writerows(np.column_stack((centres, p, u)))
    report = dict(status="numerical_isothermal_rans_diagnostic_not_physical_qualification",
        grid_mm=inputs["grid_mm"], cells=expected_cells, check_mesh=mesh,
        solver=solver, simple_residual_control_satisfied=converged,
        last_iteration=float(times[-1]), last_written_iteration=float(benchmark.latest_time_dir(case).name),
        inlet_flow_m3_s=inlet, outlet_flow_m3_s=outlet,
        relative_flow_imbalance=imbalance, relative_inlet_flow_error=flow_error,
        inlet_mean_kinematic_pressure_m2_s2=p_in, outlet_mean_kinematic_pressure_m2_s2=p_out,
        pressure_drop_pa=drop_pa, hydraulic_power_w=drop_pa * q,
        maximum_cell_speed_m_s=float(np.linalg.norm(u, axis=1).max()),
        final_field_snapshot_matches_completed_iteration=saved_final_iteration,
        boundary_patch_metrics=patches,
        numerical_flow_screen_passed=converged and saved_final_iteration and imbalance < 1e-5 and flow_error < 1e-6 and drop_pa > 0,
        source_hashes={p.name: case_inputs.sha(p) for p in (Path(__file__), SOURCE / "build_flow_case.py",
            ROOT / "outils/benchmarks/openfoam-poiseuille-f25/analyze_results.py", case / "case-report.json")},
        log_hashes={p.name: case_inputs.sha(p) for p in case.glob("log.*")},
        final_field_hashes={name: case_inputs.sha(latest / name) for name in ("p", "U", "phi")},
        cell_fields=dict(file=field_path.name, sha256=case_inputs.sha(field_path), count=len(centres),
                         coordinates="mm", velocity="m/s", pressure="Pa gauge; OpenFOAM kinematic p multiplied by rho",
                         sampling=sampling),
        hydraulic_performance_validated=False, thermal_performance_validated=False,
        manufacturing_authorized=False)
    (case / "flow-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("case", type=Path)
    args = parser.parse_args(); analyze(args.case.resolve())
