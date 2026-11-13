#!/usr/bin/env python3
"""Provide a public image for every catalogue record, including PorscheFanatics.

Records without geometry receive a labelled status card, never invented CAD.
The withdrawn synthetic Carrera F0 impeller also gets a status card. Catalogue
CAD held in a digital-twin directory is supported, and so is CAD a record
declares private (geometry.private_derived_files): it is rendered from local
bytes whose SHA-256 must match, and never committed. Every manifest records the
image kind, publication terms, caption, source CAD and catalogue/image hashes.

Render a product view of every modelled part from its own CAD.

A part folder on GitHub used to open on a bare list of STEP, STL and JSON files:
nothing showed what the part looks like. This script tessellates each part's
derived CAD (STEP preferred, STL otherwise) and renders two images into
`parts/<id>/media/`:

- `preview.png` — a shaded three-quarter view;
- `views.png`   — front, side and top orthographic views with the CAD bounding
                  box in millimeters.

Both are **geometry views of a concept CAD**, not photographs, not renders of a
manufactured part, and not evidence of fit or function. `preview.json` records
which file each image was made from, with its SHA-256, so a stale image is
detected when the CAD changes.

    # rendering needs pyvista/VTK and build123d: run it in the cadsim image,
    # memory-capped, one part at a time (see `make part-previews`)
    python3 scripts/render_part_previews.py --write [--only PART_ID]

    # Private native wall exports require a public source/artifact receipt.
    python3 scripts/render_part_previews.py --write --only PART_ID --private-cad /private/native.vtp

For this explicit mode, CI checks current public authoring inputs, receipt and
image hashes; it does not claim to recompute or reread the private mesh bytes.

    # the check needs only the standard library: it runs in `make check`
    python3 scripts/render_part_previews.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "catalog" / "parts"
PARTS = ROOT / "parts"

# Material family keyword -> display color. A color hints at the material; it
# says nothing about the finish, which no record specifies.
COLORS = [
    (("inconel", "in625", "in718", "nickel", "n07751", "n06625"), "#9a8f7c"),
    (("ti-6al-4v", "titanium", "ti64", "grade 5"), "#8f9aa6"),
    (("fiber", "fibre", "composite", "resin", "carbon"), "#3b3f45"),
    (("abs", "asa", "petg", "pa12", "polymer", "nylon", "to_be_determined_after"), "#34373b"),
    (("steel", "acier"), "#8a9097"),
    (("alsi10mg", "aluminum", "aluminium", "al2139", "6063", "cp1", "aheadd"), "#c4c9cf"),
]
DEFAULT_COLOR = "#b5bac0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def records() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RECORDS.glob("*.json"))]


def private_preview(record: dict) -> tuple[Path, dict] | None:
    """Validate public lineage; CI does not have the private native mesh bytes."""
    geometry = record.get("geometry", {})
    name = geometry.get("private_preview_receipt")
    if not name:
        return None
    if geometry.get("master_format") != "PicoGK" or geometry.get("derived_files"):
        raise ValueError("Private native previews require a PicoGK master and no published derived CAD")

    def public_file(name):
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f"Invalid public preview input: {name}")
        return path

    path = public_file(name)
    receipt = json.loads(path.read_text())
    if receipt.get("kind") != "private_native_wall_preview" or receipt.get("part_id") != record["part_id"]:
        raise ValueError("Private preview receipt identity mismatch")
    artifacts = [receipt.get("artifact", {})] + ([receipt["display_artifact"]] if "display_artifact" in receipt else [])
    for index, artifact in enumerate(artifacts):
        digest, size = artifact.get("sha256", ""), artifact.get("size_bytes")
        formats = ("STL",) if index == 0 else ("STL", "VTP")
        if (artifact.get("format") not in formats or not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
                or type(size) is not int or size <= 0):
            raise ValueError("Invalid private native/display CAD identity")
    inputs = receipt.get("inputs", [])
    roles = {}
    paths = set()
    for source in inputs:
        role, filename = source["role"], source["path"]
        if role in roles or filename in paths:
            raise ValueError("Duplicate private preview input")
        roles[role] = source
        paths.add(filename)
        if sha256(public_file(filename)) != source["sha256"]:
            raise ValueError(f"Stale private preview input: {filename}")
    if not {"canonical", "master", "source", "parameters"} <= roles.keys():
        raise ValueError("Missing canonical, master, source or parameter binding")
    if ("canonical_model_sha256" in receipt
            and receipt["canonical_model_sha256"] != roles["canonical"]["sha256"]):
        raise ValueError("Private preview canonical summary is stale")
    triangles = receipt.get("full_native_triangles")
    if triangles is not None and (type(triangles) is not int or triangles <= 0):
        raise ValueError("Private preview native triangle count is invalid")
    quality = receipt.get("native_mesh_quality")
    if quality is not None:
        count = quality.get("zero_area_face_count")
        if quality.get("admitted") is not False or type(count) is not int or count <= 0 or "native_quality" not in roles:
            raise ValueError("Diagnostic native quality state requires its rejected source-bound report")
        report = json.loads(public_file(roles["native_quality"]["path"]).read_text())
        if (report.get("native_stl_sha256") != receipt["artifact"]["sha256"]
                or report.get("zero_area_triangle_count") != count or report.get("geometry_admitted") is not False):
            raise ValueError("Native quality caption does not match its actual source/count/verdict")
        if triangles is not None and report.get("checked_triangle_count") != triangles:
            raise ValueError("Private preview native triangle count does not match its quality report")
    if "display_artifact" in receipt:
        display = receipt["display_artifact"]
        if (display.get("source_native_sha256") != receipt["artifact"]["sha256"]
                or not display.get("method") or "display_source" not in roles):
            raise ValueError("Display artifact lacks its native source, method or current exporter binding")
        if display.get("kind") != "lossless_native_transport" or display.get("reduced") is not False:
            raise ValueError("Only lossless native transport is accepted; reduced display derivatives are rejected")
        if display["format"] != "VTP" or "transport_equality" not in roles:
            raise ValueError("Lossless native VTP requires a current transport equality receipt")
        equality = json.loads(public_file(roles["transport_equality"]["path"]).read_text())
        native_hash = receipt["artifact"]["sha256"]
        if (equality.get("kind") != "lossless_native_transport_equality"
                or equality.get("native_stl_sha256") != native_hash
                or equality.get("replayed_stl_sha256") != native_hash
                or equality.get("transport_sha256") != display["sha256"]
                or equality.get("vertices_equal") is not True or equality.get("triangles_equal") is not True
                or any(type(equality.get(k)) is not int or equality[k] <= 0
                       for k in ("point_count", "triangle_count"))):
            raise ValueError("Native VTP lossless equality proof is incomplete or misbound")
        if triangles is not None and equality["triangle_count"] != triangles:
            raise ValueError("Private preview native triangle count does not match its transport proof")
        for array in ("vertices", "triangles"):
            before = equality.get("source_"+array+"_sha256", "")
            if (not isinstance(before, str) or len(before) != 64
                    or any(c not in "0123456789abcdef" for c in before)
                    or equality.get("readback_"+array+"_sha256") != before):
                raise ValueError("Native VTP array hashes do not prove lossless readback")
    if roles["master"]["path"] != geometry.get("master_file"):
        raise ValueError("Private preview master does not match its catalogue record")
    canonical = json.loads(public_file(roles["canonical"]["path"]).read_text())
    if (canonical.get("study_id") != record["part_id"]
            or canonical.get("source_builder_sha256") != roles["source"]["sha256"]
            or canonical.get("parameter_sha256") != roles["parameters"]["sha256"]):
        raise ValueError("Canonical model does not bind the current source and parameters")
    return path, receipt


def private_cad_source(record: dict, path: Path | None) -> Path | None:
    """Require exact artifact bytes before the normal renderer can consume them."""
    private = private_preview(record)
    if private is None:
        if path is not None and not private_sources(record):
            raise ValueError("--private-cad requires a catalogue private_preview_receipt"
                             " or geometry.private_derived_files")
        return None
    if path is None:
        raise ValueError("Native preview requires --write --only PART_ID --private-cad PATH")
    artifact = private[1].get("display_artifact", private[1]["artifact"])
    if (path.suffix.lower() != "."+artifact["format"].lower() or not path.is_file()
            or path.stat().st_size != artifact["size_bytes"] or sha256(path) != artifact["sha256"]):
        raise ValueError("Private CAD bytes do not match the public artifact receipt")
    return path


def private_sources(record: dict) -> list[dict]:
    """CAD held privately (scan-derived geometry that must not be published).

    Separate from the PicoGK private_preview_receipt above: the record declares
    each file's name and SHA-256 under geometry.private_derived_files; images
    are rendered locally from the private bytes (``--private-cad``) and the
    manifest cites the hash with a ``private:`` path, so the check can tie the
    images to the declared CAD without the CAD itself entering Git.
    """
    return [{"path": "private:" + str(f["name"]), "sha256": str(f["sha256"])}
            for f in record.get("geometry", {}).get("private_derived_files", [])]


def private_derived_paths(record: dict, path: Path | None) -> list[Path]:
    """Local files for geometry.private_derived_files, checked against their SHA-256."""
    declared = private_sources(record)
    names = [e["path"][len("private:"):] for e in declared]
    if path is None:
        raise SystemExit(f"{record['part_id']}: its CAD is private; pass --write --only PART_ID"
                         " --private-cad PATH (the file, or a directory holding " + ", ".join(names) + ")")
    if not path.is_dir() and len(declared) != 1:
        raise SystemExit(f"{record['part_id']}: several private files are declared; --private-cad must be a directory")
    files = []
    for name, e in zip(names, declared):
        candidate = path / name if path.is_dir() else path
        if not candidate.is_file() or sha256(candidate) != e["sha256"]:
            raise SystemExit(f"{record['part_id']}: {candidate} does not match the declared SHA-256 of {name}")
        files.append(candidate)
    return files


def private_artifact_metadata(receipt: dict) -> dict:
    canonical = next(s for s in receipt["inputs"] if s["role"] == "canonical")
    result = {"native": receipt["artifact"],
            "rendered": receipt.get("display_artifact", receipt["artifact"]),
            "canonical_model_sha256": canonical["sha256"]}
    if "native_mesh_quality" in receipt:
        result["native_mesh_quality"] = receipt["native_mesh_quality"]
    return result


def sources(part_id: str) -> list[Path]:
    """Prefer the existing per-part CAD; otherwise use catalogue-derived CAD.

    Digital-twin outputs are valid sources too. A missing declared file must
    fail rather than silently turn a model into a "not modelled" status card.
    """
    record = next(r for r in records() if r["part_id"] == part_id)
    private = private_preview(record)
    folder = PARTS / part_id.lower() / "derived"
    local = sorted(folder.iterdir()) if folder.is_dir() else []
    if private:
        if any(p.suffix.lower() in (".step", ".stp", ".stl") for p in local):
            raise ValueError("Private preview receipt conflicts with published part CAD")
        return [private[0]] + [ROOT / s["path"] for s in private[1]["inputs"]]
    # Gyroid-core variants (git-ignored, see parts/picogk-catalog/bionic/) have their own image.
    local = [p for p in local if not p.name.endswith("-picogk-gyroid.stl")]
    picogk = [p for p in local if p.name.endswith("-picogk.stl")]
    if picogk:
        return picogk[:3]
    chosen: dict[str, Path] = {}
    for p in local:
        if p.suffix.lower() not in (".step", ".stp", ".stl"):
            continue
        if p.stem not in chosen or p.suffix.lower() in (".step", ".stp"):
            chosen[p.stem] = p
    if chosen:
        return list(chosen.values())[:3]
    for name in record.get("geometry", {}).get("derived_files", []):
        path = ROOT / name
        if path.suffix.lower() not in (".step", ".stp", ".stl"):
            continue
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f"Invalid catalogue CAD source: {name}")
        if path.stem not in chosen or path.suffix.lower() in (".step", ".stp"):
            chosen[path.stem] = path
    return list(chosen.values())[:3]


def color(record: dict) -> str:
    m = record.get("manufacturing", {}).get("material", {})
    text = " ".join(str(m.get(k, "")) for k in ("family", "grade")).lower()
    for keys, value in COLORS:
        if any(k in text for k in keys):
            return value
    return DEFAULT_COLOR


def geometry_note(record: dict, picogk_model: bool, rotation_x_deg: int) -> str:
    if record.get("geometry", {}).get("private_preview_receipt"):
        quality = private_preview(record)[1].get("native_mesh_quality")
        note = (f"Unqualified diagnostic views of the full native PicoGK export. Native mesh quality screen rejected: "
                f"{quality['zero_area_face_count']} collapsed, zero-area faces retained. No reduction or repair. "
                if quality else "Geometry views of the full native PicoGK wall surfaces; no display reduction. ")
        note += (
                "Mesh bytes are retained privately; the public receipt binds their hash and authoring inputs. ")
    elif rotation_x_deg:
        note = ("Blade-side views of the existing K16 compressor concept. "
                "Blade surfaces, hub and shaft interfaces remain unmeasured design hypotheses. ")
    elif picogk_model:
        geometry = record.get("geometry", {})
        master = geometry.get("master_file", "")
        source = "parts/picogk-catalog/"
        if geometry.get("master_format") == "PicoGK" and master and not master.startswith(source):
            source = master
        note = f"Geometry views of the part's PicoGK concept model ({source}). "
    else:
        note = "Geometry views of the concept CAD. "
    return note + "Not a photograph, not a render of a manufactured part, not evidence of fit or function."


# --- rendering (cadsim image only) -------------------------------------------

def mesh_of(path: Path):
    import pyvista as pv
    if path.suffix.lower() in (".stl", ".vtp"):
        return pv.read(str(path))
    from build123d import export_stl, import_step
    shape = import_step(str(path))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "m.stl"
        size = max(shape.bounding_box().size.X, shape.bounding_box().size.Y,
                   shape.bounding_box().size.Z)
        export_stl(shape, str(out), tolerance=max(size / 2000, 0.005), angular_tolerance=0.15)
        return pv.read(str(out))


def status_card(record: dict, files: list[Path]) -> dict:
    """Provide an honest public image when no publishable geometry is available."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    part_id = record["part_id"]
    media = PARTS / part_id.lower() / "media"
    media.mkdir(parents=True, exist_ok=True)
    archived = part_id == "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001"
    heading = "ARCHIVED GEOMETRY" if archived else "GEOMETRY NOT CREATED"
    caption = (
        "Archived synthetic Carrera F0 study; not the 993 Turbo fan. "
        "The generic rotor views were withdrawn to avoid confusing the two designs."
        if archived else
        "Catalogue study only. No CAD geometry is available for this record."
    )
    image = Image.new("RGB", (1400, 900), "#f4f5f6")
    draw = ImageDraw.Draw(image)
    # Pillow ships this scalable font: no operating-system font dependency.
    def font(size):
        return ImageFont.load_default(size=size)
    draw.rectangle((0, 0, 18, 900), fill="#a5282c")
    draw.text((85, 75), "PORSCHE PARTS / RESEARCH", font=font(26), fill="#626970")
    draw.text((85, 170), heading, font=font(52), fill="#252a30")
    for i, line in enumerate(textwrap.wrap(part_id, width=42)):
        draw.text((85, 280 + i * 48), line, font=font(34), fill="#252a30")
    for i, line in enumerate(textwrap.wrap(caption, width=65)):
        draw.text((85, 425 + i * 46), line, font=font(30), fill="#444b52")
    draw.line((85, 720, 1315, 720), fill="#c4c9ce", width=2)
    draw.text((85, 760), "Status card - no part geometry depicted", font=font(25), fill="#626970")
    draw.text((85, 807), "Not a photograph or evidence of fit, function or manufacturing release.",
              font=font(23), fill="#626970")
    image.save(media / "preview.png")
    info = {
        "part_id": part_id,
        "kind": "status_card",
        "note": caption + " Status card; no part geometry depicted.",
        "sources": [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files],
        "bounding_box_mm": None,
        "images": ["preview.png"],
        "generator": "scripts/render_part_previews.py",
    }
    return save_manifest(record, info)


def save_manifest(record: dict, info: dict) -> dict:
    media = PARTS / record["part_id"].lower() / "media"
    info["record_sha256"] = sha256(RECORDS / (record["part_id"].lower() + ".json"))
    info["license"] = "Repository LICENSE; owner-authorized publication on PorscheFanatics.com."
    info["image_sha256"] = {name: sha256(media / name) for name in info["images"]}
    (media / "preview.json").write_text(json.dumps(info, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")
    return info


def display_rotation_x_deg(part_id: str, files: list[Path]) -> int:
    """Show the blade face of the two rotors archived back-face-up.

    Their documented bionic frame is a 180-degree X rotation, not a mirror.
    The source meshes and blade handedness are preserved.
    """
    back_face_up = {
        "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001",
        "993-ENG-K16-COMPRESSOR-WHEEL-AL2139-F1-0001",
    }
    return 180 if (part_id in back_face_up and files
                   and all(f.name.endswith("-picogk.stl") for f in files)) else 0


def render(record: dict, private_cad: Path | None = None) -> dict:
    part_id = record["part_id"]
    files = sources(part_id)
    private = private_preview(record)
    native_path = private_cad_source(record, private_cad)
    withheld = private_sources(record) if not files else []
    if withheld:
        files = private_derived_paths(record, private_cad)
    if not files or part_id == "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001":
        return status_card(record, files)
    import pyvista as pv
    pv.OFF_SCREEN = True
    rotation_x_deg = display_rotation_x_deg(part_id, files)
    meshes = [mesh_of(native_path)] if native_path else [mesh_of(f) for f in files]
    if rotation_x_deg:
        meshes = [m.rotate_x(rotation_x_deg, inplace=False) for m in meshes]
    geometry = record.get("geometry", {})
    picogk_model = (geometry.get("master_format") == "PicoGK"
                   or all(f.name.endswith("-picogk.stl") for f in files))
    exact_step = all(f.suffix.lower() in (".step", ".stp") for f in files)
    legacy_master = geometry.get("master_file", "").startswith("parts/picogk-catalog/")
    smooth = not private and picogk_model and (not exact_step or legacy_master)
    tint = color(record)
    media = PARTS / part_id.lower() / "media"
    media.mkdir(parents=True, exist_ok=True)

    def scene(plotter, view: str):
        plotter.set_background("white")
        offset = 0.0
        for m in meshes:
            if len(meshes) > 1:
                m = m.copy()
                b = m.bounds
                m.translate((offset - b[0], -(b[2] + b[3]) / 2, 0), inplace=True)
                offset += (b[1] - b[0]) * 1.25
            plotter.add_mesh(m, color=tint, smooth_shading=smooth, specular=0.35 if smooth else 0.25,
                             specular_power=20 if smooth else 15, ambient=0.25, diffuse=0.8)
            if not private:
                edges = m.extract_feature_edges(feature_angle=35, boundary_edges=True,
                                                non_manifold_edges=False, manifold_edges=False)
                if edges.n_points and not smooth:
                    plotter.add_mesh(edges, color="#2b2f33", line_width=1.2)
        if view == "iso":
            # three-quarter view from front-left, above: shows the X-Z profile
            # that most extruded parts are drawn in, plus depth
            plotter.view_vector((0.9, -1.7, 1.0), viewup=(0, 0, 1))
        else:
            {"front": plotter.view_xz, "side": plotter.view_yz, "top": plotter.view_xy}[view]()
            plotter.enable_parallel_projection()
        plotter.reset_camera()
        plotter.camera.zoom(1.15 if view == "iso" else 1.05)

    p = pv.Plotter(off_screen=True, window_size=(1400, 900), lighting="three lights")
    scene(p, "iso")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(str(media / "preview.png"))
    p.close()

    union = meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]
    b = union.bounds
    dims = [round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)]
    p = pv.Plotter(off_screen=True, shape=(1, 3), window_size=(1800, 620), border=False,
                   lighting="three lights")
    labels = {"front": f"front (X-Z)  {dims[0]} x {dims[2]} mm",
              "side": f"side (Y-Z)  {dims[1]} x {dims[2]} mm",
              "top": f"top (X-Y)  {dims[0]} x {dims[1]} mm"}
    for i, view in enumerate(("front", "side", "top")):
        p.subplot(0, i)
        scene(p, view)
        p.add_text(labels[view], position="lower_edge", font_size=10, color="#2b2f33")
    # The SSAA render pass corrupts multiple viewports under VTK 9.5.2/EGL.
    p.screenshot(str(media / "views.png"))
    p.close()

    info = {
        "part_id": part_id,
        "kind": "geometry_render",
        "note": geometry_note(record, picogk_model, rotation_x_deg)
        + (" Rendered from private CAD whose SHA-256 is recorded; the CAD itself is not published." if withheld else ""),
        "display_rotation_x_deg": rotation_x_deg,
        "sources": withheld or [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files],
        "bounding_box_mm": dims,
        "images": ["preview.png", "views.png"],
        "generator": "scripts/render_part_previews.py",
    }
    if private:
        private_cad_source(record, native_path)
        info["private_artifact"] = private_artifact_metadata(private[1])
    return save_manifest(record, info)


# --- check (standard library only) -------------------------------------------

def check() -> int:
    failures = []
    for record in records():
        part_id = record["part_id"]
        info_path = PARTS / part_id.lower() / "media" / "preview.json"
        try:
            files = sources(part_id)
            private = private_preview(record)
            info = json.loads(info_path.read_text(encoding="utf-8"))
            expected = [{"path": f.relative_to(ROOT).as_posix(), "sha256": sha256(f)} for f in files]
            withheld = private_sources(record) if not files else []
            if withheld:
                expected = withheld
            card = (not files and not withheld) or part_id == "993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001"
            names = ["preview.png"] if card else ["preview.png", "views.png"]
            if info.get("kind") != ("status_card" if card else "geometry_render"):
                raise ValueError("incorrect image kind")
            if info.get("part_id") != part_id or info.get("sources") != expected:
                raise ValueError("preview does not match its CAD")
            expected_private = private_artifact_metadata(private[1]) if private else None
            if info.get("private_artifact") != expected_private or (not private and "private_artifact" in info):
                raise ValueError("preview does not match its private native artifact receipt")
            if info.get("display_rotation_x_deg", 0) != display_rotation_x_deg(part_id, files):
                raise ValueError("preview does not show the expected model face")
            if info.get("record_sha256") != sha256(RECORDS / (part_id.lower() + ".json")):
                raise ValueError("preview does not match its catalogue record")
            if info.get("images") != names or not info.get("note") or not info.get("license"):
                raise ValueError("incomplete publication metadata")
            hashes = info.get("image_sha256", {})
            photo_path = info_path.parent / "photo.json"
            if photo_path.exists():
                photo = json.loads(photo_path.read_text(encoding="utf-8"))
                # The illustration depicts the CAD geometry, so it goes stale
                # only when a CAD source changes. The record and reference
                # preview hashes are provenance: what it was generated from.
                if (card or photo.get("kind") != "ai_illustration"
                        or photo.get("part_id") != part_id
                        or photo.get("sources") != expected
                        or not photo.get("record_sha256")
                        or not photo.get("reference_sha256")
                        or photo.get("images") != ["photo-concept.png"]
                        or not photo.get("prompt") or not photo.get("generator")
                        or "not a photograph" not in photo.get("note", "").lower()
                        or not photo.get("license")):
                    raise ValueError("incomplete or stale AI illustration metadata")
                names += photo["images"]
                hashes = {**hashes, **photo.get("image_sha256", {})}
            elif (info_path.parent / "photo-concept.png").exists():
                raise ValueError("AI illustration is missing its publication metadata")
            for name in names:
                path = info_path.parent / name
                with path.open("rb") as stream:
                    header = stream.read(24)
                if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n"
                        or header[12:16] != b"IHDR"
                        or not int.from_bytes(header[16:20], "big")
                        or not int.from_bytes(header[20:24], "big")):
                    raise ValueError(f"invalid PNG: {name}")
                if hashes.get(name) != sha256(path):
                    raise ValueError(f"changed image: {name}")
        except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
            failures.append(f"{part_id}: {exc}")
    for failure in failures:
        print(f"FAIL   {failure}", file=sys.stderr)
    if failures:
        print("       rerun: make part-previews", file=sys.stderr)
        return 1
    print(f"OK   {len(records())} catalogue records have current, hashed public images")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--only", help="render a single part_id")
    ap.add_argument("--private-cad", type=Path,
                    help="private CAD for the selected part: the STL/VTP matching its native preview receipt,"
                         " or the file or directory holding its geometry.private_derived_files")
    ap.add_argument("--list", action="store_true", help="print all catalogue part_ids")
    a = ap.parse_args()
    if a.private_cad and (not a.write or not a.only or a.list):
        ap.error("--private-cad requires --write --only PART_ID")
    if a.check:
        return check()
    todo = [r for r in records() if not a.only or r["part_id"].lower() == a.only.lower()]
    if a.private_cad and len(todo) != 1:
        ap.error("--private-cad requires exactly one existing catalogue record")
    if a.list:
        for r in todo:
            print(r["part_id"])
        return 0
    for r in todo:
        info = render(r, a.private_cad)
        print(f"{info['kind']} {r['part_id']}"
              + (f"  {info['bounding_box_mm']} mm" if info["bounding_box_mm"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
