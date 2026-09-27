import subprocess,json

def run(args):
 r=subprocess.run(['docker','exec','-e','OPENCLAW_CONFIG_PATH=/state/research935.json','cad-openclaw','openclaw',*args],text=True,capture_output=True,timeout=45)
 if r.returncode:raise RuntimeError(r.stderr[-1500:])
 return r.stdout
subprocess.run(['docker','exec','cad-openclaw','cp','/etc/openclaw/cad.json','/state/research935.json'],check=True)
run(['config','set','tools.allow','["read","write","edit","web_fetch"]','--strict-json'])
run(['config','set','tools.web.fetch.enabled','true','--strict-json'])
run(['config','set','tools.web.search.enabled','false','--strict-json'])
for i in range(1,25):
 name=f'research935-{i:02d}'
 out=run(['agents','add',name,'--workspace',f'/workspace/research935/{name}','--model','local/nemotron-cad','--non-interactive','--json'])
 print(json.dumps({'agent':name,'created':True}),flush=True)
