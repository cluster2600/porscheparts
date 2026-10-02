job=/workspace/jobs/fan-airflow-sweep-20260929
src="$job/twins/993-engine-cooling-fan-system-f0/source"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUDA_VISIBLE_DEVICES=3
for geometry in "$job"/geometry/*/; do
 test -f "$geometry/generation.json" || continue
 name=$(basename "$geometry")
 "$job/venv/bin/python" "$src/sweep_fan_airflow.py" screen "$job/screens/$name.json" --source "$geometry/rotor-mm.stl" --device cuda:0 > "$job/screens/$name.log" 2>&1
 printf '%s %s\n' "$name" "$?"
done
