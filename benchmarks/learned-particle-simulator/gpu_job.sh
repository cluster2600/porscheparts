#!/usr/bin/env bash
# WorldParticle fluid checks on a rented GPU. Everything it needs is public: the authors' code,
# their checkpoint and samples, and the case generator of this repository.
set -uo pipefail
W=/workspace/wp; mkdir -p $W && cd $W
exec > >(tee -a $W/job.log) 2>&1
echo "START $(date -u +%FT%TZ)"; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
pip install -q "numpy<2" open3d==0.19.0 pytorch-lightning==2.0.2 mdtraj einops msgpack zstandard pyyaml tqdm tensorboard "setuptools<81" scipy 2>&1 | tail -2
[ -d src ] || git clone -q https://github.com/WorldParticle/WorldParticle.git src
git -C src rev-parse HEAD > src-commit.txt
HF=https://huggingface.co/datasets/wclw1021/WorldParticle/resolve/main
for f in fancy_fluid/checkpoint/config.yaml fancy_fluid/checkpoint/final.ckpt fancy_fluid/dataset/66/66.npz cloth_on_ball/dataset/10/10.npz cloth_on_ball/checkpoint/config.yaml; do
  mkdir -p hf/$(dirname $f); [ -s hf/$f ] || curl -sL -o hf/$f $HF/$f
done
sha256sum hf/fancy_fluid/checkpoint/final.ckpt hf/fancy_fluid/dataset/66/66.npz
python load_weights_only.py hf/fancy_fluid/checkpoint/final.ckpt hf/fancy_fluid/checkpoint/weights-only.pt | tail -2
python make_cases.py hf cases
python -c "import open3d.ml.torch as m; import open3d; print('open3d', open3d.__version__, 'cuda ops', open3d.core.cuda.is_available())"
run() { # sample data_dir steps out
  local t0=$(date +%s)
  ( cd src && ATTN_IMPL=sdpa MPLCONFIGDIR=/tmp python inference.py --data_dir $2 --sample $1 --config $W/hf/fancy_fluid/checkpoint/config.yaml \
      --checkpoint $W/hf/fancy_fluid/checkpoint/weights-only.pt --num_steps $3 --dt 1 --output_dir $W/$4 --start 0 --end $(( $3 + 1 )) 2>&1 | grep -v "Warning\|warn\|pkg_resources" | tail -3 )
  echo "RUN $1 steps=$3 seconds=$(( $(date +%s) - t0 )) exit=$?"
}
run 66 $W/hf/fancy_fluid/dataset 599 out-fluid
run fluid-still $W/cases 300 out-cases
run fluid-dam $W/cases 500 out-cases
run fluid-still-training-tank $W/cases 300 out-cases
tar czf results.tgz out-fluid out-cases cases/fluid-still cases/fluid-dam cases/fluid-still-training-tank src-commit.txt job.log 2>/dev/null
ls -la results.tgz
echo "DONE $(date -u +%FT%TZ)"
