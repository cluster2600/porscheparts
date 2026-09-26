import json,tarfile
from pathlib import Path
base=Path(__file__).resolve().parent
with tarfile.open(base/'results-snapshot.tar.gz') as t:
 for m in t.getmembers():
  parts=Path(m.name).parts
  if m.isfile() and len(parts)==3 and parts[1].startswith('research935-') and parts[2] in {'response.json','status.json','prompt.md','stderr.log','response.initial.json','response.retry.json','retry-prompt.md','retry-status.json','retry.stderr.log'}:
   p=base/'reports'/parts[1]/parts[2];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
records=[]
for p in sorted((base/'reports').glob('*/response.json')):
 d=json.loads(p.read_text());txt='\n'.join(x.get('text','') for x in d.get('payloads',[]))
 if not txt:continue
 (p.parent/'findings.md').write_text('Rapport brut OpenClaw — conclusions à contrôler.\n\n'+txt)
 meta=d.get('meta',{});agent=meta.get('agentMeta',{});receipt=agent.get('terminalReceipt',{})
 status=json.loads((p.parent/'status.json').read_text())
 attempts=[d]
 initial=p.parent/'response.initial.json'
 if initial.exists():attempts.insert(0,json.loads(initial.read_text()))
 successful_tools=sorted({tool for attempt in attempts for tool in attempt.get('meta',{}).get('agentMeta',{}).get('terminalReceipt',{}).get('successfulToolNames',[])})
 records.append({**status,'model':agent.get('model'),'review_status':'raw_unapproved','aborted':meta.get('aborted'),'stop_reason':meta.get('stopReason'),'report_complete':meta.get('stopReason')=='stop' and not meta.get('aborted'),'successful_tools':successful_tools,'attempt_count':len(attempts),'run_id':receipt.get('runId'),'tokens':agent.get('usage',{}).get('total'),'report':str(p.parent.relative_to(base)/'findings.md')})
assert len({r['agent'] for r in records})==len(records)<=24
(base/'execution-evidence.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print(json.dumps({'reports':len(records),'with_web_fetch':sum('web_fetch' in r['successful_tools'] for r in records),'executions_successful':sum(r['returncode']==0 and not r['aborted'] for r in records),'reports_complete':sum(r['report_complete'] for r in records)},ensure_ascii=False))
