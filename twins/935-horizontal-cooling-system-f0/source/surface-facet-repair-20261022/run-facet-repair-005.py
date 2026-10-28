"""Run the locally constrained surface repair with preserved inputs and bounded resources."""
import hashlib
import json
import resource
import subprocess
import time
import sys
from pathlib import Path

p=Path('/home/lolman/935-surface-facet-repair-20261022')
source=Path('/home/lolman/935-analysis-patches-20261022/surface-001/candidate-quantized.off')
limit=sys.argv[1];names={'0.02':'limit-020-005'};assert limit in names
exe=p/'build-005/repair_poor_facets'
sha=lambda f:hashlib.file_digest(Path(f).open('rb'),'sha256').hexdigest()
assert sha(source)=='addba09e1ee2d7814f19a3262ac0910f0bc5b9d58dd43ada3254444845392e5a'
out=p/names[limit];out.mkdir(mode=0o700)
report={'source_sha256':sha(__file__),'cpp_sha256':sha(p/'policy-005/repair_poor_facets.cpp'),'CMake_sha256':sha(p/'CMakeLists.txt'),'binary_sha256':sha(exe),'input_reference_OFF_sha256':sha(source),'policy_patch_sha256':sha(p/'poor-only-classifier-005.patch'),'policy_limit_native_units':float(limit),'steps':[],'scale_verified':False,'complete_surface_bound_established':False,'CFD_accepted':False,'manufacturing_authorized':False}
def save():
    (out/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
def run(name,args,seconds):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**3,2*1024**3))
    started=time.monotonic();reason=None
    with (out/(name+'.stdout')).open('x') as stdout,(out/(name+'.stderr')).open('x') as stderr:
        try:
            result=subprocess.run([str(exe),*map(str,args)],stdout=stdout,stderr=stderr,timeout=seconds,preexec_fn=limits)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=None;reason='wall_time_limit'
    report['steps'].append({'name':name,'command':[str(exe),*map(str,args)],'exit':code,'stop_reason':reason,'elapsed_s':time.monotonic()-started,'timeout_s':seconds,'memory_limit_GiB':6,'limits_applied_before_start':True});save();return code
assert run('self-test',['--self-test'],30)==0
guard=out/'guard-existing.off';guard.write_text('preserved output guard\n');guard_sha=sha(guard)
assert run('existing-output',[out/'absent.off',guard],30)==2 and sha(guard)==guard_sha
link=out/'guard-dangling.off';link.symlink_to('absent.off')
assert run('dangling-output',[out/'absent.off',link],30)==2 and link.is_symlink() and not link.exists()
assert run('unsupported-limit',[out/'absent.off',out/'invalid.off','0.03'],30)==2 and not (out/'invalid.off').exists()
assert run('invalid-limit',[out/'absent.off',out/'invalid.off','0.01junk'],30)==2 and not (out/'invalid.off').exists()
assert run('rotor',[source,out/'candidate.off',limit],300)==0
assert sha(source)==report['input_reference_OFF_sha256'] and sha(exe)==report['binary_sha256'] and sha(p/'policy-005/repair_poor_facets.cpp')==report['cpp_sha256']
metrics=json.loads((out/'rotor.stdout').read_text());assert metrics['input_faces']==873444 and metrics['input_poor_faces']==189 and metrics['Euler_characteristic_before']==metrics['Euler_characteristic_after']==-10 and metrics['connected_components']==1 and metrics['outside_patch_vertices_and_faces_unchanged']
report.update(status='local_repair_candidate_pending_complete_independent_bound_and_topology_checks',output_OFF_sha256=sha(out/'candidate.off'),input_unchanged=True,metrics=metrics);save();print(json.dumps(report),flush=True)
