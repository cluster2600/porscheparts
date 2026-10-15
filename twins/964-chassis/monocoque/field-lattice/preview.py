"""Read-only raw STL screening and a field/probe preview; never repair the meshes."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "twins/m64-cylinder-head/source/picogk-local-junction"))
from audit_surface_topology import audit_arrays, load_binary_stl  # noqa: E402


def inspect(samples, native, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from matplotlib.patches import Rectangle

    rows = np.array(json.loads(Path(samples).read_text())["rows"])
    report = json.loads((Path(native) / "report.json").read_text())
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    audits = {}
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(16, 6), layout="constrained")
    ax = fig.add_subplot(131)
    demand = np.maximum(rows[:, 3]/rows[:, 3].max(), rows[:, 4]/rows[:, 4].max())
    view = ax.scatter(rows[:, 0], rows[:, 2], s=1, c=demand, cmap="inferno", vmin=0, vmax=1, rasterized=True)
    low, high = np.array(report["study_min_mm"]), np.array(report["study_max_mm"])
    ax.add_patch(Rectangle(low[[0, 2]], *(high-low)[[0, 2]], fill=False, color="cyan", linewidth=1.5))
    ax.set(xlabel="F0 global X (mm)", ylabel="F0 global Z (mm)", title="Original shell demand | side projection")
    ax.set_aspect("equal")
    fig.colorbar(view, ax=ax, shrink=.5, label="max of separately normalized load cases")
    origin = (low+high)/2
    for index, name in enumerate(("uniform_probe", "graded_probe"), 2):
        triangles, digest = load_binary_stl(Path(native) / (name+".stl"))
        vertices, inverse = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
        audit = audit_arrays(vertices, inverse.reshape(-1, 3))
        assert audit["faces_original_and_retained"] == len(triangles)
        audits[name] = {"stl_sha256": digest, **audit}
        ax = fig.add_subplot(1, 3, index, projection="3d")
        mesh = Poly3DCollection(triangles-origin, facecolors="#4fbbc8" if index == 2 else "#ee9c45",
                                edgecolor="none", shade=True, lightsource=matplotlib.colors.LightSource(315, 45))
        ax.add_collection3d(mesh)
        ax.set(xlim=(-26,26), ylim=(-26,26), zlim=(-26,26), xlabel="local X (mm)",
               ylabel="local Y (mm)", zlabel="local Z (mm)",
               title="Uniform | diameter 2 mm" if index == 2 else "Field-driven | diameters 3.16–6 mm")
        ax.set_box_aspect((1,1,1))
        ax.view_init(elev=18, azim=-65)
    fig.suptitle("964 F0 | Native ShapeKernel + LatticeLibrary + VDB\nLocal geometric probes — NOT fitted cores or validated CFRP structures", fontsize=14)
    fig.savefig(out / "preview.png", dpi=140)
    plt.close(fig)
    (out / "topology.json").write_text(json.dumps(audits, indent=2, allow_nan=False)+"\n")
    return audits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path)
    parser.add_argument("native", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = inspect(args.samples, args.native, args.output)
    print(json.dumps({k: {n: v[n] for n in ("faces_original_and_retained", "exact_zero_area_faces",
        "edge_connected_face_components", "closed_oriented_combinatorial_surface_screen_pass")} for k, v in result.items()}, indent=2))
