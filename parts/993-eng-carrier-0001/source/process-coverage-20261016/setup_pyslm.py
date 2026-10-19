"""Install the pinned macOS arm64/Python 3.11 PySLM runtime in a durable directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent


def install(directory):
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Run this installer with Python 3.11")
    directory = Path(directory).resolve()
    upstream = json.loads((SOURCE / "upstream.json").read_text())
    patch = SOURCE / "pyslm-exact-support-domains.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != upstream["patch_sha256"]:
        raise RuntimeError("PySLM patch hash mismatch")
    directory.mkdir(parents=True, exist_ok=False)
    checkout, environment = directory / "source", directory / "env"
    subprocess.run(["git", "clone", upstream["repository"], str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", upstream["revision"]], check=True)
    subprocess.run(["git", "-C", str(checkout), "apply", str(patch)], check=True)
    native_hashes = {name: upstream[key] for name,key in [
        ('support.py','patched_support_py_sha256'),
        ('gridBlockSupport.py','patched_grid_py_sha256'),
        ('utils.py','patched_utils_py_sha256'),
        ('geometry.py','patched_geometry_py_sha256')]}
    for name, expected in native_hashes.items():
        if hashlib.sha256((checkout / 'pyslm/support' / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Patched PySLM source hash mismatch: ' + name)
    # Resolve uv's launcher symlink so the venv records the real stdlib home.
    subprocess.run([str(Path(sys.executable).resolve()), "-m", "venv", str(environment)], check=True)
    python = environment / "bin/python"
    subprocess.run([str(python), "-m", "pip", "install", "-r",
                    str(SOURCE / "requirements-macos-arm64-python311.lock.txt")], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(checkout)], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    # Exercise the installed library, including an independent 20 x 10 mm slice.
    check = '''import hashlib, inspect, json, numpy, pyslm, pyslm.support, trimesh
from importlib.metadata import version
p=pyslm.Part("install_witness")
p.setGeometry(trimesh.creation.box((20,10,2)),fixGeometry=False,mergeVertices=False)
polygons=p.getVectorSlice(0,returnCoordPaths=False,fixPolygons=False)
assert len(polygons)==1 and abs(polygons[0].area-200)<1e-8
assert numpy.__version__=="1.26.4" and version("PythonSLM")=="0.6.1"
print(json.dumps({"packages":{n:version(n) for n in ["PythonSLM","numpy","trimesh","shapely","pyclipr","manifold3d","vispy","PyQt5"]},"installed_support_py_sha256":hashlib.sha256(open(inspect.getfile(pyslm.support.BlockSupportGenerator),"rb").read()).hexdigest(),"installed_source_sha256":{name:hashlib.sha256((__import__("pathlib").Path(inspect.getfile(pyslm.support.BlockSupportGenerator)).parent/name).read_bytes()).hexdigest() for name in ["support.py","gridBlockSupport.py","utils.py","geometry.py"]}}))
'''
    result = subprocess.check_output([str(python), "-c", check], text=True)
    readiness = json.loads(result)
    if readiness["installed_source_sha256"] != native_hashes:
        raise RuntimeError("Installed PySLM source differs from the pinned patch")
    readiness.update({"python": str(python), "source": str(checkout), "upstream": upstream,
                      "installer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "requirements_sha256": hashlib.sha256((SOURCE / "requirements-macos-arm64-python311.lock.txt").read_bytes()).hexdigest()})
    (directory / "runtime.json").write_text(json.dumps(readiness, indent=2) + "\n")
    return readiness


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(install(parser.parse_args().directory), indent=2))
