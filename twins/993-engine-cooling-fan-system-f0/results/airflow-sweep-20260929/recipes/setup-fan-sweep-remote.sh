set -eu
job=/workspace/jobs/fan-airflow-sweep-20260929
mkdir -p "$job"
python3 -m venv --system-site-packages "$job/venv"
"$job/venv/bin/pip" install 'warp-lang==1.17.0' 'trimesh==4.11.5' scipy matplotlib fast-simplification > "$job/setup-python.log" 2>&1
"$job/venv/bin/pip" install --no-deps 'nvidia-physicsnemo==2.2.2' >> "$job/setup-python.log" 2>&1
curl --fail --silent --show-error https://dl.openfoam.org/gpg.key -o "$job/openfoam.asc"
install -m 644 "$job/openfoam.asc" /etc/apt/trusted.gpg.d/openfoam-fan-study.asc
printf '%s\n' 'deb http://dl.openfoam.org/ubuntu noble main' > /etc/apt/sources.list.d/openfoam-fan-study.list
apt-get update > "$job/setup-foam.log" 2>&1
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openfoam14 >> "$job/setup-foam.log" 2>&1
CUDA_VISIBLE_DEVICES=3 "$job/venv/bin/python" - <<'PY'
import warp as wp,torch,trimesh
from physicsnemo.mesh import Mesh
wp.init()
print('Warp',wp.__version__, 'devices',wp.get_devices())
print('Torch',torch.__version__,'CUDA',torch.cuda.is_available())
PY
