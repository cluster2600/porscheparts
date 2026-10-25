"""Run only an explicitly selected local image, with limits and owned-container cleanup."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from ft_common import HERE, checked, load, new_directory, receipt, sha256, write


def run(tool, image, output):
    if tool not in ("cloudcompare", "salome"):
        raise ValueError("unknown native tool")
    output = new_directory(output).resolve()
    identity = json.loads(
        checked(["docker", "image", "inspect", image], output, 15)["stdout"]
    )[0]
    if identity["Architecture"] != "amd64" or identity["Os"] != "linux":
        raise ValueError("linux/amd64 image required")
    image_id = identity["Id"]
    cid = output / "owned-container.cid"
    command = [
        "docker",
        "run",
        "--rm",
        "--cidfile",
        str(cid),
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--memory-swap",
        "4g",
        "--pids-limit",
        "256",
        "--tmpfs",
        "/tmp:rw,nosuid,size=1g",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f"type=bind,src={output},dst=/work",
        image_id,
    ]
    if tool == "salome":
        command += [
            "salome",
            "shell",
            "--",
            "python3",
            "/opt/free-tools/salome_worker.py",
        ]
    command += ["controls", "--output", "/work/result"]
    if tool == "salome":
        command += ["--units", "mm"]
    try:
        execution = checked(command, output, 600)
        (output / "execution.log").write_text(execution["stdout"])
        result = load(output / "result/receipt.json")
        if result["status"] != "passed":
            raise ValueError("native control did not pass")
        report = receipt(
            tool + "-container",
            "passed",
            [],
            checks={
                "image_id": image_id,
                "architecture": "linux/amd64",
                "native_receipt_sha256": sha256(output / "result/receipt.json"),
                "network": "none",
            },
            limitations=[
                "Synthetic CPU controls, not a Kali execution or part qualification."
            ],
        )
        write(output / "receipt.json", report)
        return report
    finally:
        if cid.exists():
            identifier = cid.read_text().strip()
            if re.fullmatch(r"[a-f0-9]{64}", identifier):
                subprocess.run(
                    ["docker", "rm", "-f", identifier], capture_output=True, timeout=15
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=["cloudcompare", "salome"])
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.tool, args.image, args.output)
