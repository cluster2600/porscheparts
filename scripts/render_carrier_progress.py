"""Render retained carrier triangles and a diagnosed support, with hash-bound captions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
import numpy as np
import trimesh


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rejected_faces(vertices, faces, groups, graph):
    identity = hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()
    if identity != graph["input_geometry_sha256"]:
        raise ValueError("Support graph does not describe these triangles")
    by_id = {group["id"]: group for group in groups}
    if len(by_id) != len(groups) or graph["groups"] != len(groups):
        raise ValueError("Material group identities disagree")
    cursor = 0
    for group in groups:
        start, end = group["face_range"]
        if start != cursor or not start < end <= len(faces):
            raise ValueError("Material groups do not partition the faces")
        cursor = end
    if cursor != len(faces):
        raise ValueError("Material groups do not cover every face")
    listed = [name for component in graph["components"] for name in component["group_ids"]]
    if len(listed) != len(set(listed)) or set(listed) != set(by_id):
        raise ValueError("Graph components do not partition the material groups")
    mask = np.zeros(len(faces), dtype=bool)
    for component in graph["components"]:
        if not component["passed"]:
            for name in component["group_ids"]:
                start, end = by_id[name]["face_range"]
                mask[start:end] = True
    return mask


def raster(vertices, faces, colors, elevation, azimuth, bounds=None):
    from vispy import scene
    canvas = scene.SceneCanvas(show=False, size=(2000, 720), bgcolor="#f5f7f9")
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.TurntableCamera(fov=0, elevation=elevation, azimuth=azimuth)
        scene.visuals.Mesh(vertices=vertices, faces=faces, face_colors=colors,
                           shading="flat", parent=view.scene)
        box = np.array([vertices.min(0), vertices.max(0)]) if bounds is None else bounds
        view.camera.set_range(x=box[:, 0], y=box[:, 1], z=box[:, 2], margin=.035)
        # VisPy's default fit assumes XY extends horizontally, even after camera rotation.
        el, az = np.radians([elevation, azimuth])
        right = np.array([np.cos(az), np.sin(az), 0.])
        up = np.array([-np.sin(el)*np.sin(az), np.sin(el)*np.cos(az), np.cos(el)])
        corners = np.array([[x, y, z] for x in box[:, 0] for y in box[:, 1] for z in box[:, 2]])
        projected = (corners-box.mean(0)) @ np.stack([right, up], axis=1)
        extent = 2*np.abs(projected).max(0)
        view.camera.center = box.mean(0)
        view.camera.scale_factor = max(extent[1], extent[0]/(2000/720))*1.10
        pixels = canvas.render()
        occupied = np.any(pixels[:, :, :3] != [245, 247, 249], axis=2)
        y, x = np.nonzero(occupied)
        if not len(x):
            raise ValueError("Rendering is empty")
        return pixels[max(0,y.min()-30):min(len(pixels),y.max()+31),
                      max(0,x.min()-30):min(pixels.shape[1],x.max()+31)]
    finally:
        canvas.close()


def save(figure, output, name):
    figure.savefig(output / name, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)


def run(directory, support, output):
    directory, support, output = map(lambda p: Path(p).resolve(), (directory, support, output))
    output.mkdir(parents=True, exist_ok=False)
    paths = [directory / "cad/geometry.json", directory / "cad/carrier.step",
             directory / "surface/carrier-remeshed.stl", support / "support.npz",
             support / "geometry-assessment.json", support / "material-connections.json",
             support / "assessment.json", directory / "surface-audit/cad-mesh-audit.json"]
    identities = {str(path): sha(path) for path in paths}
    geometry = json.loads(paths[0].read_text())
    if geometry["geometry_sha256"]["carrier.step"] != sha(paths[1]):
        raise ValueError("CAD mass receipt does not describe this STEP")
    audit = json.loads(paths[-1].read_text())
    if audit["STEP_sha256"] != sha(paths[1]) or audit["candidate_STL_sha256"] != sha(paths[2]):
        raise ValueError("CAD/mesh audit does not bind the rendered STL to the mass receipt")
    mass = geometry["dense_reference_mass_kg"]
    if not geometry["CAD_valid"] or geometry["solid_count"] != 1 or not mass <= 1.30:
        raise ValueError("Retained carrier geometry has not passed its mass/solid checks")
    model = trimesh.load_mesh(paths[2], process=False)
    vertices, faces = np.asarray(model.vertices), np.asarray(model.faces)
    blue = np.tile([.12, .42, .61, 1.], (len(faces), 1))
    fig, axes = plt.subplots(2, 1, figsize=(15, 8.5), facecolor="#f5f7f9")
    for ax, elevation, azimuth, caption in [(axes[0], 26, 10, "Vue oblique · nervures et interfaces"),
                                           (axes[1], 90, 0, "Vue de dessus · même géométrie")]:
        ax.imshow(raster(vertices, faces, blue, elevation, azimuth))
        ax.set_title(caption, loc="left", fontsize=11, color="#243a50")
        ax.axis("off")
    fig.suptitle("993 TURBO  /  BERCEAU MOTEUR", x=.045, ha="left", fontsize=23, weight="bold", color="#173249")
    fig.text(.955, .945, f"{mass:.3f} kg".replace(".", ","), ha="right", fontsize=25, weight="bold", color="#167269")
    fig.text(.955, .913, "Limite : 1,30 kg", ha="right", fontsize=11, color="#344c5e")
    fig.text(.045, .047, f"592 × 73 × 52 mm  ·  {len(faces):,} triangles réels  ·  marge de masse : {(1.30-mass)*1000:.1f} g".replace(",", " "), fontsize=11)
    fig.text(.045, .022, "Géométrie de travail retenue · projection du STL remeshing, sans lissage ni modification de forme", fontsize=9, color="#536477")
    fig.subplots_adjust(left=.035, right=.975, top=.86, bottom=.09, hspace=.14)
    save(fig, output, "carrier-actual-geometry.png")

    assessment = json.loads((support / "geometry-assessment.json").read_text())
    graph = json.loads((support / "material-connections.json").read_text())
    with np.load(support / "support.npz", allow_pickle=False) as data:
        sv, sf = data["vertices"], data["faces"]
    if sha(support / "support.npz") != assessment["surface_sha256"]:
        raise ValueError("Support surface receipt does not match its NPZ")
    groups = assessment["peripheral_skin"]["support_surface_face_groups"]
    bad = rejected_faces(sv, sf, groups, graph)
    count = sum(not component["passed"] for component in graph["components"])
    colors = np.tile([.83, .50, .19, 1.], (len(sf), 1))
    colors[bad] = [.91, .10, .18, 1.]
    area = np.linalg.norm(np.cross(sv[sf[bad, 1]]-sv[sf[bad, 0]],
                                   sv[sf[bad, 2]]-sv[sf[bad, 0]]), axis=1).sum()/2
    fig, axes = plt.subplots(2, 1, figsize=(15, 9.5), facecolor="#f5f7f9")
    axes[0].imshow(raster(sv, sf, colors, 25, 45))
    axes[0].set_title("Région droite seule · surfaces réellement générées", loc="left", fontsize=12)
    bad_faces = np.flatnonzero(bad)
    if len(bad_faces):
        largest = bad_faces[np.argmax(trimesh.triangles.area(sv[sf[bad_faces]]))]
        group = next(g for g in groups if g["face_range"][0] <= largest < g["face_range"][1])
        if group["kind"] != "grid":
            raise ValueError("Diagnostic close-up requires an actual planar grid group")
        axis, plane = group["fixed_axis"], group["plane_coordinate_mm"]
        same_plane = np.zeros(len(sf), dtype=bool)
        for g in groups:
            if g["kind"] == "grid" and g["fixed_axis"] == axis and g["plane_coordinate_mm"] == plane:
                same_plane[slice(*g["face_range"])] = True
        free = 1-axis
        triangles = sv[sf[same_plane]][:, :, [free, 2]]
        axes[1].add_collection(PolyCollection(triangles, facecolors=colors[same_plane], edgecolors="none"))
        centre = sv[sf[largest]].mean(0)
        axes[1].set(xlim=(centre[free]-6, centre[free]+6), ylim=(centre[2]-5, centre[2]+5),
                    xlabel=f"{'Y' if axis == 0 else 'X'} (mm)", ylabel="Z (mm)")
        axes[1].set_aspect("equal")
        axes[1].grid(alpha=.15)
        axes[1].set_title(f"Détail dans le plan réel {'X' if axis == 0 else 'Y'} = {plane:.3f} mm · îlot en rouge", loc="left", fontsize=12)
    axes[0].axis("off")
    fig.suptitle("SUPPORTS D’IMPRESSION  /  DIAGNOSTIC", x=.045, ha="left", fontsize=21, weight="bold", color="#173249")
    fig.text(.045, .915, f"Essai {support.name} · {count} composantes sans les deux ancrages requis · {area:.2f} mm²", fontsize=11)
    fig.legend(handles=[Patch(color="#d48030", label="Autres surfaces du support"),
                        Patch(color="#e8192e", label="Composantes signalées par le graphe exact")],
               loc="lower center", bbox_to_anchor=(.5, .063), ncol=2, frameon=False, fontsize=10)
    fig.text(.045, .022, "ESSAI REFUSÉ · une région sur sept · les dents, contacts, îlots et triangles sont issus des données calculées", fontsize=9, color="#a52c39")
    fig.subplots_adjust(left=.035, right=.975, top=.875, bottom=.17, hspace=.17)
    save(fig, output, "support-actual-diagnostic.png")

    for source, target in [(directory / "surface-figure/carrier-remesh-comparison.png", "remesh-before-after.png"),
                           (directory / "dimensions/carrier-dimensions.png", "carrier-dimensions.png")]:
        identities[str(source)] = sha(source)
        shutil.copy2(source, output / target)
    layer = directory.parent.parent / "carrier-process-20261016/part-cache-layer-518-001/part-layer.png"
    identities[str(layer)] = sha(layer)
    shutil.copy2(layer, output / "actual-layer-00518.png")
    if any(sha(path) != digest for path, digest in identities.items()):
        raise ValueError("An input changed during rendering")
    receipt = dict(status="rendered_from_actual_geometry", source_sha256=sha(__file__),
                   inputs_sha256=identities, carrier_faces=len(faces), support_faces=len(sf),
                   support_rejected_components=count, support_rejected_surface_area_mm2=float(area),
                   mass_kg=mass, mass_limit_kg=1.30, input_files_unchanged=True,
                   full_support_preparation_admitted=False,
                   images_sha256={p.name:sha(p) for p in output.glob("*.png")})
    (output / "figures.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    captions = [
        ("carrier-actual-geometry.png", "La pièce retenue", "1,262 kg sur une limite de 1,30 kg. Les vues utilisent tous les triangles du STL actuel."),
        ("carrier-dimensions.png", "Les dimensions du modèle", "Plan coté de la géométrie de travail, avec les interfaces conservées."),
        ("remesh-before-after.png", "La surface avant et après", "Comparaison du maillage et de la référence STEP dans les mêmes coordonnées."),
        ("actual-layer-00518.png", "Une couche d’impression réelle", "Couche d’indice 518 sur 1 034, à Z = 31,110 mm. Contours et hachures de la pièce ; cette planche ne contient aucun support."),
        ("support-actual-diagnostic.png", "Les supports en cours de correction", "Essai perforé refusé : la région droite contient encore 26 composantes sans les deux ancrages requis. Les îlots sont montrés en rouge dans leur plan réel.")]
    cards = "".join(f'<section><h2>{title}</h2><p>{caption}</p><a href="{name}"><img src="{name}" alt="{title}" loading="lazy"></a></section>' for name,title,caption in captions)
    (output / "index.html").write_text('<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>993 Turbo · Images du travail</title><style>body{margin:0;background:#edf2f5;color:#183249;font:17px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:32px 20px}h1{font-size:38px;line-height:1.15}h2{margin:0;font-size:25px}section{margin:28px 0;padding:24px;background:white;border-radius:16px}img{display:block;width:100%;height:auto}a{color:#086c83}p{max-width:85ch}.status{padding:18px 22px;background:#e4f3ed;border-left:5px solid #167269}</style><main><header><p>993 TURBO · DOSSIER VISUEL</p><h1>Du modèle aux couches d’impression</h1><p>Images produites à partir des fichiers CAD, des triangles et des résultats de calcul conservés dans le projet.</p><p class="status"><strong>Pièce retenue : 1,262 kg.</strong> Géométrie et couches de la pièce calculées. Supports d’impression encore en correction.</p></header>'+cards+'<footer><p>Cliquer sur une image pour sa définition complète. <a href="figures.json">Sources et empreintes des fichiers</a>.</p></footer></main></html>')
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["directory", "support", "output"]:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.directory, args.support, args.output), indent=2))
