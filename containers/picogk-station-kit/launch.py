#!/usr/bin/env python3
"""Run the native Kit editor; GPU ordinals come from gpu.foundation, not CUDA."""

import ipaddress
import json
import os
from pathlib import Path


def command(env):
    gpu = env.get("STATION_KIT_GPU", "2")
    if not gpu.isdecimal() or int(gpu) > 3:
        raise ValueError("STATION_KIT_GPU must be a verified gpu.foundation ordinal in 0..3")
    if env.get("VAST_TCP_PORT_49100"):
        raise ValueError("Do not publish TCP 49100 on Vast; signaling must use SSH")
    public_ip = str(ipaddress.IPv4Address(env.get("PUBLIC_IPADDR") or env.get("VAST_PUBLIC_IP", "")))
    media_port = env.get("VAST_UDP_PORT_47998", "")
    if not media_port.isdecimal() or not 1 <= int(media_port) <= 65535:
        raise ValueError("VAST_UDP_PORT_47998 must contain the mapped external UDP port")
    runtime = Path(env.get("KIT_RUNTIME_DIR", "/opt/station-kit-runtime"))
    args = [
        str(runtime / "kit/kit"), str(runtime / "apps/station.editor_streaming.kit"),
        "--no-window", "--allow-root",
        f"--/renderer/activeGpu={gpu}",
        "--/renderer/multiGpu/enabled=false", "--/renderer/multiGpu/autoEnable=false",
        f"--/exts/omni.kit.livestream.app/primaryStream/publicIp={public_ip}",
        "--/exts/omni.kit.livestream.app/primaryStream/signalPort=49100",
        "--/exts/omni.kit.livestream.app/primaryStream/streamPort=47998",
        "--exec", str(runtime / "open_scene.py"),
    ]
    return args, {"signalingServer": "127.0.0.1", "signalingPort": 49100,
                  "mediaServer": public_ip, "mediaPort": int(media_port),
                  "kitGpuOrdinal": int(gpu)}


def main():
    env = dict(os.environ)
    args, connection = command(env)
    output = Path(env.get("STATION_RUNTIME_DIR", "/workspace/station-runtime"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "webrtc-connection.json").write_text(json.dumps(connection, indent=2) + "\n")
    # CUDA filtering cannot select a Vulkan device and can break interop.
    env.pop("CUDA_VISIBLE_DEVICES", None)
    os.execve(args[0], args, env)


if __name__ == "__main__":
    main()
