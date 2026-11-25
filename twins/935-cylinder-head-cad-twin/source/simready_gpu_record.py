#!/usr/bin/env python3
"""Assemble params/simready-conformance-gpu.json from the receipts of the #707 GPU session.

The session ran on a rented RTX GPU in the admitted SimReady image: SimReady profile validation
with the image's own validator and Foundation release, the same with the newest published ones,
the NVIDIA stage validator in its newest release, and an RTX capture of the frozen review scene
(capture_rtx.py). The receipts were copied back and hashed. This script reads them, sorts every
failing requirement by its cause and writes the record; it adds no number of its own.

Usage: simready_gpu_record.py RECEIPTS_DIR STAGE_WARNINGS.json SESSION.json OUT.json
  RECEIPTS_DIR       private copy of /root/out of the instance
  STAGE_WARNINGS     the output of stage_warnings.py
  SESSION            rental, admission and reading notes written during the session
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "935-cad-twin-simready-gpu/1"

# Why a requirement fails on this asset. A blocker names the issue that has to close first; an
# authoring gap is work nobody has done and needs no outside input, but is not done here either.
CAUSES = [
    (r"\.RB\.(001|MB\.001)$", "#705", "no rigid body: a body without mass would let the engine invent a density, and the alloy is not selected"),
    (r"\.SR\.004$", "#705", "SimReady metadata missing; mass is one of its fields and waits for the alloy, the others (author, licence, category, qcode) are not authored"),
    (r"\.PMT\.001$", "#705", "no physics material on the collider: friction and restitution need a material"),
    (r"\.NVM\.\d+$", "#705", "no non-visual material: the material of the part is not selected"),
    (r"\.UN\.007$", "authoring", "the stage is in millimetres (metersPerUnit 0.001, the twin's convention); the profile wants metres"),
    (r"\.NP\.005$", "authoring", "package layout: root, geometry and collider are three sibling USD files, and the folder names do not follow the asset-root convention"),
    (r"\.NP\.006$", "authoring", "no simready_metadata in the root layer or a sidecar"),
    (r"\.SR\.002$", "authoring", "no 256 x 256 thumbnail in the package"),
    (r"\.AF\.001$", "authoring", "no simready:assetFrame:forwardDirection on the default prim"),
    (r"\.SL\.(001|MAT\.001)$", "authoring", "no semantic labels"),
    (r"\.GSP\.001$", "not applicable", "no grasp vector: a robotics handling point, which no source gives for this part"),
    (r"\.VM\.(MDL\.003|PBR\.001)$", "authoring", "the display material is a UsdPreviewSurface; no MDL or OpenPBR surface is authored"),
    (r"\.RV\.\d+$", "authoring", "no physics runtime variant set"),
    (r"\.(MUJOCO|NEWTON)\.COL\.001$", "authoring", "no engine-specific collider approximation"),
    (r"\.ISA\.001$", "not applicable", "no Isaac composition"),
]


def cause(requirement: str) -> dict:
    for pattern, blocker, why in CAUSES:
        if re.search(pattern, requirement):
            return {"blocked_by": blocker, "why": why}
    return {"blocked_by": "unclassified", "why": "not sorted by this script"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_list(text) -> list[str]:
    return sorted(ast.literal_eval(text)) if text else []


def profile_runs(directory: Path, stack: str) -> list[dict]:
    codes = {}
    for line in (directory / "exit-codes.txt").read_text().splitlines():
        code, tag = line.split(" ", 1)
        codes[tag] = int(code)
    runs = []
    for tag, code in sorted(codes.items()):
        raw = json.loads((directory / f"{tag}.json").read_text() or "{}")
        log = (directory / f"{tag}.txt").read_text()
        asset = re.search(r"^Asset: (\S+)", log, re.M).group(1).replace("/root/in/", "")
        run = {"stack": stack, "asset": asset, "exit_code": code, "receipt_sha256": sha256(directory / f"{tag}.json")}
        if not raw:
            reason = re.search(r"RuntimeError: (.*)", log)
            profile, version = tag[len(asset.replace(".", "_").replace("/", "_")) + 1:].rsplit("-", 1)
            run.update(profile=profile, version=version, result="unavailable",
                       reason=(reason.group(1)[:300] if reason else "the validator produced no result"))
            runs.append(run)
            continue
        entry = next(iter(raw.values()))
        blocking, optional, passed, failed = set(), set(), [], []
        for feature, summary in entry["features_summary"].items():
            (passed if summary.get("passed") else failed).append(feature)
            failing = as_list(summary.get("failing requirements"))
            # The image's release has no blocking flag: a failing requirement of a feature counts.
            if summary.get("blocking_failure", bool(failing)):
                blocking.update(failing)
            optional.update(as_list(summary.get("optional requirements")))
            if not summary.get("blocking_failure", True) and not summary.get("passed"):
                optional.update(failing)
        run.update(profile=entry["profile_id"], version=entry["profile_version"],
                   result="pass" if code == 0 and not blocking else "fail",
                   features_passed=sorted(passed), features_failed=sorted(failed),
                   blocking_requirements=sorted(blocking), optional_requirements_unmet=sorted(optional - blocking))
        runs.append(run)
    return runs


def freeze(path: Path, names: tuple[str, ...]) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        name, _, version = line.partition("==")
        if name.lower() in names:
            out[name.lower()] = version
    return out


def nvidia_latest(directory: Path) -> dict:
    """usd-validation-nvidia in its newest release, alone in its venv, on both forms of the package."""
    out = {"version": (directory / "version.txt").read_text().split()[-1],
           "venv": freeze(directory / "freeze.txt", ("usd-validation-nvidia", "usd-core")), "assets": {}}
    for line in (directory / "exit-codes.txt").read_text().splitlines():
        code, tag = line.split(" ", 1)
        report = json.loads((directory / f"{tag}.json").read_text())
        rules = {}
        for rule in report.get("rules", []):
            severities: dict[str, int] = {}
            for issue in rule.get("issues", []):
                severities[issue["severity"]] = severities.get(issue["severity"], 0) + 1
            rules[rule["rule"]["name"]] = severities
        out["assets"][tag] = {"status": report.get("status"), "exit_code": int(code), "rules_with_issues": rules,
                              "receipt_sha256": sha256(directory / f"{tag}.json")}
    return out


def main(receipts, warnings, session, out) -> None:
    receipts, out = Path(receipts), Path(out)
    warnings = json.loads(Path(warnings).read_text())
    session = json.loads(Path(session).read_text())
    probe = receipts / "probe"
    gpu = probe.joinpath("gpu.csv").read_text().splitlines()[1].split(", ")
    image_tools = freeze(probe / "simready-validation-freeze.txt",
                         ("simready-validate", "usd-validation-nvidia", "usd-profiles-nvidia", "usd-core"))
    latest_tools = freeze(receipts / "latest-venv" / "freeze.txt",
                          ("simready-validate", "simready-foundation-tier-core", "usd-validation-nvidia",
                           "usd-profiles-nvidia", "usd-core"))
    # In the order they ran: the image's release first fed the .usdz itself, then the root layer
    # extracted from it; a second copy sits under folder names that follow the NP.005 convention.
    runs = []
    for directory, stack in (("profiles-image-usdz-attempt", "image"), ("profiles-image", "image"),
                             ("profiles-image-2", "image"), ("profiles-latest", "latest"),
                             ("profiles-latest-2", "latest")):
        runs += profile_runs(receipts / directory, stack)
    requirements = sorted({r for run in runs for r in run.get("blocking_requirements", [])})
    capture = json.loads((receipts / "rtx-scene-a" / "capture" / "capture.json").read_text())
    record = {
        "schema": SCHEMA,
        "issue": 707,
        "date": session["date"],
        "claims": ("a check that the asset is a well-formed stage and RTX pictures of a study twin: no validator pass "
                   "or picture says anything about accuracy, fit or function; the twin stays not measured, not "
                   "functional, not released"),
        "asset": session["asset"],
        "runtime": {
            "image": session["image"],
            "image_admission": session["image_admission"],
            "controller": session["controller"],
            "gpu": {"name": gpu[0], "driver": gpu[1], "memory": gpu[2]},
            "ovrtx_version": probe.joinpath("ovrtx.txt").read_text().split()[1],
            "content_agents_commit": probe.joinpath("content-agents-commit.txt").read_text().split()[0],
            "ffmpeg": probe.joinpath("ffmpeg.txt").read_text().splitlines()[0].split(" Copyright")[0],
            "vulkan_icd": session["vulkan_icd"],
        },
        "rental": session["rental"],
        "inherited_warnings": {
            "rules": ["WeldChecker", "ZeroAreaFaceChecker"],
            "cleared": warnings["trials"]["a_trial_clears_both_warnings"],
            "why_they_stand": session["why_the_warnings_stand"],
            "tol_mm": warnings["tol_mm"],
            "audit": warnings["audit"],
            "trials": warnings["trials"],
            "script": "source/stage_warnings.py",
        },
        "profile_conformance": {
            "stacks": {
                "image": {**image_tools, "foundation_commit": probe.joinpath("foundation-commit.txt").read_text().split()[0],
                          "foundation_release": session["image_foundation_release"]},
                "latest": {**latest_tools, "source": "public PyPI, pinned in the session"},
            },
            "staging": session["staging"],
            "runs": runs,
            "requirement_causes": {r: cause(r) for r in requirements},
            "summary": session["profile_summary"],
        },
        "nvidia_validator_latest": nvidia_latest(receipts / "nvidia-123"),
        "rtx": {
            "renderer": capture["renderer"], "ovrtx_version": capture["ovrtx_version"], "gpu": capture["gpu"],
            "scene_sha256": capture["scene_sha256"], "cad_stage_sha256": capture["cad_stage_sha256"],
            "stills": capture["stills"], "video_frames": capture["video_frames"], "video_fps": capture["video_fps"],
            "accumulation_steps": capture["accumulation_steps"], "adapter_sha256": capture["adapter_sha256"],
            "media_sha256": capture["media_sha256"],
            "capture_receipt_sha256": sha256(receipts / "rtx-scene-a" / "capture" / "capture.json"),
            "wall_seconds": session["rtx_wall_seconds"],
            "read_by_the_agent": True,
            "reading": session["rtx_reading"],
            "published": session["rtx_published"],
        },
        "agents": session["agents"],
        "not_authored": session["not_authored"],
    }
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"runs": [(r["stack"], r["asset"], r["profile"], r["version"], r["result"]) for r in runs]}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
