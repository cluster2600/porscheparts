set -e
job=/workspace/jobs/fan-airflow-sweep-20260929
src="$job/twins/993-engine-cooling-fan-system-f0/source"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUDA_VISIBLE_DEVICES=3
"$job/venv/bin/python" "$src/sweep_fan_airflow.py" prepare "$job/cfd/e-control" --source "$job/geometry/e-control" --device cuda:0 > "$job/prepare-control.log" 2>&1
bash "$src/run_reference_cfd.sh" "$job/cfd/e-control/case"
"$job/venv/bin/python" "$src/summarize_fan_cfd.py" "$job/cfd/e-control/case"
