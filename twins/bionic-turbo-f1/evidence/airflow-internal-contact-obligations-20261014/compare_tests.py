"""Compare completed current test diagnostics to the preceding published phase."""
import hashlib,json,re
from pathlib import Path
w=Path(__file__).parent;b=Path('work/bionic-native-face-tets-audit-20261013')
exit_codes=json.loads((w/'test-exit-codes.json').read_text())
a=(w/'make-check.log').read_text();old=(b/'make-check.log').read_text();turbo=(w/'turbo-tests.log').read_text()
def labels(s):return re.findall(r'^(?:ERROR|FAIL): .+$',s,re.M)
def summary(s):return [x for x in s.splitlines() if x.startswith(('Ran ','FAILED (','OK ('))]
out={'base_phase':'PR254 native-face-tets-audit','current_labels':labels(a),'base_labels':labels(old),'same_labels':labels(a)==labels(old),'current_log_sha256':hashlib.sha256(a.encode()).hexdigest(),'base_log_sha256':hashlib.sha256(old.encode()).hexdigest(),'summary':summary(a),'turbo_summary':summary(turbo),'exit_codes':exit_codes,'tests_started_after_both_readers':True, 'cfd_benchmark':False}
with (w/'test-comparison.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out,indent=2))
