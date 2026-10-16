"""Fetch one immutable public OCI image into a private, unprivileged rootfs."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import time
import urllib.request
import sys

REPOSITORY = "idaholab/moose"
DIGEST = "sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452"
BASE = Path(sys.argv[1]).resolve()
ROOTFS = BASE / "rootfs"
MAX_EXPANDED = 16 * 1024**3
MAX_COMPRESSED = 3 * 1024**3


def relative_path(value):
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("unsafe archive path")
    return p


def checked_path(value):
    p = ROOTFS / str(relative_path(value))
    if not p.parent.resolve().is_relative_to(ROOTFS.resolve()):
        raise ValueError("whiteout parent escapes rootfs")
    return p


def remove_path(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def main():
    for good in ("a/b", "./a", "usr/lib/x"):
        relative_path(good)
    for bad in ("../etc/passwd", "/etc/passwd", "a/../../b", ""):
        try:
            relative_path(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("path check accepted unsafe input")
    BASE.mkdir(exist_ok=True)
    ROOTFS.mkdir(exist_ok=True)
    assert ROOTFS.is_dir() and not ROOTFS.is_symlink()
    if (BASE / "receipt.json").exists():
        raise RuntimeError("immutable completed runtime already exists")
    token_url = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:" + REPOSITORY + ":pull"
    def refresh_token():
        with urllib.request.urlopen(token_url, timeout=60) as response:
            return json.load(response)["token"]

    token = refresh_token()

    def request(path):
        return urllib.request.Request("https://registry-1.docker.io/v2/" + REPOSITORY + path,
            headers={"Authorization": "Bearer " + token,
                     "Accept": "application/vnd.docker.distribution.manifest.v2+json"})

    with urllib.request.urlopen(request("/manifests/" + DIGEST), timeout=60) as response:
        manifest_raw = response.read(2 * 1024**2)
    assert "sha256:" + hashlib.sha256(manifest_raw).hexdigest() == DIGEST
    manifest = json.loads(manifest_raw)
    assert manifest["schemaVersion"] == 2
    assert sum(layer["size"] for layer in manifest["layers"]) <= MAX_COMPRESSED
    (BASE / "manifest.json").write_bytes(manifest_raw)
    config_digest = manifest["config"]["digest"]
    with urllib.request.urlopen(request("/blobs/" + config_digest), timeout=60) as response:
        config_raw = response.read(2 * 1024**2)
    assert "sha256:" + hashlib.sha256(config_raw).hexdigest() == config_digest
    (BASE / "config.json").write_bytes(config_raw)
    config = json.loads(config_raw)
    assert config["architecture"] == "amd64" and config["os"] == "linux"
    receipt = {"image": REPOSITORY + "@" + DIGEST, "config_digest": config_digest,
               "rootfs": str(ROOTFS), "architecture": config["architecture"], "layers": [],
               "expanded_bytes": 0, "started_unix": time.time(), "paid_compute": False}
    if (BASE / "progress.json").exists():
        receipt = json.loads((BASE / "progress.json").read_text())
        assert receipt["image"] == REPOSITORY + "@" + DIGEST
        assert receipt["rootfs"] == str(ROOTFS)
        assert [x["digest"] for x in receipt["layers"]] == [x["digest"] for x in manifest["layers"][:len(receipt["layers"])]]
    for i, layer in enumerate(manifest["layers"]):
        if i < len(receipt["layers"]):
            continue
        digest = layer["digest"]
        assert digest.startswith("sha256:") and len(digest) == 71
        archive = BASE / (digest.split(":")[1] + ".tar.gz")
        print("layer", i + 1, "/", len(manifest["layers"]), "bytes", layer["size"], flush=True)
        checksum = hashlib.sha256()
        size = 0
        token = refresh_token()
        if archive.exists():
            archive.rename(archive.with_suffix(".incomplete-" + str(time.time_ns())))
        with urllib.request.urlopen(request("/blobs/" + digest), timeout=120) as response, archive.open("xb") as output:
            while block := response.read(4 * 1024**2):
                size += len(block)
                assert size <= layer["size"]
                checksum.update(block)
                output.write(block)
        assert size == layer["size"] and "sha256:" + checksum.hexdigest() == digest
        exclusions = []
        members_count = 0
        with tarfile.open(archive, "r:gz") as source:
            for member in source:
                path = relative_path(member.name)
                members_count += 1
                assert not (member.ischr() or member.isblk() or member.isfifo())
                if member.islnk():
                    relative_path(member.linkname)
                receipt["expanded_bytes"] += member.size
                assert receipt["expanded_bytes"] <= MAX_EXPANDED
                if path.name == ".wh..wh..opq":
                    parent = checked_path(str(path.parent / "placeholder")).parent
                    if parent.exists():
                        for entry in parent.iterdir():
                            remove_path(entry)
                    exclusions.append(member.name)
                elif path.name.startswith(".wh."):
                    remove_path(checked_path(str(path.with_name(path.name[4:]))))
                    exclusions.append(member.name)
        command = ["bwrap", "--ro-bind", "/", "/", "--bind", str(BASE), str(BASE),
                   "--dev", "/dev", "--proc", "/proc", "--unshare-net", "tar",
                   "--extract", "--gzip", "--file", str(archive), "--directory", str(ROOTFS),
                   "--no-same-owner", "--no-same-permissions"]
        for excluded in exclusions:
            command += ["--exclude", excluded]
        subprocess.run(command, check=True)
        receipt["layers"].append({"digest": digest, "compressed_bytes": size,
                                  "members": members_count, "whiteouts": exclusions})
        (BASE / "progress.json").write_text(json.dumps(receipt, indent=2) + "\n")
        archive.unlink()
    receipt["finished_unix"] = time.time()
    receipt["completed"] = True
    (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("runtime extracted", receipt["expanded_bytes"], "bytes", flush=True)


if __name__ == "__main__":
    main()
