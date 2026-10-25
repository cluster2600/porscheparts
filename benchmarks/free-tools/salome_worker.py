"""Native SALOME/NETGEN volume comparison; never heals or replaces input faces."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re

from ft_common import finite, load, new_directory, receipt, sha256, write
from ft_geometry import closed_surface, read_surface, verify_tets


def fixture(kind):
    if kind == "cube":
        points = [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ]
        faces = [
            [0, 2, 1],
            [0, 3, 2],
            [4, 5, 6],
            [4, 6, 7],
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ]
        return points, faces, {"support": [0, 1], "loaded": [2, 3]}
    points, faces = [], []
    count = 16
    for z, radius in ((0, 1), (0, 0.5), (1, 1), (1, 0.5)):
        points.extend(
            [
                [
                    radius * math.cos(2 * math.pi * i / count),
                    radius * math.sin(2 * math.pi * i / count),
                    z,
                ]
                for i in range(count)
            ]
        )
    groups = {"support": [], "loaded": [], "bore": []}
    for i in range(count):
        j = (i + 1) % count
        bi, bj, ii, ij, ti, tj, ui, uj = (
            i,
            j,
            count + i,
            count + j,
            2 * count + i,
            2 * count + j,
            3 * count + i,
            3 * count + j,
        )
        groups["support"].extend([len(faces), len(faces) + 1])
        faces.extend([[bi, ij, bj], [bi, ii, ij]])
        groups["loaded"].extend([len(faces), len(faces) + 1])
        faces.extend([[ti, tj, uj], [ti, uj, ui]])
        faces.extend([[ti, bi, bj], [ti, bj, tj]])
        groups["bore"].extend([len(faces), len(faces) + 1])
        faces.extend([[ui, uj, ij], [ui, ij, ii]])
    return points, faces, groups


def write_inp(path, points, tets, groups):
    with Path(path).open("x") as stream:
        stream.write("*NODE\n")
        for i, point in enumerate(points, 1):
            stream.write(
                str(i)
                + ", "
                + ", ".join(format(finite(x), ".17g") for x in point)
                + "\n"
            )
        stream.write("*ELEMENT, TYPE=C3D4\n")
        for i, tet in enumerate(tets, 1):
            stream.write(str(i) + ", " + ", ".join(str(x + 1) for x in tet) + "\n")
        for name, nodes in groups.items():
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name) or not nodes:
                raise ValueError("nonempty named boundary groups required")
            stream.write("*NSET, NSET=" + name + "\n")
            for start in range(0, len(nodes), 12):
                stream.write(
                    ", ".join(str(x + 1) for x in nodes[start : start + 12]) + "\n"
                )


def read_inp(path):
    points, tets, groups = [], [], {}
    section = None
    for line in Path(path).read_text().splitlines():
        if line.startswith("*NODE"):
            section = "nodes"
        elif line.startswith("*ELEMENT"):
            if line != "*ELEMENT, TYPE=C3D4":
                raise ValueError("C3D4 export required")
            section = "tets"
        elif line.startswith("*NSET, NSET="):
            section = line.split("=", 1)[1]
            groups[section] = []
        elif line.startswith("*"):
            raise ValueError("unsupported export section")
        elif line.strip():
            values = [x.strip() for x in line.split(",")]
            if section == "nodes":
                if int(values[0]) != len(points) + 1:
                    raise ValueError("nonsequential node IDs")
                points.append([finite(float(x)) for x in values[1:]])
            elif section == "tets":
                if int(values[0]) != len(tets) + 1:
                    raise ValueError("nonsequential element IDs")
                tets.append([int(x) - 1 for x in values[1:]])
            else:
                groups[section].extend(int(x) - 1 for x in values)
    return points, tets, groups


def calculix_tets(salome_tets):
    if any(len(tet) != 4 for tet in salome_tets):
        raise ValueError("linear four-node SALOME tetrahedra required")
    # SMDS 9.16 Tetra_F makes (0,1,2) outward; C3D4 uses the opposite convention.
    return [[tet[0], tet[2], tet[1], tet[3]] for tet in salome_tets]


def mesh_surface(points, faces, groups, output, max_size):
    closed_surface(points, faces)
    finite(max_size, positive=True)
    for name, indices in groups.items():
        if (
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name)
            or not indices
            or any(type(i) is not int or i < 0 or i >= len(faces) for i in indices)
        ):
            raise ValueError("explicit valid face groups required")
    output = new_directory(output)
    print("Initializing the sessionless SALOME runtime", flush=True)
    import salome

    salome.salome_init_without_session()
    import SMESH
    from salome.smesh import smeshBuilder

    smesh = smeshBuilder.New()
    print("Building the imported surface mesh", flush=True)
    mesh = smesh.Mesh()
    node_ids = [mesh.AddNode(*point) for point in points]
    face_ids = [mesh.AddFace([node_ids[i] for i in face]) for face in faces]
    original_groups = {}
    for name, indices in groups.items():
        group = mesh.CreateEmptyGroup(SMESH.FACE, name)
        group.Add([face_ids[i] for i in indices])
        original_groups[name] = set(group.GetIDs())
    tetra = mesh.Tetrahedron(algo=smeshBuilder.NETGEN)
    parameters = tetra.Parameters()
    parameters.SetMaxSize(max_size)
    parameters.SetOptimize(False)
    print("Computing the NETGEN volume", flush=True)
    if not mesh.Compute():
        raise ValueError("NETGEN volume computation failed")
    for i, node_id in enumerate(node_ids):
        if list(mesh.GetNodeXYZ(node_id)) != list(points[i]):
            raise ValueError("input node moved")
    for face_id, face in zip(face_ids, faces):
        if list(mesh.GetElemNodes(face_id)) != [node_ids[i] for i in face]:
            raise ValueError("input face changed")
    if any(
        set(group.GetIDs()) != original_groups[group.GetName()]
        for group in mesh.GetGroups()
    ):
        raise ValueError("boundary group changed")
    all_ids = sorted(mesh.GetNodesId())
    offsets = {node_id: i for i, node_id in enumerate(all_ids)}
    vertices = [list(mesh.GetNodeXYZ(i)) for i in all_ids]
    raw_tets = [
        [offsets[i] for i in mesh.GetElemNodes(element)]
        for element in mesh.GetElementsByType(SMESH.VOLUME)
    ]
    mesh.ExportMED(str(output / "native.med"), 0)
    write(output / "native-mesh.json", {"points": vertices, "salome_tets": raw_tets})
    tets = calculix_tets(raw_tets)
    checks = verify_tets(vertices, tets, points, faces)
    sets = {
        name: sorted({offsets[node_ids[i]] for index in indices for i in faces[index]})
        for name, indices in groups.items()
    }
    write_inp(output / "mesh.inp", vertices, tets, sets)
    if read_inp(output / "mesh.inp") != (vertices, tets, sets):
        raise ValueError("CalculiX conversion changed nodes, elements or groups")
    checks.update(
        {
            "group_membership_preserved": True,
            "calculix_roundtrip": True,
            "salome_to_calculix_permutation": [0, 2, 1, 3],
            "max_size_mm": max_size,
        }
    )
    write(
        output / "receipt.json",
        receipt(
            "salome-netgen",
            "volume_comparison_completed",
            [],
            outputs=[
                {"id": name, "sha256": sha256(output / name)}
                for name in ("mesh.inp", "native.med", "native-mesh.json")
            ],
            checks=checks,
            limitations=[
                "Mesh comparison only; no native FEM solve or physical qualification.",
                "Carrier equilibrium, stress-energy and existing interface certificates remain separate gates.",
            ],
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["controls", "mesh"])
    parser.add_argument("--surface", type=Path)
    parser.add_argument("--groups", type=Path)
    parser.add_argument("--units", choices=["mm"], required=True)
    parser.add_argument("--max-size", type=float, default=0.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "controls":
        output = new_directory(args.output)
        for name in ("cube", "bore"):
            mesh_surface(*fixture(name), output / name, 0.5)
        write(
            output / "receipt.json",
            receipt(
                "salome-controls",
                "passed",
                [],
                checks={
                    "cube": True,
                    "bore": True,
                    "runtime": "SALOME 9.16.0; NETGEN only",
                },
            ),
        )
    else:
        if not args.surface or not args.groups:
            parser.error("mesh requires surface and independently authored face groups")
        before = sha256(args.surface)
        mesh_surface(
            *read_surface(args.surface), load(args.groups), args.output, args.max_size
        )
        if before != sha256(args.surface):
            raise ValueError("input surface changed")


if __name__ == "__main__":
    main()
