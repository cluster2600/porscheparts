"""Build manifold CAD charts from exact source facets; split only vertex fans."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeEdge,
                               BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.TopoDS import TopoDS, TopoDS_Compound, TopoDS_Shell
from OCP.gp import gp_Pnt


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def atlas(vertices, faces):
    if len(np.unique(vertices, axis=0)) != len(vertices):
        raise ValueError("Coincident distinct source vertices need separate admission; no welding")
    triangle = vertices[faces]
    if np.any(np.linalg.norm(np.cross(triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]), axis=1) == 0):
        raise ValueError("Degenerate source triangle refused")
    corner_parent = np.arange(faces.size)
    face_parent = np.arange(len(faces))

    def find(parent, index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def join(parent, a, b):
        parent[find(parent, a)] = find(parent, b)

    edges = {}
    for row, triangle_ids in enumerate(faces):
        for column in range(3):
            a, b = int(triangle_ids[column]), int(triangle_ids[(column + 1) % 3])
            key = tuple(sorted((a, b)))
            edges.setdefault(key, []).append((row, a < b))
    for edge, uses in edges.items():
        if len(uses) > 2:
            raise ValueError("Nonmanifold source edge refused")
        if len(uses) == 2:
            (a, forward_a), (b, forward_b) = uses
            if forward_a == forward_b:
                raise ValueError("Inconsistent source winding refused")
            join(face_parent, a, b)
            for vertex in edge:
                ca = a * 3 + int(np.flatnonzero(faces[a] == vertex)[0])
                cb = b * 3 + int(np.flatnonzero(faces[b] == vertex)[0])
                join(corner_parent, ca, cb)
    root = np.array([find(corner_parent, i) for i in range(faces.size)])
    unique, inverse = np.unique(root, return_inverse=True)
    source_vertex = faces.ravel()[unique]
    chart_faces = inverse.reshape(faces.shape)
    if not np.array_equal(source_vertex[chart_faces], faces):
        raise ValueError("Corner provenance changed")
    components = np.array([find(face_parent, i) for i in range(len(faces))])
    chart_edges = np.sort(np.concatenate((chart_faces[:, [0, 1]], chart_faces[:, [1, 2]], chart_faces[:, [2, 0]])), axis=1)
    unique_edges, counts = np.unique(chart_edges, axis=0, return_counts=True)
    degree = np.bincount(unique_edges[counts == 1].ravel(), minlength=len(source_vertex))
    if np.any((degree != 0) & (degree != 2)) or len(unique_edges) != len(edges):
        raise ValueError("Fan decomposition did not preserve manifold edge charts")
    multiplicity = np.bincount(source_vertex, minlength=len(vertices))
    report = {"source_vertices": len(vertices), "native_chart_vertices": len(source_vertex),
              "source_vertices_split_into_fans": int((multiplicity > 1).sum()),
              "additional_coincident_chart_vertices": len(source_vertex) - len(vertices),
              "source_faces": len(faces), "source_edges": len(edges),
              "boundary_edges": int((counts == 1).sum()),
              "edge_connected_components": len(np.unique(components)),
              "source_face_and_edge_adjacency_preserved": True,
              "source_corner_mapping_exact": True, "coordinates_changed": False,
              "vertex_point_contacts_separated": bool(np.any(multiplicity > 1)),
              "original_vertex_contact_topology_preserved": not bool(np.any(multiplicity > 1))}
    return vertices[source_vertex], chart_faces, source_vertex, components, report


def native_shape(vertices, faces, components):
    native_vertices = [BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex() for p in vertices]
    edge_cache = {}
    builder = BRep_Builder()
    result = TopoDS_Compound()
    builder.MakeCompound(result)
    shells = {}
    for group in np.unique(components):
        shell = TopoDS_Shell()
        builder.MakeShell(shell)
        shells[int(group)] = shell
    for row, triangle in enumerate(faces):
        wire = BRepBuilderAPI_MakeWire()
        for a, b in zip(triangle, np.roll(triangle, -1)):
            a, b = int(a), int(b)
            key = tuple(sorted((a, b)))
            if key not in edge_cache:
                edge = BRepBuilderAPI_MakeEdge(native_vertices[key[0]], native_vertices[key[1]])
                if not edge.IsDone():
                    raise ValueError("Exact shared edge construction failed")
                edge_cache[key] = edge.Edge()
            edge = edge_cache[key] if a < b else TopoDS.Edge_s(edge_cache[key].Reversed())
            wire.Add(edge)
        if not wire.IsDone():
            raise ValueError("Exact source wire construction failed")
        face = BRepBuilderAPI_MakeFace(wire.Wire(), True)
        if not face.IsDone() or not BRepCheck_Analyzer(face.Face()).IsValid():
            raise ValueError("Exact source face construction failed")
        builder.Add(shells[int(components[row])], face.Face())
    for shell in shells.values():
        if not BRepCheck_Analyzer(shell).IsValid():
            raise ValueError("Native manifold chart failed validity")
        builder.Add(result, shell)
    if not BRepCheck_Analyzer(result).IsValid():
        raise ValueError("Native chart compound failed validity")
    return result


def export(shape, path):
    writer = STEPControl_Writer()
    if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone or writer.Write(str(path)) != IFSelect_RetDone:
        raise ValueError("STEP export failed")


def controls(output):
    vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    v, f, _, c, square = atlas(vertices, faces)
    if (len(v), square["source_edges"], square["boundary_edges"]) != (4, 5, 4):
        raise ValueError("Shared-edge square control failed")
    export(native_shape(v, f, c), output / "shared-square-control.step")
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]], float)
    faces = np.array([[0, 1, 2], [0, 3, 4]])
    v, f, source, c, contact = atlas(vertices, faces)
    if len(v) != 6 or len(np.unique(source)) != 5 or contact["edge_connected_components"] != 2:
        raise ValueError("Point-contact fan split control failed")
    export(native_shape(v, f, c), output / "point-contact-control.step")
    failures = {}
    for name, points, triangles, expected in (
        ("inconsistent_winding", np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], float),
         np.array([[0, 1, 2], [0, 1, 3]]), "Inconsistent source winding"),
        ("nonmanifold_edge", np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]], float),
         np.array([[0, 1, 2], [1, 0, 3], [0, 1, 4]]), "Nonmanifold source edge"),
        ("degenerate_triangle", vertices, np.array([[1, 0, 3]]), "Degenerate source triangle"),
        ("coincident_distinct_ids", np.vstack((vertices[:3], vertices[:3])),
         np.array([[0, 1, 2], [3, 4, 5]]), "Coincident distinct source vertices")):
        try:
            atlas(points, triangles)
        except ValueError as error:
            failures[name] = expected in str(error)
        else:
            failures[name] = False
    if not all(failures.values()):
        raise ValueError("Source refusal controls failed")
    return {"square": square, "point_contact": contact, "refusals": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preparation", "paper", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing source-shell output refused")
    contract = args.paper / "registered-contract.json"
    partitions = args.paper / "registered-partitions.json"
    if digest(contract) != "49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779" or digest(partitions) != "bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824":
        raise SystemExit("Frozen source contract mismatch")
    registered = json.loads(partitions.read_text())["partitions"]
    args.output.mkdir(parents=True)
    inputs = {f"region_{i}": digest(args.preparation / f"stud_passage_{i}_wall_candidate-reference.npz") for i in range(1, 4)}
    save(args.output / "plan.json", {"inputs_sha256": inputs, "source_sha256": digest(__file__),
         "construction": "One native vertex per original edge-connected incident-face fan; one native edge per original edge; exact planar triangle faces.",
         "source_coordinate_change_allowed_mm": 0.0, "roundtrip_coordinate_limit_mm": 1e-6,
         "automatic_welding_or_healing": False, "physical_acceptance": False})
    save(args.output / "controls.json", controls(args.output))
    reports = []
    for index in range(1, 4):
        ident = f"stud_passage_{index}_wall_candidate"
        entry = next(p for p in registered if p["id"] == ident)
        partition = args.paper / entry["file"]
        if digest(partition) != entry["sha256"]:
            raise ValueError("Registered mask changed")
        with np.load(partition, allow_pickle=False) as data:
            selected = data["selected_source_face_ids"]
        with np.load(args.preparation / (ident + "-reference.npz"), allow_pickle=False) as data:
            vertices, faces = data["vertices"], data["triangles"]
            source_vertices, source_faces = data["source_vertex_ids"], data["source_face_ids"]
        if not np.array_equal(selected, source_faces):
            raise ValueError("Source face membership changed")
        v, f, vertex_map, components, report = atlas(vertices, faces)
        np.savez_compressed(args.output / (ident + "-chart-provenance.npz"), vertices=v, triangles=f,
                            original_source_vertex_ids=source_vertices[vertex_map],
                            original_source_face_ids=source_faces, component_labels=components)
        export(native_shape(v, f, components), args.output / (ident + "-source-shells.step"))
        report.update(region=ident, step_sha256=digest(args.output / (ident + "-source-shells.step")),
                      solids_created=0, functional_anatomy_identified=False)
        reports.append(report)
    save(args.output / "construction.json", {"regions": reports, "source_geometry_modified": False,
         "charts_are_physical_parts": False, "physical_acceptance": False, "manufacturing_authorized": False})
    print(json.dumps(reports))


if __name__ == "__main__":
    main()
