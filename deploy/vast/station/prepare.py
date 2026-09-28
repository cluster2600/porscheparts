#!/usr/bin/env python3
"""Prepare a surgical wrapper candidate, bounded manifest and persistent guard.

Never installs the wrapper and never rents. The render command binds a qualified
image and one private session directory; review the candidate before installation.
"""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import plistlib
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "deploy/openbao/station_profile.py"
GUARD = Path(__file__).with_name("deadline_guard.py")


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


policy = load(MODULE, "station_profile")


def private_directory(path):
    if not path.is_absolute() or path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077:
        raise ValueError("existing absolute 0700 session directory required")
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError("session directory must not traverse symlinks")


def render(source, pins, module_path=MODULE):
    if "STATION_PINS =" in source:
        raise ValueError("wrapper already has a station extension; review it before replacing")
    anchor = "def run(operation: list[str]) -> int:\n"
    if source.count(anchor) != 1:
        raise ValueError("wrapper run entry point changed")
    helper = ("STATION_PINS = " + repr(pins) + "\n\n"
              "def _station_prepare(operation):\n"
              f"    if not operation or operation[0] not in {policy.OPERATIONS!r}:\n"
              "        return None, None\n"
              f"    code = m64_read_file(Path({str(module_path)!r}), 65536)\n"
              f"    if hashlib.sha256(code).hexdigest() != {hashlib.sha256(module_path.read_bytes()).hexdigest()!r}:\n"
              "        raise SafeError('station profile fingerprint changed')\n"
              "    namespace = {}\n"
              f"    exec(compile(code, {str(module_path)!r}, 'exec'), namespace)\n"
              "    return namespace, namespace['prepare'](globals(), operation, STATION_PINS)\n\n\n")
    before, after = source.split(anchor)
    after = "    station_module, station_bundle = _station_prepare(operation)\n" + after
    auth = "        api_key = read_vast_key(token)\n"
    if after.count(auth) != 1:
        raise ValueError("wrapper authentication boundary changed")
    after = after.replace(auth, auth + "        if station_module is not None:\n"
                          "            return station_module['run'](globals(), api_key, operation, station_bundle)\n", 1)
    result = before + helper + anchor + after
    compile(result, "station-wrapper-candidate", "exec")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrapper", type=Path, default=Path.home() / ".local/bin/openbao-vastai")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("render")
    command.add_argument("--qualification", type=Path, required=True)
    command.add_argument("--session-directory", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("manifest")
    command.add_argument("--offer-id", type=int, required=True)
    command.add_argument("--hours", type=float, default=6)
    command = commands.add_parser("arm")
    command.add_argument("manifest", type=Path)
    args = parser.parse_args()
    wrapper = load(args.wrapper, "approved_vast_wrapper")
    if args.command == "render":
        private_directory(args.session_directory)
        proof, digest = policy.read_json(vars(wrapper), args.qualification)
        if not policy.qualification_valid(proof):
            raise ValueError("image, model, bytes and published ports need qualification before rendering")
        pins = {"qualification_path": str(args.qualification), "qualification_sha256": digest,
                "session_directory": str(args.session_directory), "guard_path": str(GUARD),
                "guard_sha256": hashlib.sha256(GUARD.read_bytes()).hexdigest()}
        source = wrapper.m64_read_file(args.wrapper, 1024**2).decode()
        output = render(source, pins)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o700)
        with os.fdopen(fd, "w") as stream:
            stream.write(output)
        print(json.dumps({"candidate": str(args.output), "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                          "candidate_sha256": hashlib.sha256(output.encode()).hexdigest(), "installed": False}))
        return
    pins = wrapper.STATION_PINS
    directory = Path(pins["session_directory"])
    private_directory(directory)
    if args.command == "manifest":
        if not 0.5 <= args.hours <= 6:
            raise ValueError("hours must be between 0.5 and 6")
        result = subprocess.run([str(args.wrapper), "station-offers", str(args.offer_id)],
                                check=True, capture_output=True, timeout=120)
        offers = json.loads(result.stdout)
        if len(offers) != 1:
            raise ValueError("exact station offer unavailable")
        offer = offers[0]
        now = int(time.time())
        state = directory / "session.json"
        if not state.exists():
            policy.write_json(state, {"profile": policy.PROFILE, "created_epoch": now,
                                     "deadline_epoch": now + 21600, "budget_usd": 50.0})
        bounds = policy.session(vars(wrapper), directory)
        remaining = 50 - policy.reserved_cost(vars(wrapper), directory)
        transfers = offer["inet_down_cost_usd_per_gb"] * 500 + offer["inet_up_cost_usd_per_gb"] * 100 + 2
        seconds = min(int(args.hours * 3600), bounds["deadline_epoch"] - now,
                      int((remaining - transfers) / offer["dph_total"] * 3600))
        if seconds < 1800:
            raise ValueError("remaining session budget or time cannot cover startup and cleanup")
        attempt_budget = min(remaining, math.ceil((offer["dph_total"] * seconds / 3600 + transfers) * 100) / 100)
        suffix = secrets.token_hex(10)
        job = "station-" + suffix
        proof, _ = policy.read_json(vars(wrapper), pins["qualification_path"])
        manifest = {"schema_version": "1.0.0", "profile": policy.PROFILE, "role": "llm", "variant": policy.PROFILE,
                    "job_id": job, "attempt_label": "3dprinting993-picogk-station-" + suffix, "sibling_label": "",
                    "image_ref": proof["image_ref"], "model": policy.MODEL, "model_revision": policy.REVISION,
                    "created_epoch": now, "deadline_epoch": now + seconds, "budget_usd": attempt_budget,
                    "download_budget_gb": 500, "upload_budget_gb": 100,
                    **{key: pins[key] for key in ("qualification_path", "qualification_sha256", "guard_path", "guard_sha256")},
                    "guard_ready_path": str(directory / (job + ".guard-ready.json")),
                    "guard_service_name": "com.3dprinting993." + job}
        path = directory / (job + ".json")
        policy.write_json(path, manifest)
        policy.prepare(vars(wrapper), ["launch-station", str(args.offer_id), str(path)], pins)
        print(json.dumps({"manifest": str(path), "deadline_epoch": manifest["deadline_epoch"], "budget_usd": attempt_budget}))
        return
    manifest, _ = policy.read_json(vars(wrapper), args.manifest)
    policy.prepare(vars(wrapper), ["reconcile-station", str(args.manifest)], pins)
    label = manifest["guard_service_name"]
    plist = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    plist.parent.mkdir(parents=True, exist_ok=True)
    service = {"Label": label, "ProgramArguments": [sys.executable, str(GUARD), str(args.manifest)],
               "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 10,
               "StandardOutPath": str(directory / (manifest["job_id"] + ".guard.log")),
               "StandardErrorPath": str(directory / (manifest["job_id"] + ".guard-errors.log"))}
    fd = os.open(plist, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        plistlib.dump(service, stream)
    subprocess.run(["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)], check=True)
    print(json.dumps({"guard_launchagent": str(plist), "ready_path": manifest["guard_ready_path"],
                      "rented": False, "require_mac_awake": True}))


if __name__ == "__main__":
    main()
