"""Reload real STEP charts and verify geometry, adjacency and source vertex fans."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import (TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL,
                       TopAbs_SOLID, TopAbs_WIRE, TopAbs_REVERSED)
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def indexed(shape, kind):
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, result)
    return result


def load(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise ValueError("STEP reload failed")
    result = reader.OneShape()
    if not BRepCheck_Analyzer(result).IsValid():
        raise ValueError("Reopened source chart is invalid")
    if indexed(result, TopAbs_SOLID).Extent():
        raise ValueError("Unexpected solid in observed source charts")
    return result


def connected_groups(nodes, adjacency):
    remaining = set(nodes)
    groups = []
    while remaining:
        start = remaining.pop()
        group, pending = {start}, [start]
        while pending:
            for neighbor in adjacency.get(pending.pop(), ()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    group.add(neighbor)
                    pending.append(neighbor)
        groups.append(tuple(sorted(group)))
    return groups


def inspect_source(path, vertices, source_faces, face_ids):
    source_vertices = np.unique(source_faces)
    if len(np.unique(vertices[source_vertices], axis=0)) != len(source_vertices):
        raise ValueError("Ambiguous coordinate-to-source mapping refused")
    expected_faces = {tuple(sorted(map(int, face))): int(identity)
                      for face, identity in zip(source_faces, face_ids)}
    if len(expected_faces) != len(source_faces):
        raise ValueError("Duplicate indexed source triangles refused")
    source_by_id = {int(identity): face for identity, face in zip(face_ids, source_faces)}
    expected_edges, incident = defaultdict(list), defaultdict(set)
    adjacency = defaultdict(set)
    for identity, face in zip(face_ids, source_faces):
        identity = int(identity)
        for a, b in zip(face, np.roll(face, -1)):
            expected_edges[tuple(sorted((int(a), int(b))))].append(identity)
            incident[int(a)].add(identity)
    for uses in expected_edges.values():
        if len(uses) == 2:
            a, b = uses
            adjacency[a].add(b)
            adjacency[b].add(a)
    expected_fans = Counter()
    for vertex, neighbors in incident.items():
        local_adjacency = {face: adjacency[face] & neighbors for face in neighbors}
        for group in connected_groups(neighbors, local_adjacency):
            expected_fans[(vertex, group)] += 1
    expected_components = Counter(connected_groups(face_ids, adjacency))
    shape = load(path)
    vm, em, fm, sm = (indexed(shape, kind) for kind in
                      (TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL))
    positions = []
    for i in range(1, vm.Extent() + 1):
        point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vm.FindKey(i)))
        positions.append([point.X(), point.Y(), point.Z()])
    distance, nearest = cKDTree(vertices[source_vertices]).query(np.asarray(positions))
    if distance.max() > 1e-6:
        raise ValueError("Actual STEP moved source coordinates")
    mapped = source_vertices[nearest]
    native_vertex_faces, native_edge_faces = defaultdict(set), defaultdict(list)
    native_face_ids, seen = {}, []
    maximum_normal_error = 0.0
    for i in range(1, fm.Extent() + 1):
        face = TopoDS.Face_s(fm.FindKey(i))
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Plane or indexed(face, TopAbs_WIRE).Extent() != 1:
            raise ValueError("Actual STEP changed a source triangle surface")
        walker = BRepTools_WireExplorer(BRepTools.OuterWire_s(face), face)
        corners, edge_indices, vertex_indices = [], [], []
        while walker.More():
            v = vm.FindIndex(walker.CurrentVertex())
            e = em.FindIndex(walker.Current())
            if not v or not e:
                raise ValueError("Native source topology lookup failed")
            corners.append(int(mapped[v - 1]))
            vertex_indices.append(v)
            edge_indices.append(e)
            walker.Next()
        key = tuple(sorted(corners))
        if len(corners) != 3 or key not in expected_faces:
            raise ValueError("Actual STEP introduced or changed a triangle")
        identity = expected_faces[key]
        native_face_ids[i] = identity
        seen.append(identity)
        for v in vertex_indices:
            native_vertex_faces[v].add(identity)
        for e in edge_indices:
            native_edge_faces[e].append(identity)
        original = vertices[source_by_id[identity]]
        normal = np.cross(original[1] - original[0], original[2] - original[0])
        normal /= np.linalg.norm(normal)
        direction = surface.Plane().Axis().Direction()
        native_normal = np.array([direction.X(), direction.Y(), direction.Z()])
        if face.Orientation() == TopAbs_REVERSED:
            native_normal = -native_normal
        maximum_normal_error = max(maximum_normal_error, abs(1 - float(normal @ native_normal)))
    if Counter(seen) != Counter(map(int, face_ids)) or maximum_normal_error > 1e-8:
        raise ValueError("Source triangle coverage or orientation changed")
    actual_edges = {}
    for i in range(1, em.Extent() + 1):
        edge = TopoDS.Edge_s(em.FindKey(i))
        if BRepAdaptor_Curve(edge).GetType() != GeomAbs_Line:
            raise ValueError("Source straight edge changed curve type")
        first = vm.FindIndex(TopExp.FirstVertex_s(edge))
        last = vm.FindIndex(TopExp.LastVertex_s(edge))
        key = tuple(sorted((int(mapped[first - 1]), int(mapped[last - 1]))))
        if key in actual_edges or key not in expected_edges:
            raise ValueError("Native source edge was duplicated or introduced")
        actual_edges[key] = sorted(native_edge_faces[i])
    if actual_edges != {key: sorted(value) for key, value in expected_edges.items()}:
        raise ValueError("Actual STEP changed source edge-to-face adjacency")
    actual_fans = Counter((int(mapped[i - 1]), tuple(sorted(native_vertex_faces[i])))
                          for i in range(1, vm.Extent() + 1))
    if actual_fans != expected_fans:
        raise ValueError("Actual native vertex fans differ from acquired face links")
    actual_components = Counter()
    for i in range(1, sm.Extent() + 1):
        component_faces = indexed(sm.FindKey(i), TopAbs_FACE)
        group = tuple(sorted(native_face_ids[fm.FindIndex(component_faces.FindKey(j))]
                             for j in range(1, component_faces.Extent() + 1)))
        actual_components[group] += 1
    if actual_components != expected_components:
        raise ValueError("Native shell grouping changed source edge components")
    return {"source_vertices": len(source_vertices), "native_vertices": vm.Extent(),
            "edges": em.Extent(), "faces": fm.Extent(), "shells": sm.Extent(),
            "source_boundary_edges": sum(len(uses) == 1 for uses in expected_edges.values()),
            "vertex_roundtrip_maximum_mm": float(distance.max()),
            "normal_roundtrip_maximum_error": maximum_normal_error,
            "checks": {"every_original_triangle_once": True, "original_orientation": True,
                       "straight_source_edges": True, "exact_source_edge_adjacency": True,
                       "exact_source_vertex_fans": True, "exact_source_shell_components": True,
                       "valid_reopened_native_shape": True, "zero_solids": True},
            "original_vertex_point_contacts_separated": vm.Extent() != len(source_vertices)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cad", "arrays", "paper", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing shell verification output refused")
    contract_path = args.paper / "registered-contract.json"
    partition_path = args.paper / "registered-partitions.json"
    if digest(contract_path) != "49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779" or digest(partition_path) != "bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824":
        raise SystemExit("Frozen source contract mismatch")
    contract = json.loads(contract_path.read_text())
    if digest(args.arrays) != contract["arrays_sha256"]:
        raise SystemExit("Original arrays mismatch")
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    partitions = json.loads(partition_path.read_text())["partitions"]
    controls = {}
    for name, expected in (("shared-square-control.step", [4, 5, 2, 1]),
                           ("point-contact-control.step", [6, 6, 2, 2])):
        shape = load(args.cad / name)
        measured = [indexed(shape, kind).Extent() for kind in (TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL)]
        if measured != expected:
            raise ValueError("STEP topology control failed: " + name)
        controls[name] = measured
    reports = []
    for index in range(1, 4):
        ident = f"stud_passage_{index}_wall_candidate"
        entry = next(p for p in partitions if p["id"] == ident)
        partition = args.paper / entry["file"]
        if digest(partition) != entry["sha256"]:
            raise ValueError("Original source partition changed")
        with np.load(partition, allow_pickle=False) as data:
            selected = data["selected_source_face_ids"]
        path = args.cad / (ident + "-source-shells.step")
        before = digest(path)
        report = inspect_source(path, vertices, faces[selected], selected)
        if digest(path) != before:
            raise ValueError("Actual STEP changed during verification")
        report.update(region=ident, actual_step_sha256=before)
        reports.append(report)
    args.output.mkdir(parents=True)
    result = {"regions": reports, "controls": controls, "verifier_source_sha256": digest(__file__),
              "acquired_geometry_preserved": True, "source_index_array_modified": False,
              "chart_vertex_point_contacts_are_separated": True,
              "charts_are_physical_components": False, "full_head_created": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    with (args.output / "verification.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
