#!/usr/bin/env bash
set -euo pipefail

# The Qwen base pins NCCL globally; Kit tooling has its own hash-locked Python set.
unset UV_CONSTRAINT UV_OVERRIDE PIP_CONSTRAINT PIP_REQUIREMENT

if [[ "${NVIDIA_EULA_ACCEPTED:-}" != yes ]]; then
    echo 'NVIDIA_EULA_ACCEPTED=yes is required after explicit acceptance of NVIDIA Software License Agreement and Omniverse Product-Specific Terms.' >&2
    exit 2
fi
recipe=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
build_dir=${KIT_BUILD_DIR:-/tmp/station-kit-build}
runtime_dir=${KIT_RUNTIME_DIR:-/opt/station-kit-runtime}
revision=3f4b33387f58e5c6694b5479559c945fb80bb625
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git "$build_dir"
git -C "$build_dir" checkout --detach "$revision"
cd "$build_dir"
# Official generator records acceptance only after the explicit build argument.
./repo.sh template new --input 'Yes;Application>;[kit_base_editor]: Kit Base Editor;station.editor;PicoGK Station;0.1.0;No'
test -s source/apps/station.editor.kit
cp "$recipe/station.editor_streaming.kit" source/apps/
python3 - <<'PY'
from pathlib import Path
path = Path('repo.toml')
text = path.read_text()
old = '"${root}/source/apps/station.editor.kit"'
assert text.count(old) == 1, 'Unexpected upstream precache configuration'
path.write_text(text.replace(old, '"${root}/source/apps/station.editor_streaming.kit"'))
with Path('premake5.lua').open('a') as output:
    output.write('\ndefine_app("station.editor_streaming")\n')
PY
./repo.sh build --release
# Dereference packman/cache links so the final image needs no build cache.
mkdir -p "$runtime_dir"
cp -aL _build/linux-x86_64/release/. "$runtime_dir/"
test -x "$runtime_dir/kit/kit"
test -s "$runtime_dir/apps/station.editor_streaming.kit"
cp LICENSE PRODUCT_TERMS_OMNIVERSE "$runtime_dir/"
printf '%s\n' "$revision" > "$runtime_dir/kit-app-template-revision.txt"
install -m 755 "$recipe/launch.py" /usr/local/bin/station-kit
install -m 644 "$recipe/open_scene.py" "$runtime_dir/open_scene.py"
