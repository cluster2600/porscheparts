"""Render the generated support surfaces and an actual 60 micrometre layer."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from vispy import scene
import trimesh


def render(directory, layer_index=None, output=None):
    directory = Path(directory).resolve()
    destination = Path(output).resolve() if output is not None else directory
    if output is not None:
        destination.mkdir(parents=True, exist_ok=False)
    report_path = directory / "report.json"
    partial = not report_path.exists()
    report = json.loads((directory / ("partial.json" if partial else "report.json")).read_text())
    label = "TÉMOIN PARTIEL · " if partial else ""
    for name, expected in report["outputs_sha256"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Output hash mismatch: {name}")
    part = trimesh.load_mesh(directory / "part-build.stl", process=False)
    plate = trimesh.load_mesh(directory / "plate.stl", process=False)
    supports = []
    for path in sorted(directory.glob("support-*.npz")):
        with np.load(path, allow_pickle=False) as data:
            supports.append(trimesh.Trimesh(vertices=data["vertices"], faces=data["faces"], process=False))
    canvas = scene.SceneCanvas(show=False, size=(1600, 1000), bgcolor="white")
    view = canvas.central_widget.add_view()
    view.camera = scene.cameras.TurntableCamera(fov=0, elevation=25, azimuth=20)
    visuals = []
    for mesh, color in [(plate, "#bcc4cd"), (part, "#2c6e97")] + [(s, "#dc8844") for s in supports]:
        visuals.append(scene.visuals.Mesh(vertices=mesh.vertices, faces=mesh.faces,
                        color=color, shading="smooth", parent=view.scene))
    view.camera.set_range()
    whole = canvas.render()
    contact = supports[0].vertices[np.argmax(supports[0].vertices[:, 2])]
    for visual in visuals:
        visual.visible = False
    support = supports[0]
    triangles = support.vertices[support.faces]
    lower, upper = contact - [7, 7, 4], contact + [7, 7, 1]
    selection = np.all(triangles.max(axis=1) >= lower, axis=1) & np.all(triangles.min(axis=1) <= upper, axis=1)
    scene.visuals.Mesh(vertices=support.vertices, faces=support.faces[selection],
                       color="#dc8844", shading="smooth", parent=view.scene)
    view.camera.elevation, view.camera.azimuth = 8, 0
    view.camera.set_range(x=(contact[0]-7, contact[0]+7), y=(contact[1]-7, contact[1]+7),
                          z=(contact[2]-4, contact[2]+1), margin=0)
    teeth = canvas.render()
    canvas.close()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    for filename, pixels, title in [
        ("build-supports.png", whole, "Supports PySLM calculés · pièce à plat · rotation de 45° dans le plan"),
        ("support-teeth.png", teeth, "Dents calculées, support seul · pénétration nominale de 0,2 mm"),
    ]:
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.imshow(pixels)
        ax.axis("off")
        ax.set_title(label + title)
        handles = [Patch(color="#dc8844", label="Surfaces de support dentées")]
        if filename == "build-supports.png":
            handles += [Patch(color="#2c6e97", label="Pièce"), Patch(color="#bcc4cd", label="Plaque")]
        fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False)
        fig.savefig(destination / filename, dpi=130, bbox_inches="tight")
        plt.close(fig)
    if layer_index is None:
        with (directory / "layers.csv").open() as stream:
            row = max(csv.DictReader(stream), key=lambda r: float(r["part_area_mm2"]))
        index = int(row["layer"])
    else:
        index = layer_index
    with np.load(directory / "layers" / f"layer-{index:05d}.npz", allow_pickle=False) as data:
        fig, axes = plt.subplots(1, 2, figsize=(18, 9))
        for ax in axes:
            ax.add_collection(LineCollection(data["support_scan_segments_mm"], colors="#a85c21", linewidths=0.55))
            ax.add_collection(LineCollection(data["part_hatch_segments_mm"], colors="#719cb8", linewidths=0.2))
            for name, offset_name, color in [
                ("part_boundary_points_mm", "part_boundary_offsets", "black"),
                ("part_scan_contour_points_mm", "part_scan_contour_offsets", "#b22b35"),
            ]:
                points, offsets = data[name], data[offset_name]
                for start, end in zip(offsets[:-1], offsets[1:]):
                    ax.plot(points[start:end, 0], points[start:end, 1], color=color, linewidth=0.5)
            ax.autoscale()
            ax.set_aspect("equal")
            ax.set_xlabel("x [mm]")
            ax.set_ylabel("y [mm]")
        axes[0].set_title("Couche calculée entière", pad=12)
        axes[1].set(xlim=(-75, 75), ylim=(-75, 75), title="Détail central : contours et vecteurs")
        axes[1].title.set_y(1.01)
        fig.suptitle(label + f"Couche {index} · z = {float(data['z_mm']):.3f} mm · épaisseur de couche : 60 µm", y=0.985)
        legend = [("black", "Section brute"), ("#b22b35", "Contours compensés"),
                  ("#719cb8", "Hachures de la pièce"), ("#a85c21", "Vecteurs des supports")]
        fig.legend(handles=[Line2D([0], [0], color=color, linewidth=2, label=text)
                            for color, text in legend], loc="lower center", ncol=4, frameon=False)
        fig.tight_layout(rect=(0, 0.065, 1, 0.92))
        fig.savefig(destination / "layer-contours-hatches.png", dpi=130)
        fig.savefig(destination / "layer-contours-hatches.svg")
        plt.close(fig)
    images = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()
              if p.suffix in {".png", ".svg"}}
    (destination / "figures.json").write_text(json.dumps({"images_sha256": images,
        "input_receipt_sha256": hashlib.sha256((directory / ("partial.json" if partial else "report.json")).read_bytes()).hexdigest(),
        "render_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "layer_index": index, "partial_witness": partial,
        "tooth_closeup_part_hidden": True,
        "tooth_closeup_centre_mm": contact.tolist()}, indent=2) + "\n")
    return images


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--layer", type=int)
    parser.add_argument("--output", type=Path, help="New figure directory; preserve existing images")
    args = parser.parse_args()
    print(json.dumps(render(args.directory, args.layer, args.output)))
