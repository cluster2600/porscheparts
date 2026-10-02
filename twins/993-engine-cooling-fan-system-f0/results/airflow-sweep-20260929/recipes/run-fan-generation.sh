set -e
job=/workspace/jobs/fan-airflow-sweep-20260929
cd "$job"
rm -f "$job/twins/993-engine-cooling-fan-system-f0/source/picogk-reference/._Program.cs"
src="$job/twins/993-engine-cooling-fan-system-f0/source"

dotnet build "$src/picogk-reference/Reference.csproj" -o "$job/build" > "$job/build.log" 2>&1
cp /app/PicoGK.dll "$job/build/"
cp /app/picogk.26.2.so "$job/build/"
mkdir -p "$job/geometry" "$job/screens"
export DOTNET_PROCESSOR_COUNT=4
export LD_LIBRARY_PATH=/app:/opt/picogk-native/lib
python3 - <<'PY'
from pathlib import Path
import concurrent.futures, subprocess, os
root=Path('/workspace/jobs/fan-airflow-sweep-20260929')
names=['e-control']+[p.stem for p in sorted((root/'configs').glob('*.json')) if p.stem not in ['plan','e-control']]
def generate(name):
 with (root/'geometry'/f'{name}.log').open('w') as log:
  p=subprocess.run(['dotnet',str(root/'build/Reference.dll'),str(root/'configs'/f'{name}.json'),str(root/'geometry'/name)],stdout=log,stderr=subprocess.STDOUT)
 print(name,p.returncode,flush=True)
 if p.returncode: raise RuntimeError(name)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(generate,names))
PY
for geometry in "$job"/geometry/*/; do
 name=$(basename "$geometry")
 CUDA_VISIBLE_DEVICES=3 "$job/venv/bin/python" "$src/sweep_fan_airflow.py" screen "$job/screens/$name.json" --source "$geometry/rotor-mm.stl" --device cuda:0 > "$job/screens/$name.log" 2>&1
done
