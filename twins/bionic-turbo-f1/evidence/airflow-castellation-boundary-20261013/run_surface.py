import json,shutil
from pathlib import Path
from run_native import execute
root=Path('work/bionic-airflow-20261012');parent=root/'outer-wall-bisect-086';case=root/'castellation-target-089'
shutil.copytree(parent/'system',case/'system')
r=execute(case,'surfaceCheck constant/triSurface/collar.stl > log.surfaceCheck 2>&1',[parent]);assert r['native_exit_code']==0
