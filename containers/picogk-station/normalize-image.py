#!/usr/bin/env python3
"""Remove inherited public ports without rewriting a single filesystem layer.

Usage: normalize-image.py SOURCE_IMAGE NEW_TAG
Docker save/load use a temporary legacy manifest.json archive; obsolete OCI
index metadata is omitted so Docker cannot select the unmodified config.
The archive uses disk, bounded RAM, and is deleted automatically.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

PORTS = {"22/tcp": {}, "47998/udp": {}}


def inspect(reference):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", reference]))[0]


def normalize(source, target):
    if source == target:
        raise ValueError("A distinct destination tag is required")
    original = inspect(source)
    source_digest = original["Id"].split(":", 1)[1]
    config_names = {source_digest + ".json", "blobs/sha256/" + source_digest}
    # Never default a multi-GB image archive to a possibly RAM-backed /tmp.
    archive_directory = os.environ.get("TMPDIR") or os.getcwd()
    # Docker's archive can contain twice its advertised image Size.
    if shutil.disk_usage(archive_directory).free < original["Size"] * 3:
        raise ValueError("Archive directory needs at least three times the image Size free")
    saved = subprocess.Popen(["docker", "save", source], stdout=subprocess.PIPE)
    # Finish the export before starting an import on the same image store.
    with tempfile.TemporaryFile(dir=archive_directory) as archive:
        try:
            config = manifest = None
            with tarfile.open(fileobj=saved.stdout, mode="r|", bufsize=1024 * 1024) as reader, tarfile.open(fileobj=archive, mode="w|", bufsize=1024 * 1024) as writer:
                for member in reader:
                    if member.name in {"index.json", "oci-layout", "repositories"}:
                        continue
                    stream = reader.extractfile(member) if member.isfile() else None
                    if member.name in config_names or member.name == "manifest.json":
                        if member.size > 4 * 1024 * 1024:
                            raise ValueError("Unexpectedly large image metadata")
                        payload = json.load(stream)
                        if member.name == "manifest.json":
                            manifest = payload
                        else:
                            config = payload
                        continue
                    writer.addfile(member, stream)
                if config is None or manifest is None or len(manifest) != 1:
                    raise ValueError("Expected exactly one Docker image config and manifest")
                if manifest[0]["Config"] not in config_names:
                    raise ValueError("Docker manifest does not match the inspected source")
                config["config"]["ExposedPorts"] = PORTS
                encoded = json.dumps(config, separators=(",", ":")).encode()
                config_name = "blobs/sha256/" + hashlib.sha256(encoded).hexdigest()
                manifest[0]["Config"] = config_name
                manifest[0]["RepoTags"] = [target]
                for name, data in ((config_name, encoded), ("manifest.json", json.dumps(manifest).encode())):
                    member = tarfile.TarInfo(name)
                    member.size, member.mode = len(data), 0o644
                    writer.addfile(member, io.BytesIO(data))
            saved.stdout.close()
            if saved.wait() != 0:
                raise RuntimeError("docker save failed")
        finally:
            if saved.poll() is None:
                saved.kill()
                saved.wait()
        archive.seek(0)
        subprocess.run(["docker", "load"], stdin=archive, stdout=subprocess.PIPE, check=True)
    result = inspect(target)
    expected_config = dict(original["Config"], ExposedPorts=PORTS)
    if result["RootFS"] != original["RootFS"] or result["Config"] != expected_config:
        raise RuntimeError("Normalized image changed layers or unrelated configuration")
    print(json.dumps({"status": "PASS", "source": original["Id"], "image": result["Id"],
                      "ports": PORTS, "layers_unchanged": True, "tag": target}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    normalize(*sys.argv[1:])
