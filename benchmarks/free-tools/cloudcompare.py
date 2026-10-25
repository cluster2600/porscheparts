"""Bounded CloudCompare point-to-surface diagnostics with declared millimetres."""

import argparse
import os
from pathlib import Path
import shutil

from ft_common import checked, finite, load, new_directory, receipt, sha256, write
from ft_geometry import read_surface, rigid_points, write_obj


def compare(cloud, mesh, configuration, output, executable="CloudCompare"):
    config = load(configuration)
    if config.get("units") != "mm":
        raise ValueError("explicit mm units required")
    points = []
    for row in Path(cloud).read_text().splitlines():
        point = [finite(float(x)) for x in row.split()]
        if len(point) != 3:
            raise ValueError("XYZ-only cloud required")
        points.append(point)
    if not points:
        raise ValueError("nonempty point cloud required")
    points = rigid_points(points, config["cloud_to_reference"])
    vertices, faces = read_surface(mesh)
    inputs = [
        {"id": name, "sha256": sha256(path)}
        for name, path in (
            ("cloud", cloud),
            ("mesh", mesh),
            ("configuration", configuration),
        )
    ]
    output = new_directory(output).resolve()
    cloud_path, mesh_path = output / "input.xyz", output / "reference.obj"
    cloud_path.write_text(
        "\n".join(" ".join(format(x, ".17g") for x in point) for point in points) + "\n"
    )
    write_obj(mesh_path, vertices, faces)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=str(output))
    command = [
        executable,
        "-SILENT",
        "-AUTO_SAVE",
        "OFF",
        "-C_EXPORT_FMT",
        "ASC",
        "-PREC",
        "12",
        "-O",
        str(cloud_path),
        "-O",
        str(mesh_path),
        "-C2M_DIST",
        "-UNSIGNED",
        "-SAVE_CLOUDS",
        "FILE",
        str(output / "distances.asc"),
    ]
    execution = checked(command, output, 120, env)
    (output / "execution.log").write_text(execution["stdout"])
    distances = []
    for line in (output / "distances.asc").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith(("#", "//")):
            values = [finite(float(x)) for x in line.split()]
            if len(values) != 4:
                raise ValueError("expected XYZ and one distance scalar")
            distances.append(abs(values[-1]))
    if len(distances) != len(points):
        raise ValueError("incomplete CloudCompare output")
    if any(
        sha256(path) != item["sha256"]
        for item, path in zip(inputs, (cloud, mesh, configuration))
    ):
        raise ValueError("inputs changed during comparison")
    # SVG is a diagnostic chart, not an inferred geometric reconstruction.
    maximum = max(distances)
    bars = "".join(
        f'<rect x="{10+i*12}" y="{110-(v/max(maximum,1e-30))*90:.4f}" width="8" height="{(v/max(maximum,1e-30))*90:.4f}" fill="#285a8e"/>'
        for i, v in enumerate(distances[:50])
    )
    (output / "distances.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="145"><title>Sampled absolute distance in mm</title>{bars}<text x="10" y="135">Diagnostic samples; max {maximum:.8g} mm</text></svg>'
    )
    report = receipt(
        "cloudcompare",
        "diagnostic_completed",
        inputs,
        outputs=[
            {"id": name, "sha256": sha256(output / name)}
            for name in ("distances.asc", "distances.svg")
        ],
        checks={
            "sample_count": len(points),
            "maximum_distance_mm": maximum,
            "executable_sha256": sha256(shutil.which(executable) or executable),
            "exit_status": execution["exit_status"],
        },
        limitations=[
            "Sampled distances only; never a whole-surface certificate, measured accuracy or fitment proof."
        ],
    )
    write(output / "receipt.json", report)
    return distances


def controls(output, executable="CloudCompare"):
    output = new_directory(output)
    plane = output / "plane.obj"
    write_obj(
        plane, [[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]], [[0, 1, 2], [0, 2, 3]]
    )
    results = []
    for name, height, translation, expected in (
        ("identity", 0, 0, 0),
        ("offset", 1, 0, 1),
        ("rigid-transform", 3, -3, 0),
    ):
        cloud = output / f"{name}.xyz"
        cloud.write_text(
            "\n".join(
                f"{x} {y} {height}"
                for x, y in [
                    (-1, -1),
                    (0, 0),
                    (1, 1),
                    (-1, 0.5),
                    (0.5, -1),
                    (0.75, 0.2),
                ]
            )
            + "\n"
        )
        configuration = output / f"{name}.json"
        write(
            configuration,
            {
                "units": "mm",
                "cloud_to_reference": [
                    [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, translation],
                    [0, 0, 0, 1],
                ],
            },
        )
        values = compare(cloud, plane, configuration, output / name, executable)
        if any(abs(value - expected) > 0.0001 for value in values):
            raise ValueError("analytic CloudCompare control failed")
        results.append({"case": name, "expected_mm": expected, "values_mm": values})
    write(
        output / "receipt.json",
        receipt(
            "cloudcompare-controls",
            "passed",
            [],
            checks={"absolute_tolerance_mm": 0.0001, "cases": results},
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["controls", "compare"])
    for flag in ("cloud", "mesh", "configuration", "output"):
        parser.add_argument("--" + flag, type=Path, required=flag == "output")
    parser.add_argument("--executable", default="CloudCompare")
    args = parser.parse_args()
    if args.command == "controls":
        controls(args.output, args.executable)
    else:
        if not all([args.cloud, args.mesh, args.configuration]):
            parser.error("compare requires cloud, mesh and configuration")
        compare(args.cloud, args.mesh, args.configuration, args.output, args.executable)


if __name__ == "__main__":
    main()
