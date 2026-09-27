import concurrent.futures,json,subprocess,time
from pathlib import Path
base=Path('/srv/cad/agent-workspace/research935')
# Reuse the completed public research sessions; preserve every original response.
def retry(folder):
 name=folder.name;i=int(name[-2:]);old=json.loads((folder/'response.json').read_text())
 if old.get('meta',{}).get('stopReason')=='stop' and i not in (3,7,12):return
 prompt='''Reprends uniquement ta mission précédente. Fournis directement le rapport final en français en trois puces : fait avec URL, applicabilité au scan, information manquante. Ne compte pas les mots. N'expose pas ta préparation. Ne recommence pas les consultations si elles ont déjà eu lieu. La variante précise du scan n'est PAS identifiée. Rien ne permet de dire que cette culasse est une Baby, K3, K4 ou Moby Dick. Les ailettes d'une culasse ne sont pas la carrosserie de la voiture. Les capacités d'un atelier ne sont pas des cotes disponibles de notre pièce. N'invente aucune dimension.\nNote de contrôle Codex: la page https://www.xtremecylinderheads.com/programs consultée directement décrit bien Lost Wax casting, RR350 aluminium et HIP. Si ton extraction ne contenait pas ce passage, mentionne la limite de ton extraction. Cela ne prouve PAS que notre pièce soit une Xtreme de ce programme. Le matériau de notre scan reste inconnu.'''
 (folder/'retry-prompt.md').write_text(prompt)
 (folder/'response.initial.json').write_text(json.dumps(old,ensure_ascii=False,indent=2))
 cmd=['docker','exec','-e','OPENCLAW_CONFIG_PATH=/state/research935.json','-e',f'OPENCLAW_STATE_DIR=/state/research935-state-{i:02d}','cad-openclaw','openclaw','agent','--local','--agent',name,'--session-id',f'{name}-20260926','--message-file',f'/workspace/research935/{name}/retry-prompt.md','--thinking','off','--timeout','120','--json']
 start=time.time()
 try:
  r=subprocess.run(cmd,text=True,capture_output=True,timeout=140)
  (folder/'response.retry.json').write_text(r.stdout);(folder/'retry.stderr.log').write_text(r.stderr)
  d=json.loads(r.stdout)
  complete=r.returncode==0 and d.get('meta',{}).get('stopReason')=='stop'
  if complete:(folder/'response.json').write_text(r.stdout)
  out={'agent':name,'retry_complete':complete,'returncode':r.returncode,'seconds':round(time.time()-start,1)}
 except Exception as e:out={'agent':name,'retry_complete':False,'error':type(e).__name__}
 (folder/'retry-status.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
if __name__=='__main__':
 while not (base/'manifest.json').exists():time.sleep(5)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(retry,sorted(base.glob('research935-*'))))
