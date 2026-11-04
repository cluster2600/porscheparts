"""OCCT controls for straight cylindrical cavities and partial-CAD abstention.

This deliberately restricted adapter is not the paper's full GWS algorithm:
face-set enumeration, general hole expansion and learned models are not run.
"""
from __future__ import annotations

import numpy as np

from scripts.scan_feature_study import cavity_variance, inspect_circle


def shapes(shape, kind):
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_WIRE
    cast = {TopAbs_FACE: TopoDS.Face_s, TopAbs_EDGE: TopoDS.Edge_s, TopAbs_WIRE: TopoDS.Wire_s}
    iterator = TopExp_Explorer(shape, kind)
    result = []
    while iterator.More():
        result.append(cast[kind](iterator.Current()) if kind in cast else iterator.Current())
        iterator.Next()
    return result


def wire_points(wire):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    result = []
    for edge in shapes(wire, TopAbs_EDGE):
        curve = BRepAdaptor_Curve(edge)
        # Fixed dense sampling also handles exact circular arcs represented by one edge.
        for parameter in np.linspace(curve.FirstParameter(), curve.LastParameter(), 32, endpoint=False):
            point = curve.Value(float(parameter))
            result.append([point.X(), point.Y(), point.Z()])
    return np.array(result)


def face_triangles(face):
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopAbs import TopAbs_REVERSED
    location = TopLoc_Location()
    mesh = BRep_Tool.Triangulation_s(face, location)
    if mesh is None:
        raise ValueError("face has no tessellation")
    transform = location.Transformation()
    points = [mesh.Node(i).Transformed(transform) for i in range(1, mesh.NbNodes() + 1)]
    vertices = np.array([[p.X(), p.Y(), p.Z()] for p in points])
    indices = np.array([mesh.Triangle(i).Get() for i in range(1, mesh.NbTriangles() + 1)]) - 1
    tri = vertices[indices]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if face.Orientation() == TopAbs_REVERSED:
        cross *= -1
    size = np.linalg.norm(cross, axis=1)
    valid = size > 1e-12
    return tri.mean(axis=1)[valid], cross[valid] / size[valid, None], size[valid] / 2


def inspect_shape(shape):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Circle
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_WIRE, TopAbs_SOLID
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    valid = BRepCheck_Analyzer(shape).IsValid()
    solids = len(shapes(shape, TopAbs_SOLID))
    faces = shapes(shape, TopAbs_FACE)
    edge_map = TopTools_IndexedMapOfShape()
    face_edges, edge_faces, edge_uses = [], {}, {}
    for index, face in enumerate(faces):
        ids = set()
        for edge in shapes(face, TopAbs_EDGE):
            edge_id = edge_map.Add(edge)
            ids.add(edge_id)
            edge_faces.setdefault(edge_id, set()).add(index)
            edge_uses[edge_id] = edge_uses.get(edge_id, 0) + 1
        face_edges.append(ids)
    # A periodic cylinder seam has two uses in the same face, not two distinct faces.
    oriented_volume = None
    if valid and solids == 1:
        volume = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, volume)
        oriented_volume = float(volume.Mass())
    admitted = (valid and solids == 1 and oriented_volume is not None
                and np.isfinite(oriented_volume) and oriented_volume > 0
                and all(count == 2 for count in edge_uses.values()))
    rims = []
    for index, face in enumerate(faces):
        outer = BRepTools.OuterWire_s(face)
        for wire in shapes(face, TopAbs_WIRE):
            if wire.IsSame(outer):
                continue
            record = {"face_index": index, "closed_wire": wire.Closed(), "state": "rim_only"}
            try:
                record.update(inspect_circle(wire_points(wire)))
            except ValueError as error:
                record["fit_error"] = str(error)
            adjacent = set()
            for edge in shapes(wire, TopAbs_EDGE):
                adjacent.update(edge_faces[edge_map.FindIndex(edge)])
            record["wall_face_indices"] = sorted(adjacent - {index})
            record["through_or_blind"] = "unresolved"
            rims.append(record)
    groups = {}
    for record in rims:
        if not admitted:
            record["state"] = "abstain_partial_or_nonmanifold_CAD"
            continue
        walls = record["wall_face_indices"]
        if (not record.get("circular_rim_candidate") or len(walls) != 1
                or BRepAdaptor_Surface(faces[walls[0]]).GetType() != GeomAbs_Cylinder):
            record["state"] = "abstain_unsupported_wall_topology"
            continue
        groups.setdefault(walls[0], []).append(record)
    detections = []
    if groups:
        BRepMesh_IncrementalMesh(shape, .05, False, .15, True)
    for wall_id, mouths in groups.items():
        wall = faces[wall_id]
        centers, normals, areas = face_triangles(wall)
        hollow = cavity_variance(centers, normals, areas)
        terminal = set().union(*(edge_faces[e] for e in face_edges[wall_id])) - {wall_id}
        simple = len(terminal) == 2
        for terminal_id in terminal:
            face = faces[terminal_id]
            if BRepAdaptor_Surface(face).GetType() != GeomAbs_Plane:
                simple = False
                continue
            outer_edges = {edge_map.FindIndex(e) for e in shapes(BRepTools.OuterWire_s(face), TopAbs_EDGE)}
            # An annular step sharing its outer boundary with this cylinder is not a blind cap.
            if len(shapes(face, TopAbs_WIRE)) > 1:
                outer_curves = shapes(BRepTools.OuterWire_s(face), TopAbs_EDGE)
                if (outer_edges & face_edges[wall_id]
                        or all(BRepAdaptor_Curve(e).GetType() == GeomAbs_Circle for e in outer_curves)):
                    simple = False
        state = ("abstain_unsupported_terminal_topology" if not simple else
                 "rejected_convex_or_nonhollow" if not hollow["hollow_candidate"] else
                 "straight_cylindrical_cavity_candidate")
        classification = ("through" if len(mouths) == 2 else "blind" if len(mouths) == 1 else "unresolved")
        if state != "straight_cylindrical_cavity_candidate":
            classification = "unresolved"
        for mouth in mouths:
            mouth.update(state=state, through_or_blind=classification)
        detections.append({"wall_face_index": wall_id, "mouths": len(mouths), "state": state,
                           "through_or_blind": classification, "cavity_statistic": hollow})
    return {"valid": valid, "faces": len(faces), "solids": solids,
            "oriented_volume_mm3": oriented_volume,
            "solid_hole_classification_admitted": admitted, "rims": rims, "cavities": detections,
            "scope": "straight cylindrical controls and rim candidates; not a full GWS reproduction",
            "physical_acceptance": False}


def synthetic_controls():
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    plate = BRepPrimAPI_MakeBox(40., 30., 10.).Shape()

    def cylinder(radius, z, height, x=12.):
        return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, 15, z), gp_Dir(0, 0, 1)), radius, height).Shape()

    through = BRepAlgoAPI_Cut(plate, cylinder(4, -1, 12)).Shape()
    blind = BRepAlgoAPI_Cut(plate, cylinder(4, 3, 8)).Shape()
    boss = BRepAlgoAPI_Fuse(plate, cylinder(4, 10, 5)).Shape()
    two = BRepAlgoAPI_Cut(through, cylinder(3, -1, 12, 28)).Shape()
    stepped = BRepAlgoAPI_Cut(BRepAlgoAPI_Cut(plate, cylinder(5, 6, 5)).Shape(), cylinder(3, 3, 8)).Shape()
    controls = []
    for name, shape, expected, volume in [
            ("plate", plate, [], 12000.), ("through", through, ["through"], 12000 - 160 * np.pi),
            ("blind", blind, ["blind"], 12000 - 112 * np.pi),
            ("boss", boss, [], 12000 + 80 * np.pi),
            ("two_through", two, ["through", "through"], 12000 - 250 * np.pi),
            ("stepped_blind_unsupported", stepped, [], 12000 - 127 * np.pi)]:
        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, properties)
        assert abs(properties.Mass() - volume) < 1e-6, (name, "fixture volume mismatch")
        report = inspect_shape(shape)
        actual = sorted(r["through_or_blind"] for r in report["cavities"]
                        if r["state"] == "straight_cylindrical_cavity_candidate")
        assert actual == expected, (name, actual, expected)
        controls.append({"id": name, "expected": expected, "actual": actual, "passed": True,
                         "independent_analytic_fixture_volume_check": True, "report": report})
    return controls
