#!/bin/sh
# CPU-only disposable-container dependency test. No GPU, model key or asset.
# Invoke under timeout 600s, --cpus 2 --memory 4g; only new /opt/m64-* paths.
set -eu
umask 077
test ! -e /opt/m64-simready-validate
test ! -e /opt/m64-simready-foundation
test ! -e /opt/m64-usd-convert-cad-guide
original_head=$(git -C /opt/simready-foundation rev-parse HEAD)
# The image's filtered clone contains the old commit but not necessarily its
# blobs. Materialize a separate pinned public checkout; never mutate the old one.
GIT_LFS_SKIP_SMUDGE=1 git clone --filter=blob:none --no-checkout https://github.com/NVIDIA/simready-foundation.git /opt/m64-simready-foundation
git -C /opt/m64-simready-foundation sparse-checkout init --cone
git -C /opt/m64-simready-foundation sparse-checkout set nv_core skills
GIT_LFS_SKIP_SMUDGE=1 git -C /opt/m64-simready-foundation checkout --detach a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3
test -z "$(git -C /opt/m64-simready-foundation status --porcelain --untracked-files=no)"
# NVIDIA preflight verifies the Git commit of the CAD capability guide, even
# though conversion itself uses the existing isolated usd-convert-cad wheel.
GIT_LFS_SKIP_SMUDGE=1 git clone --filter=blob:none --no-checkout https://github.com/NVIDIA-Omniverse/usd-convert-cad.git /opt/m64-usd-convert-cad-guide
GIT_LFS_SKIP_SMUDGE=1 git -C /opt/m64-usd-convert-cad-guide checkout --detach 208fe2c1cd71ae2bb7bd825daf712617000ae028
test -z "$(git -C /opt/m64-usd-convert-cad-guide status --porcelain --untracked-files=no)"
python3.12 -m venv /opt/m64-simready-validate
/opt/simready-validation/bin/uv --no-config pip install --python /opt/m64-simready-validate/bin/python \
    --index-url https://pypi.org/simple \
    usd-exchange==2.3.0 omniverse-asset-validator==1.18.0 omniverse-usd-profiles==1.10.22 \
    numpy==1.26.4 jinja2==3.1.6 markdown-it-py==4.2.0 markupsafe==3.0.3 mdurl==0.1.2 PyYAML==6.0.2
/opt/simready-validation/bin/uv --no-config pip install --python /opt/m64-simready-validate/bin/python \
    --index-url https://pypi.org/simple --no-deps simready-validate==2026.4.8
test "$(git -C /opt/simready-foundation rev-parse HEAD)" = "${original_head}"
/opt/m64-simready-validate/bin/python -I - <<'PY'
import importlib.metadata as md
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy
import omni.asset_validator
import yaml
from pxr import Usd, UsdGeom, UsdPhysics

expected = {
    "usd-exchange": "2.3.0", "omniverse-asset-validator": "1.18.0",
    "omniverse-usd-profiles": "1.10.22", "simready-validate": "2026.4.8",
    "numpy": "1.26.4", "jinja2": "3.1.6", "markdown-it-py": "4.2.0",
    "markupsafe": "3.0.3", "mdurl": "0.1.2", "PyYAML": "6.0.2",
}
actual = {name: md.version(name) for name in expected}
assert actual == expected, actual
foundation = Path("/opt/m64-simready-foundation")
commit = subprocess.check_output(["git", "-C", str(foundation), "rev-parse", "HEAD"], text=True).strip()
assert commit == "a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3"
cad_guide = Path("/opt/m64-usd-convert-cad-guide")
cad_guide_commit = subprocess.check_output(["git", "-C", str(cad_guide), "rev-parse", "HEAD"], text=True).strip()
assert cad_guide_commit == "208fe2c1cd71ae2bb7bd825daf712617000ae028"
assert not subprocess.check_output(["git", "-C", str(cad_guide), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
specs = foundation / "nv_core/sr_specs/docs"
assert specs.is_dir()
profile_index = specs / "profiles/profiles.toml"
assert profile_index.is_file() and profile_index.stat().st_size > 0
assert not profile_index.read_bytes().startswith(b"version https://git-lfs")
assert not subprocess.check_output(["git", "-C", str(foundation), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
environment = {"PATH": "/opt/m64-simready-validate/bin:/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
help_result = subprocess.run(["/opt/m64-simready-validate/bin/simready-validate", "--help"], env=environment, capture_output=True, timeout=30)
assert help_result.returncode == 0, "pinned simready-validate --help failed"
print(json.dumps({
    "schema_version": "1.0.0", "test": "m64-isolated-pinned-runtime-cpu",
    "foundation_commit": commit, "cad_guide_commit": cad_guide_commit, "versions": actual,
    "imports_passed": True, "cli_help_passed": True, "usd_version": Usd.GetVersion(),
    "specs_present": True, "profile_index_present": True, "pinned_worktree_clean": True,
    "production_image_tested": False,
    "gpu_tested": False, "asset_simulated": False, "manufacturing_authorized": False,
}, sort_keys=True), flush=True)
PY
