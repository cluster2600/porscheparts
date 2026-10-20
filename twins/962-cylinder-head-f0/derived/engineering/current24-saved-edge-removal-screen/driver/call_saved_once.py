"""HELD fixed saved-context caller. Root-owned external actual digest required."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,sys
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
X=E/'head-star-current24-edge-removal-saved-execution-prep-001'
D=E/'head-star-current24-edge-removal-saved-root-execution-001'
DRIVER=E/'head-star-current24-edge-removal-saved-driver-prep-001/collect_saved_edge_removal.py'
DRIVER_HELD=DRIVER.parent/'held-preparation.json'
def rec(path):
 data=path.read_bytes()
 return dict(path=path.relative_to(R).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]), 'External actual digest required'
actual_path=X/'actual-contract.json';assert rec(actual_path)['sha256']==sys.argv[1]
actual=json.loads(actual_path.read_text())
assert actual['schema']=='962-current24-fixed23-saved-edge-removal-held-actual/v1'
assert actual['caller']==rec(Path(__file__)) and actual['driver_source']==rec(DRIVER) and actual['driver_held']==rec(DRIVER_HELD)
assert str(Path(sys.executable).resolve())==actual['selected_interpreter']['path']
assert sys.flags.isolated==1 and sys.flags.dont_write_bytecode==1 and sys.flags.no_site==1 and sys.flags.optimize==0
assert 'site' not in sys.modules and '_distutils_hack' not in sys.modules
assert all(actual[k] is False for k in ['saved_execution_authorized','native_execution_authorized','geometry_write_authorized','physical_acceptance','automatic_retry'])
spec=importlib.util.spec_from_file_location('held_fixed23_saved_edge_removal_driver',DRIVER)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result,encoded=module.build_saved_report() # Exactly ONE fixed case call; no retry.
if type(encoded) is not bytes or len(encoded)>32*1024**2:raise ValueError('Complete returnedbytes must fit32MiB')
path=D/'report.json'
with path.open('xb') as out:
 written=out.write(encoded);out.flush();os.fsync(out.fileno())
if written!=len(encoded) or path.read_bytes()!=encoded:raise ValueError('Complete returnedbytes readback required')
summary=dict(driver_calls=1,report=rec(path),procedure_preservation_passed=result.get('procedure_preservation_passed'),complete_context_byte_identical=result.get('complete_context_byte_identical'),selected_case_count=result.get('selected_case_count'),candidate_count=result.get('candidate_count'),complete_application_eligibility=result.get('complete_application_eligibility'),mesh_application_authorized=result.get('mesh_application_authorized'))
print(json.dumps(summary,sort_keys=True))
# Preserve the full returned report BEFORE refusing a failed preservation result.
if result.get('procedure_preservation_passed') is not True or result.get('complete_context_byte_identical') is not True:
 raise ValueError('Saved context/input preservation refused; complete report retained, no acceptance')
if result.get('complete_application_eligibility') is not None or result.get('mesh_application_authorized') is not False:
 raise ValueError('Eligibility must remain unavailable and application false')
