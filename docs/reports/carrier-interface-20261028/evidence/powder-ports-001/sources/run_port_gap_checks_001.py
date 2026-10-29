import hashlib,json,subprocess,sys,time
from pathlib import Path
w=Path('work/carrier-interface-20261028');output=w/'cgal-port-gap-batch-001';assert not output.exists();output.mkdir();runner=w/'cgal-port-gap-worker-002/run_check.py';binary=w/'cgal-port-gap-compile-002/output/check-hausdorff';inputs=w/'cgal-port-inputs-001';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();start=time.monotonic();cases=[]
(output/'contract.json').write_text(json.dumps(dict(source_sha256=sha(Path(__file__)),runner_sha256=sha(runner),worker_sha256=sha(runner.with_name('check_self.cpp')),binary_sha256=sha(binary),required_cases=16,required_exact_gap_mm='10001/10000',each_container_cpus=1,each_container_memory_gib=6,manufacturing_authorized=False),indent=2)+'\n')
for network in range(8):
 for mode in ['voids','tools']:
  folder=w/('cgal-port-0-void-gap-001')if network==0 and mode=='voids'else output/f'network-{network}-{mode}'
  if not folder.exists():
   with(output/f'network-{network}-{mode}.log').open('w')as log:
    subprocess.run([sys.executable,str(runner),'--first',str(inputs/f'tool-{network}.mesh64'),'--second',str(inputs/f'other-{mode}-{network}.mesh64'),'--binary',str(binary),'--output',str(folder)],stdout=log,stderr=log,check=False)
  terminal=json.loads((folder/'actual-terminal.json').read_text());report=json.loads((folder/'output/assessment.json').read_text())if(folder/'output/assessment.json').exists()else None;passed=terminal['actual_returncode']==0 and terminal['container_removed']and terminal['inputs_unchanged']and report is not None and report['all_source_faces_covered'];cases.append(dict(network=network,target=mode,passed=passed,report=str(folder/'output/assessment.json'),terminal=str(folder/'actual-terminal.json'),exact_centroid_queries=report['exact_centroid_queries']if report else None));print(json.dumps(cases[-1]),flush=True)
passed=len(cases)==16 and all(c['passed']for c in cases);(output/'assessment.json').write_text(json.dumps(dict(status='all_sixteen_exact_gap_certificates_passed'if passed else'exact_gap_batch_refused',cases=cases,completed_cases=len(cases),passed_cases=sum(c['passed']for c in cases),elapsed_seconds=time.monotonic()-start,manufacturing_authorized=False),indent=2)+'\n')
