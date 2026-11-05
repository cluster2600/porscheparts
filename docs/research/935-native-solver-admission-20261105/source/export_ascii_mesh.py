"""Write MSH 2.2 ASCII at 17 digits and prove exact native array readback."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import gmsh
import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "input-report", "native-reader", "inspector", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--mode", choices=("precision-control", "head"), required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    assert gmsh.__version__ == "4.12.1"
    assert sha(args.native_reader) == "e9a4b8cb0805ddaa779f307ba7c0b89c17a679a3915028487a28879a73ecf484"
    assert sha(args.inspector) == "b0810ac21b35654556dce18ef022f6d4ca8f30a847223c5d566188eab82f4e71"
    report = json.loads(args.input_report.read_text())
    assert report["mesh_sha256"] == sha(args.mesh) and report["all_cells_positive_for_stored_binary_coordinates"]
    assert report["actual_complete_boundary_and_orientation_exact"] and report["all_internal_faces_oppositely_oriented"]
    modules = []
    for name, path in (("retained_ascii_reader", args.native_reader), ("retained_ascii_exact", args.inspector)):
        spec = importlib.util.spec_from_file_location(name, path)
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        modules.append(value)
    reader, exact = modules
    with np.load(args.mesh, allow_pickle=False) as data:
        nodes, cells, boundary = data["nodes"].copy(), data["tets"], data["boundary"]
    fixture = None
    if args.mode == "precision-control":
        assert sha(args.mesh) == "a8f2d8cbc8332af366dcca282d3385caf0076ea5533802f8da34b30b7ef8dfe5"
        assert nodes.shape == (5, 3) and cells.shape == (2, 4)
        nodes[:, 0] += 100
        nodes[0, 0] = np.nextafter(100., np.inf)
        assert float(format(nodes[0, 0], ".16g")) != nodes[0, 0]
        assert float(format(nodes[0, 0], ".17g")) == nodes[0, 0]
        volume = sum((exact.exact_determinant(nodes[cell]) / 6 for cell in cells), Fraction(0))
        assert all(exact.exact_determinant(nodes[cell]) > 0 for cell in cells)
        assert volume == Fraction(2, 3) * (1 + Fraction(1, 2**46))
        reference = args.output / "precision-control.npz"
        np.savez_compressed(reference, nodes=nodes, tets=cells, boundary=boundary)
        fixture = {"synthetic_only": True, "sixteen_digit_loss_witness": True,
                   "definition": "Original five-point synthetic bipyramid shifted in x; apex x set to nextafter(100,+inf)",
                   "reference_sha256": sha(reference), "exact_analytic_volume": str(volume)}
    else:
        assert sha(args.mesh) == "233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e"
    plan = {"source_sha256": sha(Path(__file__)), "input_sha256": sha(args.mesh), "input_report_sha256": sha(args.input_report),
            "format": "MSH 2.2 ASCII", "coordinate_digits": 17, "mode": args.mode,
            "field_or_physical_admission": False, "new_paid_compute_usd": 0}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    mesh = args.output / "solid.msh"
    with mesh.open("x") as stream:
        stream.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n2\n2 2 "source_boundary_unclassified"\n3 1 "hypothetical_solid"\n$EndPhysicalNames\n$Nodes\n')
        stream.write(str(len(nodes)) + "\n")
        for i, (x, y, z) in enumerate(nodes):
            stream.write(f"{i + 1} {x:.17g} {y:.17g} {z:.17g}\n")
        stream.write("$EndNodes\n$Elements\n" + str(len(boundary) + len(cells)) + "\n")
        for i, (a, b, c) in enumerate(boundary):
            stream.write(f"{i + 1} 2 2 2 1 {int(a) + 1} {int(b) + 1} {int(c) + 1}\n")
        for i, (a, b, c, d) in enumerate(cells):
            stream.write(f"{len(boundary) + i + 1} 4 2 1 1 {int(a) + 1} {int(b) + 1} {int(c) + 1} {int(d) + 1}\n")
        stream.write("$EndElements\n")
    gmsh.initialize()
    gmsh.open(str(mesh))
    recovered = reader.arrays()
    for expected, actual in zip((nodes, cells, boundary), recovered[:3]):
        assert np.array_equal(expected, actual), "ASCII native readback changed source arrays"
    gmsh.finalize()
    result = {**plan, "msh_sha256": sha(mesh), "msh_bytes": mesh.stat().st_size,
              "all_native_readback_coordinates_cells_and_boundary_exact": True,
              "complete_native_node_label_mapping_verified": True, "tetrahedra": len(cells), "nodes": len(nodes),
              "precision_fixture": fixture, "native_quality_gate_unchanged": True,
              "case_specific_solver_admission": False, "physics_admitted": False, "manufacturing_qualified": False,
              "seconds": time.monotonic() - started}
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
