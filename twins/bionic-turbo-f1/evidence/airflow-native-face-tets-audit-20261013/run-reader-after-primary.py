"""Single exclusive supervisor: launch reader only after successful primary."""
import json,os,subprocess,time
from pathlib import Path
w=Path(__file__).parent
with (w/'reader-supervisor.json').open('x') as f:json.dump({'pid':os.getpid(),'started_unix':time.time(),'primary_pid':43613,'reader_launched':False},f)
while not (w/'primary.exit').exists():time.sleep(5)
assert (w/'primary.exit').read_text().strip()=='0','Primary did not complete successfully; no reader launched'
assert (w/'readback.json').exists()
with (w/'reader-launch.json').open('x') as f:json.dump({'supervisor_pid':os.getpid(),'launched_unix':time.time()},f)
with (w/'independent.log').open('x') as log:
 p=subprocess.Popen(['work/bionic-tools/bin/python','-u',str(w/'verify_face_tets.py')],stdout=log,stderr=subprocess.STDOUT)
 with (w/'reader-pid.json').open('x') as f:json.dump({'pid':p.pid,'started_unix':time.time()},f)
 code=p.wait()
with (w/'independent.exit').open('x') as f:f.write(str(code)+'\n')
raise SystemExit(code)
