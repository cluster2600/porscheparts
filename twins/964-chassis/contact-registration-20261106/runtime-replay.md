# CPU USD validation replay — 6 November 2026

The [runtime receipt](runtime-receipt.json) records an executed Linux arm64 CPU
validation lane on Mac Docker. Its overall status is **needs_rerun**: software
readiness and the narrow synthetic witness passed; the historical rejected
[whole-body bundle](../monocoque/omniverse/README.md) failed Asset Validator and
the diagnostic `Prop-Robotics-Neutral@1.0.0` profile. This is not the reconstructed
cell or its engineering acceptance profile.

The image is `python@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54`.
Runtime pins are USD Exchange 2.3.0 / OpenUSD 25.5, Asset Validator 1.18.0,
USD Profiles 1.10.22, SimReady Validate 2026.4.8, NumPy 1.26.4, Jinja2 3.1.6,
markdown-it-py 4.2.0, MarkupSafe 3.0.3 and mdurl 0.1.2. PyYAML 6.0.1 bootstraps
the installed skill. Foundation is pinned to
`a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3` (`v2026.04.1`). The installed skill's
lock must match these pins; a different lock needs a new receipt.

Run from the repository root with Docker available, sufficient free disk and the
installed `omniverse-cad-to-simready` skill. About 203 MB of image and 206 MiB of private runtime/reports were
retained in the observed execution. Use a fresh output directory. The following
commands create only a bounded, disposable CPU container and private outputs;
they do not change existing workloads or install host packages.

The recorded execution used an existing pinned Foundation checkout. A later
readiness check found that checkout empty and the host Python environments
unavailable. A fresh private sparse checkout was recovered from the official
public repository at the same commit. The existing Linux container environment
then repeated the synthetic and minimum checks successfully and the same eight
profile failures, with networking disabled and source hashes unchanged. The
receipt keeps this recovery separate from the original execution. The commands
below use that fresh-checkout route and do not repair host environments.

```sh
set -eu
REPO_ROOT="$(pwd)"
OMNI_SKILL="$HOME/.codex/skills/nvidia-physical-ai-omniverse-cad-to-simready"
test -f "$REPO_ROOT/twins/964-chassis/monocoque/omniverse/bundle-001/monocoque.usda"
test -f "$OMNI_SKILL/upstream-versions.lock.json"
docker info --format '{{.Architecture}} {{.NCPU}}'
df -Pk "$REPO_ROOT"
REPLAY_OUTPUT="$(mktemp -d "$REPO_ROOT/work/964-cpu-validation.XXXXXX")"
FOUNDATION_ROOT="$REPLAY_OUTPUT/foundation"
GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 git -c credential.helper= -c core.askPass= \
  clone --filter=blob:none --sparse --depth 1 --branch v2026.04.1 --single-branch \
  https://github.com/NVIDIA/simready-foundation.git "$FOUNDATION_ROOT"
GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 git -C "$FOUNDATION_ROOT" \
  -c credential.helper= sparse-checkout set nv_core/sr_specs/docs
test "$(git -C "$FOUNDATION_ROOT" rev-parse HEAD)" = \
  a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3
docker pull --platform linux/arm64 \
  python@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
docker run --rm --init -i --platform linux/arm64 \
  --cpus 2 --memory 2g --pids-limit 256 \
  --mount "type=bind,source=$REPLAY_OUTPUT,target=/out" \
  --mount "type=bind,source=$OMNI_SKILL,target=/skill,readonly" \
  --mount "type=bind,source=$FOUNDATION_ROOT,target=/foundation,readonly" \
  --mount "type=bind,source=$REPO_ROOT/twins/964-chassis/monocoque/omniverse,target=/source,readonly" \
  python@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 \
  timeout --signal=TERM --kill-after=10s 900s sh -s <<'CONTAINER'
set -eu
export PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/foundation
apt-get update
apt-get install -y --no-install-recommends git git-lfs
rm -rf /var/lib/apt/lists/*
python -m venv /out/venvs/simready-validate
V=/out/venvs/simready-validate/bin
"$V/python" -m pip install --index-url https://pypi.org/simple \
  usd-exchange==2.3.0 omniverse-asset-validator==1.18.0 \
  omniverse-usd-profiles==1.10.22 numpy==1.26.4 jinja2==3.1.6 \
  markdown-it-py==4.2.0 markupsafe==3.0.3 mdurl==0.1.2 PyYAML==6.0.1
"$V/python" -m pip install --index-url https://pypi.org/simple \
  --no-deps simready-validate==2026.4.8
export PATH="$V:$PATH" SIMREADY_FOUNDATION_ROOT=/foundation
"$V/python" -m pip freeze > /out/installed-versions.txt
"$V/python" /skill/references/preflight/scripts/preflight.py \
  --targets validation --check-only --skip-content-agents --skip-deploy --skip-uv-sync \
  --home /out/home --state-root /out/state --venv-root /out/venvs --project-root /source \
  --source-asset /source/bundle-001/monocoque.usda \
  --report /out/preflight.json --markdown-report /out/preflight.md
export PHYSICAL_AI_PREFLIGHT_MANIFEST=/out/preflight.json PHYSICAL_AI_REQUIRE_PREFLIGHT=1
sha256sum /source/bundle-001/* > /out/source-before.sha256
"$V/python" - <<'PY'
from pxr import Usd, UsdGeom
s = Usd.Stage.CreateNew('/out/software-witness.usda')
w = UsdGeom.Xform.Define(s, '/World')
s.SetDefaultPrim(w.GetPrim())
UsdGeom.SetStageMetersPerUnit(s, 1.0)
UsdGeom.SetStageUpAxis(s, UsdGeom.Tokens.z)
UsdGeom.Cube.Define(s, '/World/SoftwareWitness').CreateSizeAttr(1.0)
s.GetRootLayer().Save()
PY
"$V/python" /skill/references/validate-usd-minimum/scripts/run.py \
  /out/software-witness.usda --report /out/synthetic-minimum.json
"$V/python" /skill/references/omni-asset-validate/scripts/run.py \
  --no-init-rules --rule StageMetadataChecker /out/software-witness.usda \
  --report /out/synthetic-metadata.json
"$V/simready-validate" --help > /out/cli-help.txt
"$V/python" /skill/references/validate-usd-minimum/scripts/run.py \
  /source/bundle-001/monocoque.usda --report /out/minimum.json
set +e
"$V/python" /skill/references/omni-asset-validate/scripts/run.py \
  /source/bundle-001/monocoque.usda --timeout 180 --report /out/asset-validator.json
asset_status=$?
"$V/python" /skill/references/simready-validate/scripts/run.py \
  /source/bundle-001/monocoque.usda --profile Prop-Robotics-Neutral \
  --foundation-root /foundation --report /out/simready-profile.json
profile_status=$?
set -e
sha256sum /source/bundle-001/* > /out/source-after.sha256
cmp /out/source-before.sha256 /out/source-after.sha256
printf 'Asset Validator exit: %s; profile exit: %s\n' "$asset_status" "$profile_status"
CONTAINER
```

Inspect each JSON verdict. A completed container is not a passing asset verdict.
The observed stage returned eight Asset Validator failures and six warnings,
including missing normals, untyped groups, zero-area/non-manifold geometry and
winding concerns. The formal profile returned eight failed requirements. Keep
those findings; do not select a different profile just to obtain a pass.

`GSP.001` is routed to the upstream FET005 family but repair is blocked: admitted
grasp contacts and final geometry are absent, and the automotive review context
is not robot pickup. No `--fix`, stamping, conformance repair or mechanical
property assignment is authorised by this replay. Native OVRTX/Kit captures and
vehicle engineering validation remain separate, outstanding work. Source files
remain read-only; publish only sanitised aggregates and hashes, retaining raw
logs, local paths and private source bytes outside Git.
