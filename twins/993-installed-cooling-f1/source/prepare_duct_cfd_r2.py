#!/usr/bin/env python3
"""Prepare the fixed-flow, free-discharge duct pilot from the undecimated fluid surface (issue #452).

Second revision of the CFD preparer. ``prepare_duct_cfd.py`` stays as it is: the
receipts of attempts 1-6 cite its hash. The upstream audit of 2026-11-10 found
that its 90 % decimation put 1,007 creases on smooth faces, so this revision

- meshes the cleaned PicoGK surface as exported, with no decimation;
- writes the inlet and outlet rims, the edges between surface regions, as an
  explicit feature-edge mesh and asks snappyHexMesh to snap to those edges only;
- labels the whole of each outlet opening as outlet (see ``port_labels``);
- takes the study card and the background cell size as arguments.

Every other dictionary entry, quality limit, boundary condition and solver
setting is that of ``prepare_duct_cfd.py``. No rotating fan, intercooler, engine
resistance or heat transfer is modelled; the prescribed inlet flow is a test
boundary, not a fan operating point.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh

STUDY = Path(__file__).resolve().parents[1]
NAMES = ["walls", "inlet", "left1", "left2", "left3", "right1", "right2", "right3"]
# Background block of prepare_duct_cfd.py, in mm: 116 x 106 x 64 cells of 5 mm.
BLOCK_MIN = (-290.0, -210.0, 5.0)
BLOCK_MAX = (290.0, 320.0, 325.0)


AUDITOR = Path(__file__).with_name("audit_mesh_admission_r2.py")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_auditor():
    spec = importlib.util.spec_from_file_location("audit_mesh_admission_r2", AUDITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def port_labels_r1(centres, card):
    """Region of each triangle by the rule of prepare_duct_cfd.py; kept to measure what it mislabels."""
    g = card["geometry"]
    labels = np.full(len(centres), "walls", dtype=object)
    labels[np.abs(centres[:, 1] - g["fan_rear_y_mm"]) < .01] = "inlet"
    for side, x in (("left", -g["outlet_x_mm"]), ("right", g["outlet_x_mm"])):
        for i, y in enumerate(g["outlet_y_mm"]):
            at_port = ((np.abs(centres[:, 2] - g["outlet_z_mm"]) < .01)
                       & (np.hypot(centres[:, 0] - x, centres[:, 1] - y) < g["outlet_radius_mm"] + 3))
            labels[at_port] = f"{side}{i + 1}"
    return labels


def port_labels(mesh, card):
    """Region of each triangle: a port where the surface faces out of a port plane, walls elsewhere.

    Two defects of the rule of prepare_duct_cfd.py are corrected.

    It accepted an outlet triangle only within outlet_radius + 3 mm of
    (outlet_x, y). The branch cone reaches that radius 25 mm below the outlet
    plane; where the plane cuts it the opening is wider and centred further
    inboard, so a crescent of every opening was labelled as wall. Here a triangle
    of the outlet plane belongs to its nearest port.

    It also accepted only triangles lying in the port plane. The voxel export
    replaces each sharp rim by a chamfer about one and a half voxels wide, so the
    regions stopped that far short of the rims. Here a triangle within two voxels
    of a port plane belongs to the port when its outward normal is within 45
    degrees of the plane's, which puts the region boundary on the chamfer.
    """
    g = card["geometry"]
    centres, normals = mesh.triangles_center, mesh.face_normals
    reach, facing = 2 * g["voxel_mm"], np.cos(np.radians(45))
    labels = np.full(len(centres), "walls", dtype=object)
    labels[(centres[:, 1] - g["fan_rear_y_mm"] < reach) & (-normals[:, 1] > facing)] = "inlet"
    outlet = (centres[:, 2] - g["outlet_z_mm"] < reach) & (-normals[:, 2] > facing)
    nearest = np.abs(centres[:, 1][:, None] - np.array(g["outlet_y_mm"])[None, :]).argmin(axis=1)
    for side, left in (("left", True), ("right", False)):
        for i in range(len(g["outlet_y_mm"])):
            labels[outlet & ((centres[:, 0] < 0) == left) & (nearest == i)] = f"{side}{i + 1}"
    return labels


def clean_surface(native):
    """The cleaning of build_review.py: drop duplicate and degenerate triangles, fill nothing."""
    mesh = trimesh.load_mesh(native, process=True)
    mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count == 1 and mesh.volume > 0):
        raise ValueError("Closed, outward-oriented single fluid domain required")
    return mesh


def region_boundary_edges(mesh, labels):
    """Edges shared by two triangles of different regions, grouped into connected boundaries."""
    pairs = mesh.face_adjacency
    between = labels[pairs[:, 0]] != labels[pairs[:, 1]]
    edges = mesh.face_adjacency_edges[between]
    regions = [tuple(sorted((labels[a], labels[b]))) for a, b in pairs[between]]
    if np.any(np.bincount(edges.ravel()) % 2):
        raise ValueError("A region boundary is not closed")
    groups = trimesh.graph.connected_components(edges, min_len=1)
    group_of = {int(v): i for i, group in enumerate(groups) for v in group}
    length = np.zeros(len(groups))
    np.add.at(length, [group_of[int(a)] for a in edges[:, 0]],
              np.linalg.norm(mesh.vertices[edges[:, 0]] - mesh.vertices[edges[:, 1]], axis=1))
    return edges, regions, length


def block_cells(cell_mm):
    counts = []
    for lo, hi in zip(BLOCK_MIN, BLOCK_MAX):
        n = (hi - lo) / cell_mm
        if abs(n - round(n)) > 1e-9:
            raise ValueError("The background block is not a whole number of cells of this size")
        counts.append(int(round(n)))
    return counts


def run(native, study, output, flow, cell_mm):
    if not np.isfinite(flow) or flow <= 0:
        raise ValueError("Positive finite flow required")
    if output.exists():
        raise FileExistsError(output)
    card = json.loads(study.read_text())
    g = card["geometry"]
    counts = block_cells(cell_mm)
    mesh = clean_surface(native)
    labels = port_labels(mesh, card)
    if set(labels) != set(NAMES):
        raise ValueError("Missing fluid port")
    edges, edge_regions, boundary_lengths = region_boundary_edges(mesh, labels)
    if len(boundary_lengths) != 8:
        raise ValueError("Expected the two inlet rims and six outlet rims")
    rim_points = mesh.vertices[np.unique(edges)]
    # The surface's own region boundaries zigzag along the voxel chamfers and are longer
    # than the rims they follow. The explicit edges are therefore the rims as the
    # generator cuts them, from the constructive model that the auditor checks against
    # this surface, and the surface's boundaries must lie within two voxels of them.
    audit = load_auditor()
    model = audit.bind_r2_model(audit.load_base(), g)
    rims = audit.constructive_rims(model, g, g["voxel_mm"])
    rim_gap = np.array([min(np.linalg.norm(rim - point, axis=1).min() for rim in rims.values()) for point in rim_points])
    if rim_gap.max() > 2 * g["voxel_mm"]:
        raise ValueError("The surface's region boundaries are not the constructive rims")
    for name in ("system", "constant/triSurface", "0"):
        (output / name).mkdir(parents=True)

    with (output / "constant/triSurface/duct.stl").open("w") as stream:
        triangles, normals = mesh.triangles / 1000, mesh.face_normals
        for name in NAMES:
            stream.write(f"solid {name}\n")
            for triangle, normal in zip(triangles[labels == name], normals[labels == name]):
                stream.write("facet normal " + " ".join(f"{v:.9g}" for v in normal) + "\nouter loop\n")
                for vertex in triangle:
                    stream.write("vertex " + " ".join(f"{v:.9g}" for v in vertex) + "\n")
                stream.write("endloop\nendfacet\n")
            stream.write(f"endsolid {name}\n")

    def write(path, body, cls="dictionary"):
        obj = Path(path).name
        (output / path).write_text(f"FoamFile {{version 2.0; format ascii; class {cls}; object {obj};}}\n" + body + "\n")

    feature_points = np.vstack(list(rims.values()))
    feature_edges, offset = [], 0
    for rim in rims.values():
        feature_edges += [(offset + i, offset + (i + 1) % len(rim)) for i in range(len(rim))]
        offset += len(rim)
    write("constant/triSurface/duct-rims.eMesh",
          f"{len(feature_points)}\n(\n"
          + "\n".join("(" + " ".join(f"{v:.9g}" for v in p / 1000) + ")" for p in feature_points)
          + f"\n)\n{len(feature_edges)}\n(\n"
          + "\n".join(f"({a} {b})" for a, b in feature_edges) + "\n)",
          "featureEdgeMesh")
    lo, hi = np.array(BLOCK_MIN) / 1000, np.array(BLOCK_MAX) / 1000
    corners = [(x, y, z) for z in (lo[2], hi[2]) for x, y in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1]))]
    write("system/blockMeshDict", "scale 1;\nvertices ("
          + "".join("(" + " ".join(f"{v:.9g}" for v in c) + ")" for c in corners) + ");\n"
          + f"blocks (hex (0 1 2 3 4 5 6 7) ({counts[0]} {counts[1]} {counts[2]}) simpleGrading (1 1 1));\n"
          + "edges (); boundary (outer {type wall; faces ((0 4 7 3)(1 2 6 5)(0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7));});")
    regions = "\n".join(f"{n} {{ name {n}; }}" for n in NAMES)
    # Differences from prepare_duct_cfd.py: the features entry, and explicit snapping to it.
    # Implicit feature snapping (attempt 6) stays off.
    write("system/snappyHexMeshDict", '''castellatedMesh true; snap true; addLayers false;
geometry {duct.stl {type triSurfaceMesh; name duct; regions {''' + regions + '''}}}
castellatedMeshControls {
 maxLocalCells 1000000; maxGlobalCells 1500000; minRefinementCells 0; maxLoadUnbalance .1;
 nCellsBetweenLevels 3; features ({file "duct-rims.eMesh"; level 0;}); refinementSurfaces {duct {level (0 0); patchInfo {type wall;}}}
 resolveFeatureAngle 30; refinementRegions {}; locationInMesh (.15 .12 .15); allowFreeStandingZoneFaces true;
}
snapControls {nSmoothPatch 3; tolerance 2; nSolveIter 30; nRelaxIter 5; nFeatureSnapIter 10;
 implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap true;}
addLayersControls {}
meshQualityControls {
 maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
 minVol 1e-13; minTetQuality 1e-15; minArea -1; minTwist .02; minDeterminant .001;
 minFaceWeight .05; minVolRatio .01; minTriangleTwist -1; nSmoothScale 4; errorReduction .75;
}
mergeTolerance 1e-6;''')
    functions = "\n".join(f'''{n} {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
writeControl timeStep; writeInterval 1; regionType patch; name {n}; operation sum; fields (phi); writeFields false;}}''' for n in NAMES[1:])
    write("system/controlDict", '''application simpleFoam; startFrom startTime; startTime 0; stopAt endTime;
endTime 600; deltaT 1; writeControl timeStep; writeInterval 200; purgeWrite 1;
writeFormat ascii; writePrecision 10; runTimeModifiable false;
functions {''' + functions + '''}''')
    write("system/fvSchemes", '''ddtSchemes {default steadyState;}
gradSchemes {default cellLimited Gauss linear 1;}
divSchemes {default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind;
div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited .5;} interpolationSchemes {default linear;}
snGradSchemes {default limited .5;} wallDist {method meshWave;}''')
    write("system/fvSolution", '''solvers {p {solver GAMG; tolerance 1e-7; relTol .05; smoother GaussSeidel;}
"(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}}
SIMPLE {nNonOrthogonalCorrectors 1; consistent yes;}
relaxationFactors {fields {p .25;} equations {U .5; k .5; omega .5;}}''')
    write("system/decomposeParDict", "numberOfSubdomains 4; method scotch;")
    write("constant/transportProperties", "transportModel Newtonian; nu [0 2 -1 0 0 0 0] 1.5e-5;")
    write("constant/turbulenceProperties", "simulationType RAS; RAS {RASModel kOmegaSST; turbulence on; printCoeffs on;}")
    write("0/U", f'''dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {{inlet {{type flowRateInletVelocity; volumetricFlowRate constant {flow}; value uniform (0 60 0);}}
"(left.*|right.*)" {{type pressureInletOutletVelocity; value uniform (0 0 0);}}
walls {{type noSlip;}} outer {{type noSlip;}}}}''', "volVectorField")
    write("0/p", '''dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {inlet {type zeroGradient;} "(left.*|right.*)" {type fixedValue; value uniform 0;}
walls {type zeroGradient;} outer {type zeroGradient;}}''', "volScalarField")
    for name, dim, val, wall in (("k", "[0 2 -2 0 0 0 0]", 1.5, "kqRWallFunction"), ("omega", "[0 0 -1 0 0 0 0]", 100, "omegaWallFunction"),
                                 ("nut", "[0 2 -1 0 0 0 0]", 0, "nutkWallFunction")):
        inlet = "calculated" if name == "nut" else "fixedValue"
        outlet = "calculated" if name == "nut" else "inletOutlet"
        extra = "" if name == "nut" else f"inletValue uniform {val};"
        write("0/" + name, f'''dimensions {dim}; internalField uniform {val}; boundaryField {{
inlet {{type {inlet}; value uniform {val};}} "(left.*|right.*)" {{type {outlet}; {extra} value uniform {val};}}
"(walls|outer)" {{type {wall}; value uniform {val};}}}}''', "volScalarField")

    r1_labels = port_labels_r1(mesh.triangles_center, card)
    in_outlet_plane = np.abs(mesh.triangles_center[:, 2] - g["outlet_z_mm"]) < .01
    receipt = {
        "status": "prepared_not_solved", "scope": "stationary_delivery_duct_fixed_flow_free_discharge",
        "preparer_revision": 2, "geometry_revision": card.get("revision"),
        "reentrant_blend_mm": g.get("reentrant_blend_mm", 0),
        "alternator_subtraction_blend_mm": g.get("alternator_subtraction_blend_mm", 0),
        "fan_resolved": False, "intercooler_resolved": False, "engine_heat_transfer_resolved": False,
        "physical_validation": False, "flow_m3_s": flow, "background_cell_mm": cell_mm, "background_cells": counts,
        "source_sha256": sha256(Path(__file__).read_bytes()),
        "study": {"path": study.name, "sha256": sha256(study.read_bytes())},
        "native_surface_sha256": sha256(native.read_bytes()),
        "decimation": "none", "triangles": len(mesh.faces), "surface_volume_mm3": float(mesh.volume),
        "patch_triangles": {n: int((labels == n).sum()) for n in NAMES},
        "patch_area_mm2": {n: round(float(mesh.area_faces[labels == n].sum()), 1) for n in NAMES},
        "r1_label_rule_on_this_surface": {
            "meaning": "what the rule of prepare_duct_cfd.py would have labelled, for comparison only",
            "patch_area_mm2": {n: round(float(mesh.area_faces[r1_labels == n].sum()), 1) for n in NAMES},
            "outlet_plane_area_labelled_wall_mm2": round(float(
                mesh.area_faces[in_outlet_plane & (r1_labels == "walls")].sum()), 1),
        },
        "explicit_feature_edges": {
            "meaning": "the inlet and outlet rims only, where the port planes cut the constructive walls; "
                       "closed polylines at the voxel pitch",
            "constructive_model": {"auditor_sha256": sha256(AUDITOR.read_bytes()),
                                   "generator_sha256": audit.R2_PROGRAM_SHA256},
            "edges": len(feature_edges), "points": len(feature_points), "closed_loops": len(rims),
            "rim_length_mm": {name: round(float(np.linalg.norm(rim - np.roll(rim, -1, axis=0), axis=1).sum()), 1)
                              for name, rim in rims.items()},
            "surface_region_boundaries": {
                "meaning": "edges of the surface between two regions: zigzags along the voxel chamfers, "
                           "checked against the rims but not snapped to",
                "edges": len(edges), "connected_boundaries": len(boundary_lengths),
                "boundary_length_mm": sorted(round(float(v), 1) for v in boundary_lengths),
                "edges_by_region_pair": {"/".join(pair): edge_regions.count(pair) for pair in sorted(set(edge_regions))},
                "distance_to_constructive_rims_mm": {"mean": round(float(rim_gap.mean()), 3),
                                                     "max": round(float(rim_gap.max()), 3)},
            },
        },
        "files": {rel: sha256((output / rel).read_bytes()) for rel in (
            "constant/triSurface/duct.stl", "constant/triSurface/duct-rims.eMesh", "system/blockMeshDict",
            "system/snappyHexMeshDict", "system/controlDict", "system/fvSchemes", "system/fvSolution",
            "system/decomposeParDict", "constant/transportProperties", "constant/turbulenceProperties",
            "0/U", "0/p", "0/k", "0/omega", "0/nut")},
    }
    (output / "preparation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--native", type=Path, required=True, help="delivery-fluid-domain.stl as written by PicoGK, in mm")
    p.add_argument("--study", type=Path, required=True, help="study card the surface was generated from")
    p.add_argument("--output", type=Path, required=True, help="new case directory")
    p.add_argument("--flow", type=float, required=True, help="prescribed inlet flow, m3/s")
    p.add_argument("--cell-mm", type=float, default=5.0, help="uniform background cell size")
    a = p.parse_args()
    print(json.dumps({k: v for k, v in run(a.native, a.study, a.output, a.flow, a.cell_mm).items() if k != "files"}, indent=2))
