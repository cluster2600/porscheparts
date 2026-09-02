#!/usr/bin/env python3
"""Smoke hermetique d'un maillage OCC 3D synthetique avec Gmsh."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pwd
import re
import subprocess
from importlib.metadata import version
from pathlib import Path

import gmsh


APP_ROOT = Path("/opt/gmsh-mesh-f35")
EXPECTED_UID = 9135
EXPECTED_GID = 9135
EXPECTED_GMSH = "4.15.2"
EXPECTED_LIBGMSH_SHA256 = "9db3090d3b720c57b76bcbfa01d13854823ae2698c91343c20bdd4c2b81f6317"
LIBGMSH_PATH = Path("/usr/local/lib/libgmsh.so.4.15")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_runtime_contract() -> dict[str, object]:
    account = pwd.getpwuid(os.getuid())
    require(os.getuid() == EXPECTED_UID, "unexpected runtime uid")
    require(os.getgid() == EXPECTED_GID, "unexpected runtime gid")
    require(account.pw_name == "gmsh-mesh", "unexpected runtime account")
    require(os.environ.get("HOME") == "/tmp", "HOME must be /tmp")
    require(
        os.environ.get("XDG_CACHE_HOME") == "/tmp/gmsh-mesh-f35-cache",
        "unexpected cache boundary",
    )
    require(not os.access(APP_ROOT, os.W_OK), "application payload must be read-only")
    require(version("gmsh") == EXPECTED_GMSH, "unexpected Gmsh version")
    require(gmsh.GMSH_API_VERSION == EXPECTED_GMSH, "unexpected Gmsh API version")
    require(LIBGMSH_PATH.is_file(), "libgmsh is absent")
    libgmsh_sha256 = hashlib.sha256(LIBGMSH_PATH.read_bytes()).hexdigest()
    require(libgmsh_sha256 == EXPECTED_LIBGMSH_SHA256, "unexpected libgmsh hash")
    ldd = subprocess.run(
        ["ldd", str(LIBGMSH_PATH)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    require("not found" not in ldd.stdout.lower(), "unresolved libgmsh dependency")

    requirement = (APP_ROOT / "requirements.txt").read_text(encoding="utf-8")
    require("gmsh==4.15.2" in requirement, "Gmsh requirement is not exact")
    require(
        "4076a948ce22625330d1413d4982e22b5c69fc2f0f7951f5df64c778cf54108c"
        in requirement,
        "Gmsh wheel hash is absent",
    )

    hash_lines = [
        line.strip()
        for line in (APP_ROOT / "system-packages.sha256").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    require(len(hash_lines) == 24, "unexpected system package hash count")
    require(
        all(re.fullmatch(r"[0-9a-f]{64}  [^/ ]+\.deb", line) for line in hash_lines),
        "malformed system package hash lock",
    )

    route = Path("/proc/net/route")
    if route.exists():
        default_route = any(
            fields[1] == "00000000"
            for line in route.read_text(encoding="ascii").splitlines()[1:]
            if len(fields := line.split()) >= 2
        )
        require(not default_route, "runtime must not expose a default network route")

    bundled_files = sorted(
        str(path.relative_to(APP_ROOT))
        for path in APP_ROOT.rglob("*")
        if path.is_file()
    )
    require(
        bundled_files == ["requirements.txt", "smoke.py", "system-packages.sha256"],
        "unexpected application payload",
    )
    return {
        "gmsh_api_version": gmsh.GMSH_API_VERSION,
        "libgmsh_sha256": libgmsh_sha256,
        "resolved_elf_dependencies": True,
        "runtime_gid": os.getgid(),
        "runtime_uid": os.getuid(),
    }


def build_synthetic_mesh() -> dict[str, object]:
    gmsh.initialize(
        ["gmsh-mesh-f35-smoke", "-nopopup"],
        readConfigFiles=False,
        run=False,
    )
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads1D", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads2D", 1)
        gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
        gmsh.option.setNumber("Mesh.RandomSeed", 1)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.logger.start()
        gmsh.model.add("synthetic_occ_cylinder")

        length = 0.05
        radius = 0.01
        volume = gmsh.model.occ.addCylinder(0.0, 0.0, 0.0, length, 0.0, 0.0, radius)
        gmsh.model.occ.synchronize()

        surfaces = [tag for dimension, tag in gmsh.model.getBoundary([(3, volume)]) if dimension == 2]
        require(len(surfaces) == 3, "synthetic OCC cylinder must expose three surfaces")

        inlet: list[int] = []
        outlet: list[int] = []
        wall: list[int] = []
        for surface in surfaces:
            centre_x = gmsh.model.occ.getCenterOfMass(2, surface)[0]
            if math.isclose(centre_x, 0.0, abs_tol=1.0e-9):
                inlet.append(surface)
            elif math.isclose(centre_x, length, abs_tol=1.0e-9):
                outlet.append(surface)
            else:
                wall.append(surface)

        require(len(inlet) == len(outlet) == len(wall) == 1, "surface classification failed")
        require(set(inlet + outlet + wall) == set(surfaces), "surface groups are incomplete")
        require(len(set(inlet) & set(outlet)) == 0, "inlet and outlet overlap")
        require(len(set(inlet) & set(wall)) == 0, "inlet and wall overlap")
        require(len(set(outlet) & set(wall)) == 0, "outlet and wall overlap")
        groups = {
            "fluid_volume": (3, [volume]),
            "inlet": (2, inlet),
            "outlet": (2, outlet),
            "wall": (2, wall),
        }
        for name, (dimension, entities) in groups.items():
            physical_tag = gmsh.model.addPhysicalGroup(dimension, entities)
            gmsh.model.setPhysicalName(dimension, physical_tag, name)
            require(
                sorted(gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag))
                == sorted(entities),
                f"physical group membership mismatch: {name}",
            )

        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.004)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.004)
        gmsh.model.mesh.generate(3)

        node_tags, _, _ = gmsh.model.mesh.getNodes()
        require(len(node_tags) > 0, "mesh contains no nodes")

        element_types = gmsh.model.mesh.getElementTypes(3)
        require(len(element_types) > 0, "mesh contains no volume element type")
        element_count = 0
        minimum_jacobian = math.inf
        minimum_det_jac = math.inf
        minimum_sicn = math.inf
        for element_type in element_types:
            element_name, dimension, order, node_count, _, primary_node_count = (
                gmsh.model.mesh.getElementProperties(element_type)
            )
            require(
                dimension == 3
                and order == 1
                and node_count == 4
                and primary_node_count == 4
                and "tetra" in element_name.lower(),
                "smoke expects first-order tetrahedra only",
            )
            element_tags, _ = gmsh.model.mesh.getElementsByType(element_type)
            require(len(element_tags) > 0, "volume element type is empty")
            element_count += len(element_tags)
            min_det_jac = gmsh.model.mesh.getElementQualities(element_tags, "minDetJac")
            min_sicn = gmsh.model.mesh.getElementQualities(element_tags, "minSICN")
            require(
                len(min_det_jac) == len(element_tags)
                and all(math.isfinite(value) and value > 0.0 for value in min_det_jac),
                "non-positive minDetJac detected",
            )
            require(
                len(min_sicn) == len(element_tags)
                and all(math.isfinite(value) and value > 0.0 for value in min_sicn),
                "non-positive minSICN detected",
            )
            minimum_det_jac = min(minimum_det_jac, min(min_det_jac))
            minimum_sicn = min(minimum_sicn, min(min_sicn))
            local_coordinates, _ = gmsh.model.mesh.getIntegrationPoints(element_type, "Gauss1")
            _, determinants, _ = gmsh.model.mesh.getJacobians(
                element_type, local_coordinates
            )
            require(len(determinants) > 0, "Jacobian evaluation is empty")
            require(
                all(math.isfinite(value) and value > 0.0 for value in determinants),
                "non-positive or non-finite Jacobian detected",
            )
            minimum_jacobian = min(minimum_jacobian, min(determinants))

        require(element_count > 0, "mesh contains no volume element")
        physical_names = sorted(
            gmsh.model.getPhysicalName(dimension, tag)
            for dimension, tag in gmsh.model.getPhysicalGroups()
        )
        require(physical_names == sorted(groups), "physical groups are incomplete")

        messages = gmsh.logger.get()
        require(
            not any("error" in message.lower() or "warning" in message.lower() for message in messages),
            "Gmsh emitted a warning or error",
        )
        gmsh.logger.stop()

        return {
            "element_count_3d": element_count,
            "element_types_3d": [int(value) for value in element_types],
            "gmsh_version": version("gmsh"),
            "minimum_jacobian_positive": minimum_jacobian > 0.0,
            "minimum_det_jac_positive": minimum_det_jac > 0.0,
            "minimum_sicn_positive": minimum_sicn > 0.0,
            "node_count": len(node_tags),
            "physical_groups": physical_names,
        }
    finally:
        gmsh.finalize()


def main() -> int:
    runtime = verify_runtime_contract()
    mesh = build_synthetic_mesh()
    physical_release_gates = {
        "cfd_model_validated": False,
        "engine_geometry_scaled_and_registered": False,
        "engine_interfaces_dimensionally_verified": False,
        "engine_mesh_quality_validated": False,
        "engine_start_authorized": False,
        "fea_model_validated": False,
        "fitment_verified": False,
        "manufacturing_authorized": False,
        "metal_print_authorized": False,
        "physical_correlation_complete": False,
        "target_power_proven": False,
    }
    report = {
        "claim_scope": "synthetic_occ_volume_mesh_only",
        "engine_geometry_verified": False,
        "fabrication_authorized": False,
        "fitment_verified": False,
        "mesh": mesh,
        "physical_release_gates": physical_release_gates,
        "physics_simulation_verified": False,
        "porsche_geometry_used": False,
        "runtime": runtime,
        "status": "passed_synthetic_occ_volume_mesh_only",
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
