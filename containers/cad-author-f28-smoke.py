#!/usr/bin/env python3
"""Smoke CAD/STEP synthetique de l'image auteur F28, sans geometrie Porsche."""

from __future__ import annotations

import hashlib
import gzip
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import pwd
import re
import sys
import tarfile
import tempfile
from typing import Any


APPLICATION_ROOT = Path("/opt/cad-author-f28")
REQUIREMENTS = APPLICATION_ROOT / "cad-author-f28-requirements.txt"
SYSTEM_PACKAGES = APPLICATION_ROOT / "cad-author-f28-system-packages.sha256"
RUNTIME_UID = 9178
RUNTIME_GID = 9178
RUNTIME_HOME = Path("/tmp")
RUNTIME_CACHE = Path("/tmp/cad-author-f28-cache")
UNCOMPRESSED_LAYERS_BUDGET_BYTES = 1100000000
CANONICAL_EMPTY_GZIP_LAYER_SHA256 = (
    "4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1"
)
RELEASE_GATES = {
    "canonical_scan_used": False,
    "scan_identity_confirmed": False,
    "physical_scale_confirmed": False,
    "engine_geometry_authored": False,
    "engine_assembly_released": False,
    "cae_geometry_released": False,
    "classical_solver_released": False,
    "physicsnemo_dataset_released": False,
    "physicsnemo_training_released": False,
    "omniverse_simready_released": False,
    "manufacturing_released": False,
    "fabrication_released": False,
    "engine_start_released": False,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def dependency_audit() -> dict[str, Any]:
    source = REQUIREMENTS.read_text(encoding="ascii")
    pins = {
        canonical_name(name): version
        for name, version in re.findall(
            r"^([A-Za-z0-9_.-]+)==([^ \\\n]+)", source, re.MULTILINE
        )
    }
    hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", source)
    require(len(pins) == 46, "the F28 wheel lock must contain exactly 46 pins")
    require(len(hashes) == 46 and len(set(hashes)) == 46, "invalid F28 wheel hashes")

    installed = {
        canonical_name(distribution.metadata["Name"]): distribution.version
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    mismatches = {
        name: {"expected": version, "actual": installed.get(name)}
        for name, version in pins.items()
        if installed.get(name) != version
    }
    require(not mismatches, f"wheel lock mismatch: {mismatches}")
    unexpected = sorted(set(installed) - set(pins) - {"pip"})
    require(not unexpected, f"unexpected Python distributions: {unexpected}")
    require(installed.get("pip") == "25.0.1", "unexpected pip in pinned Python base")
    require(pins["build123d"] == "0.11.1", "unexpected build123d pin")
    require(pins["cadquery-ocp-novtk"] == "7.9.3.1.1", "unexpected OCP pin")
    system_source = SYSTEM_PACKAGES.read_text(encoding="ascii")
    system_entries = re.findall(
        r"^([0-9a-f]{64})  ([A-Za-z0-9%+_.:-]+\.deb)$",
        system_source,
        re.MULTILINE,
    )
    require(
        len(system_entries) == 11 and len({digest for digest, _ in system_entries}) == 11,
        "invalid F28 Debian package lock",
    )
    return {
        "policy": "46_exact_hashed_linux_amd64_wheels_plus_11_exact_hashed_debian_packages_plus_pinned_base_pip",
        "requirements_sha256": sha256(REQUIREMENTS),
        "pin_count": len(pins),
        "hash_count": len(hashes),
        "system_package_hash_count": len(system_entries),
        "system_packages_sha256": sha256(SYSTEM_PACKAGES),
        "unexpected_distributions": unexpected,
        "versions": {
            "python": platform.python_version(),
            "pip": installed["pip"],
            "build123d": pins["build123d"],
            "cadquery-ocp-novtk": pins["cadquery-ocp-novtk"],
            "cadquery-ocp-proxy": pins["cadquery-ocp-proxy"],
            "numpy": pins["numpy"],
        },
    }


def runtime_identity_and_cache_audit() -> dict[str, Any]:
    account = pwd.getpwuid(RUNTIME_UID)
    require(account.pw_name == "cad-author", "unexpected runtime account name")
    require(account.pw_gid == RUNTIME_GID, "unexpected runtime primary group")
    require(account.pw_dir == str(RUNTIME_HOME), "runtime passwd home must be /tmp")
    require(os.environ.get("HOME") == str(RUNTIME_HOME), "HOME must be /tmp")
    require(
        os.environ.get("XDG_CACHE_HOME") == str(RUNTIME_CACHE),
        "XDG_CACHE_HOME must be the dedicated /tmp cache",
    )
    RUNTIME_CACHE.mkdir(mode=0o700, parents=False, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="write-probe-", dir=RUNTIME_CACHE, delete=True
    ) as probe:
        probe.write(b"cad-author-f28")
        probe.flush()
    return {
        "account": account.pw_name,
        "uid": os.getuid(),
        "gid": os.getgid(),
        "passwd_home": account.pw_dir,
        "home_environment": os.environ["HOME"],
        "xdg_cache_home": os.environ["XDG_CACHE_HOME"],
        "cache_write_probe": True,
    }


def license_audit() -> dict[str, Any]:
    system_source = SYSTEM_PACKAGES.read_text(encoding="ascii")
    package_files = re.findall(
        r"^[0-9a-f]{64}  ([A-Za-z0-9%+_.:-]+\.deb)$",
        system_source,
        re.MULTILINE,
    )
    package_names = sorted(filename.split("_", 1)[0] for filename in package_files)
    notice_paths = {
        package: Path("/usr/share/doc") / package / "copyright"
        for package in package_names
    }
    missing = sorted(
        package
        for package, path in notice_paths.items()
        if not path.is_file() or path.stat().st_size == 0
    )
    require(not missing, f"missing Debian copyright notices: {missing}")
    common_licenses = Path("/usr/share/common-licenses")
    require(common_licenses.is_dir(), "Debian common licences are unavailable")
    common_files = sorted(path.name for path in common_licenses.iterdir() if path.is_file())
    require(common_files, "Debian common licences are empty")
    return {
        "policy": "NOASSERTION_label_with_package_notices_and_sbom_as_authority",
        "package_notice_count": len(notice_paths),
        "package_notice_sha256": {
            package: sha256(path) for package, path in sorted(notice_paths.items())
        },
        "missing_package_notices": missing,
        "common_licenses_present": True,
        "common_license_file_count": len(common_files),
    }


def fontconfig_audit() -> dict[str, Any]:
    fonts_conf = Path("/etc/fonts/fonts.conf")
    require(fonts_conf.is_file() and fonts_conf.stat().st_size > 0, "fontconfig config missing")
    fragments_root = Path("/etc/fonts/conf.d")
    fragments = sorted(
        path.name for path in fragments_root.iterdir() if path.is_file()
    ) if fragments_root.is_dir() else []
    require(fragments, "fontconfig fragments missing")
    font_root = Path("/usr/share/fonts")
    font_suffixes = {".ttf", ".otf", ".ttc", ".woff", ".woff2", ".pfa", ".pfb"}
    system_font_files = sorted(
        str(path.relative_to(font_root))
        for path in font_root.rglob("*")
        if path.is_file() and path.suffix.lower() in font_suffixes
    ) if font_root.is_dir() else []
    require(not system_font_files, f"unexpected system fonts: {system_font_files}")
    return {
        "config_present": True,
        "fonts_conf_sha256": sha256(fonts_conf),
        "config_fragment_count": len(fragments),
        "system_font_file_count": len(system_font_files),
    }


def font_payload_audit() -> dict[str, Any]:
    site_packages = Path("/usr/local/lib/python3.12/site-packages")
    font_suffixes = {".ttf", ".otf", ".ttc", ".woff", ".woff2", ".pfa", ".pfb"}
    font_files = {
        str(path.relative_to(site_packages)): sha256(path)
        for path in site_packages.rglob("*")
        if path.is_file() and path.suffix.lower() in font_suffixes
    }
    expected = {
        "build123d/data/fonts/reliefsingleline/ReliefSingleLineCAD-Regular.ttf":
            "8b30ea7ea8a2b17fb9d5c70b5c7c37e6a9285b4f8aced4fbd646bc591dba59b3"
    }
    require(font_files == expected, f"unexpected dependency font payload: {font_files}")
    return {
        "dependency_font_file_count": len(font_files),
        "dependency_font_files_sha256": font_files,
        "source": "hash_locked_build123d_wheel_data",
        "system_fonts_included": False,
        "text_geometry_validated": False,
    }


def bundled_content_audit() -> dict[str, Any]:
    expected = {
        "cad-author-f28-requirements.txt",
        "cad-author-f28-smoke.py",
        "cad-author-f28-system-packages.sha256",
    }
    files = sorted(
        str(path.relative_to(APPLICATION_ROOT))
        for path in APPLICATION_ROOT.rglob("*")
        if path.is_file()
    )
    require(set(files) == expected, f"unexpected F28 application bundle: {files}")
    forbidden_suffixes = {
        ".obj", ".ply", ".stl", ".3mf", ".step", ".stp", ".brep",
        ".fcstd", ".scad", ".usd", ".usda", ".usdc", ".usdz", ".npz",
        ".h5", ".hdf5", ".bin", ".ckpt", ".onnx", ".pt", ".pth",
        ".safetensors",
    }
    forbidden_assets = sorted(
        path for path in files if Path(path).suffix.lower() in forbidden_suffixes
    )
    secret_named = sorted(
        path
        for path in files
        if Path(path).name.lower() == ".env"
        or Path(path).suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
        or any(
            marker in Path(path).name.lower()
            for marker in ("credential", "secret", "token")
        )
    )
    require(not forbidden_assets and not secret_named, "forbidden content in F28 bundle")
    return {
        "scope": str(APPLICATION_ROOT),
        "expected_files": sorted(expected),
        "unexpected_files": [],
        "forbidden_asset_files": forbidden_assets,
        "secret_named_files": secret_named,
        "contains_scan_or_engine_geometry": False,
        "contains_model_weights": False,
    }


def network_isolation_evidence() -> dict[str, Any]:
    network_root = Path("/sys/class/net")
    route_file = Path("/proc/net/route")
    ipv6_route_file = Path("/proc/net/ipv6_route")
    require(network_root.is_dir() and route_file.is_file(), "network evidence unavailable")
    interfaces = sorted(path.name for path in network_root.iterdir())
    ipv4_rows = [line.split() for line in route_file.read_text().splitlines()[1:] if line.strip()]
    ipv6_rows = (
        [line.split() for line in ipv6_route_file.read_text().splitlines() if line.strip()]
        if ipv6_route_file.is_file()
        else []
    )
    routed_interfaces = sorted(
        {row[0] for row in ipv4_rows if row}
        | {row[-1] for row in ipv6_rows if row}
    )
    external = [name for name in routed_interfaces if name != "lo"]
    default_ipv4 = any(
        len(row) > 7
        and row[0] != "lo"
        and row[1] == "00000000"
        and row[7] == "00000000"
        for row in ipv4_rows
    )
    default_ipv6 = any(
        len(row) > 1
        and row[-1] != "lo"
        and row[0] == "0" * 32
        and row[1] == "00"
        for row in ipv6_rows
    )
    require(not external and not default_ipv4 and not default_ipv6, "smoke requires --network=none")
    return {
        "verified": True,
        "scope": "container_network_namespace",
        "kernel_interfaces": interfaces,
        "routed_interfaces": routed_interfaces,
        "external_routed_interfaces": external,
        "default_ipv4_external_route": default_ipv4,
        "default_ipv6_external_route": default_ipv6,
        "network_calls_attempted": False,
    }


def vector(values: Any) -> list[float]:
    return [round(float(values.X), 9), round(float(values.Y), 9), round(float(values.Z), 9)]


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounding_box = shape.bounding_box()
    solid_closed = [
        bool(
            solid.is_valid
            and solid.is_manifold
            and len(solid.shells()) == 1
            and solid.shells()[0].is_manifold
            and solid.volume > 0.0
        )
        for solid in solids
    ]
    return {
        "valid": bool(shape.is_valid),
        "manifold": bool(shape.is_manifold),
        "solid_count": len(solids),
        "all_solids_closed": bool(solids) and all(solid_closed),
        "shell_counts": [len(solid.shells()) for solid in solids],
        "face_count": len(shape.faces()),
        "edge_count": len(shape.edges()),
        "volume_mm3": round(sum(solid.volume for solid in solids), 9),
        "bounds_min_mm": vector(bounding_box.min),
        "bounds_max_mm": vector(bounding_box.max),
        "bounds_size_mm": vector(bounding_box.size),
    }


def build_fixture() -> Any:
    from build123d import Align, Box, Cylinder, Pos

    width, depth, height = 20.0, 12.0, 8.0
    bore_radius = 2.0
    body = Box(
        width,
        depth,
        height,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    cutter = Pos(width / 2.0, depth / 2.0, -2.0) * Cylinder(
        bore_radius,
        height + 4.0,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return body - cutter


def exercise_step_roundtrip(directory: Path, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from build123d import export_step, import_step

    source = build_fixture()
    step_path = directory / f"{name}.step"
    export_step(source, step_path)
    require(step_path.is_file() and step_path.stat().st_size > 1000, "STEP export missing")
    imported = import_step(step_path)
    return shape_metrics(source), {
        **shape_metrics(imported),
        "step_bytes": step_path.stat().st_size,
        "step_sha256": sha256(step_path),
        "step_header_identifies_occt_7_9": "Open CASCADE STEP processor 7.9"
        in step_path.read_text(encoding="latin-1", errors="strict")[:4096],
    }


def cad_smoke_main() -> None:
    import OCP
    import build123d

    require(os.getuid() == RUNTIME_UID and os.getgid() == RUNTIME_GID, "non-root UID/GID required")
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "linux/amd64 required")
    require(build123d.__version__ == "0.11.1", "unexpected build123d runtime")
    require(OCP.__version__ == "7.9.3.1", "unexpected OCP runtime")

    expected_volume = 20.0 * 12.0 * 8.0 - math.pi * 2.0**2 * 8.0
    expected_bounds = [20.0, 12.0, 8.0]
    with tempfile.TemporaryDirectory(prefix="cad-author-f28-") as temporary:
        directory = Path(temporary)
        created_1, reopened_1 = exercise_step_roundtrip(directory, "fixture-a")
        created_2, reopened_2 = exercise_step_roundtrip(directory, "fixture-b")

    for metrics in (created_1, created_2, reopened_1, reopened_2):
        require(metrics["valid"], "invalid synthetic solid")
        require(metrics["manifold"], "non-manifold synthetic solid")
        require(metrics["solid_count"] == 1, "synthetic fixture must contain one solid")
        require(metrics["all_solids_closed"], "synthetic fixture must be a closed solid")
        require(metrics["shell_counts"] == [1], "synthetic fixture must contain one closed shell")
        require(
            math.isclose(metrics["volume_mm3"], expected_volume, rel_tol=0.0, abs_tol=1e-6),
            "synthetic volume mismatch",
        )
        require(metrics["bounds_size_mm"] == expected_bounds, "synthetic bounds mismatch")
    require(reopened_1["step_header_identifies_occt_7_9"], "STEP header does not identify OCCT 7.9")
    require(reopened_2["step_header_identifies_occt_7_9"], "STEP header does not identify OCCT 7.9")

    created_signature_equal = created_1 == created_2
    reopened_geometry_1 = {key: value for key, value in reopened_1.items() if not key.startswith("step_")}
    reopened_geometry_2 = {key: value for key, value in reopened_2.items() if not key.startswith("step_")}
    reopened_signature_equal = reopened_geometry_1 == reopened_geometry_2
    require(created_signature_equal and reopened_signature_equal, "geometry signature is not repeatable")

    report = {
        "status": "passed_synthetic_cad_fixture_only",
        "offline": True,
        "non_root": True,
        "gpu": False,
        "platform": "linux/amd64-cpu",
        "runtime_uid_gid": f"{os.getuid()}:{os.getgid()}",
        "build123d": build123d.__version__,
        "ocp": OCP.__version__,
        "runtime_identity_and_cache_audit": runtime_identity_and_cache_audit(),
        "fontconfig_audit": fontconfig_audit(),
        "font_payload_audit": font_payload_audit(),
        "license_audit": license_audit(),
        "network_isolation_evidence": network_isolation_evidence(),
        "bundled_content_audit": bundled_content_audit(),
        "dependency_audit": dependency_audit(),
        "fixture": {
            "kind": "synthetic_box_with_through_bore",
            "source": "dimensions_declared_in_smoke_not_derived_from_vehicle_geometry",
            "dimensions_mm": {
                "width": 20.0,
                "depth": 12.0,
                "height": 8.0,
                "bore_radius": 2.0,
            },
        },
        "checks": {
            "created_shape": created_1,
            "step_reopened_shape": reopened_geometry_1,
            "step_export_bytes": reopened_1["step_bytes"],
            "step_export_sha256_recorded_not_a_reproducibility_claim": reopened_1["step_sha256"],
            "step_header_identifies_occt_7_9": reopened_1["step_header_identifies_occt_7_9"],
            "expected_volume_mm3": round(expected_volume, 9),
            "expected_bounds_size_mm": expected_bounds,
            "created_geometry_signature_repeatable": created_signature_equal,
            "reopened_geometry_signature_repeatable": reopened_signature_equal,
            "closed_solid_after_step_roundtrip": reopened_geometry_1["all_solids_closed"],
            "canonical_scan_used": False,
            "vehicle_geometry_used": False,
        },
        "release_gates": RELEASE_GATES,
    }
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False))


class CountingReader:
    """Compter un flux de couche sans le charger en memoire."""

    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self.count = 0

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.count += len(data)
        return data


def validate_tar_stream_and_count(stream: Any) -> int:
    counter = CountingReader(stream)
    with tarfile.open(fileobj=counter, mode="r|") as layer_tar:
        for _member in layer_tar:
            pass
    while counter.read(1024 * 1024):
        pass
    return counter.count


def archive_member_sha256(archive: tarfile.TarFile, member: tarfile.TarInfo) -> str:
    member_stream = archive.extractfile(member)
    require(member_stream is not None, f"archive member is unreadable: {member.name}")
    digest = hashlib.sha256()
    for chunk in iter(lambda: member_stream.read(1024 * 1024), b""):
        digest.update(chunk)
    member_stream.close()
    return digest.hexdigest()


def measure_image_archive(archive_path: Path, local_store_bytes: int) -> dict[str, Any]:
    require(local_store_bytes > 0, "local image store size must be positive")
    require(archive_path.is_file() and archive_path.stat().st_size > 0, "image archive missing")
    with tarfile.open(archive_path, mode="r:") as archive:
        manifest_member = archive.getmember("manifest.json")
        require(manifest_member.isfile(), "image manifest must be a regular file")
        manifest_stream = archive.extractfile(manifest_member)
        require(manifest_stream is not None, "image manifest is unreadable")
        manifest = json.load(manifest_stream)
        require(isinstance(manifest, list) and len(manifest) == 1, "one image manifest required")
        layer_paths = manifest[0].get("Layers")
        require(isinstance(layer_paths, list) and layer_paths, "image layers missing")

        uncompressed_layer_tar_bytes = 0
        for layer_path in layer_paths:
            require(isinstance(layer_path, str), "layer path must be a string")
            supported_path = bool(
                re.fullmatch(r"blobs/sha256/[0-9a-f]{64}", layer_path)
                or re.fullmatch(r"[0-9a-f]{64}/layer[.]tar", layer_path)
            )
            require(supported_path, f"unsafe or unsupported layer path: {layer_path}")
            layer_member = archive.getmember(layer_path)
            require(layer_member.isfile(), f"layer must be a regular file: {layer_path}")
            if layer_path.startswith("blobs/sha256/"):
                expected_blob_sha256 = layer_path.rsplit("/", 1)[1]
                require(
                    archive_member_sha256(archive, layer_member) == expected_blob_sha256,
                    f"OCI layer digest mismatch: {layer_path}",
                )
            layer_stream = archive.extractfile(layer_member)
            require(layer_stream is not None, f"layer is unreadable: {layer_path}")
            prefix = layer_stream.read(512)
            layer_stream.close()

            layer_stream = archive.extractfile(layer_member)
            require(layer_stream is not None, f"layer is unreadable: {layer_path}")
            if prefix[:2] == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=layer_stream, mode="rb") as decoded:
                    first_byte = decoded.read(1)
                layer_stream.close()
                if not first_byte:
                    require(
                        layer_path
                        == f"blobs/sha256/{CANONICAL_EMPTY_GZIP_LAYER_SHA256}",
                        f"only the canonical empty gzip layer is accepted: {layer_path}",
                    )
                    layer_bytes = 0
                else:
                    layer_stream = archive.extractfile(layer_member)
                    require(layer_stream is not None, f"layer is unreadable: {layer_path}")
                    with gzip.GzipFile(fileobj=layer_stream, mode="rb") as decoded:
                        layer_bytes = validate_tar_stream_and_count(decoded)
                    layer_stream.close()
            else:
                raw_tar_header = (
                    len(prefix) == 512
                    and (prefix[257:262] == b"ustar" or prefix == b"\0" * 512)
                )
                require(raw_tar_header, f"unsupported non-gzip layer encoding: {layer_path}")
                layer_bytes = validate_tar_stream_and_count(layer_stream)
                layer_stream.close()
                require(
                    layer_bytes == layer_member.size,
                    f"uncompressed layer size mismatch: {layer_path}",
                )
            uncompressed_layer_tar_bytes += layer_bytes

    require(
        uncompressed_layer_tar_bytes < UNCOMPRESSED_LAYERS_BUDGET_BYTES,
        "uncompressed layer budget exceeded",
    )
    return {
        "metric_scope": "docker_local_store_plus_sum_of_uncompressed_layer_tar_streams",
        "local_store_reported_bytes": local_store_bytes,
        "local_store_metric_note": "diagnostic_only_engine_backend_dependent_not_gated",
        "uncompressed_layer_tar_bytes": uncompressed_layer_tar_bytes,
        "budgets": {
            "uncompressed_layer_tar_bytes": UNCOMPRESSED_LAYERS_BUDGET_BYTES,
        },
    }


def cli() -> None:
    arguments = sys.argv[1:]
    if not arguments:
        cad_smoke_main()
        return
    if (
        len(arguments) == 4
        and arguments[0] == "--measure-image-archive"
        and arguments[2] == "--local-store-bytes"
        and arguments[3].isdigit()
    ):
        report = measure_image_archive(Path(arguments[1]), int(arguments[3]))
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return
    raise SystemExit(
        "usage: cad-author-f28-smoke.py "
        "[--measure-image-archive PATH --local-store-bytes BYTES]"
    )


if __name__ == "__main__":
    cli()
