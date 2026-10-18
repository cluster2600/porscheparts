"""Only reposition the Figure33 peak annotation; preserve all001 sources/results."""
from pathlib import Path
import difflib,hashlib,json
H=Path(__file__).resolve().parent;O=H.with_name('carrier-first-window-stock-FEA-figure-preparation-001');old=(O/'figure.py').read_text();a="xytext=(12,18)";b="xytext=(30,-55)";assert old.count(a)==1;s=old.replace(a,b);assert s.replace(b,a)==old
(H/'figure.py').write_text(s);(H/'source-changes.json').write_text(json.dumps({'original':str((O/'figure.py').relative_to(H.parents[1])),'original_sha256':hashlib.sha256(old.encode()).hexdigest(),'derived_sha256':hashlib.sha256(s.encode()).hexdigest(),'substitutions':[[a,b,1]],'whole_inverse_byteexact':True},indent=2)+'\n');(H/'figure-from-Figure31.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=str(O/'figure.py'),tofile=str(H/'figure.py'))))
for name in ['prepare.py','prepare-source-changes.json','prepare-from-Figure31.diff','ARMING.md']:(H/name).write_bytes((O/name).read_bytes())
t=(O/'selfcheck.py').read_text();a="OLD = ROOT / 'work/carrier-functional-law-FEA-figure-preparation-001'";b="OLD = ROOT / 'work/carrier-first-window-stock-FEA-figure-preparation-001'";assert t.count(a)==1;t=t.replace(a,b)
a="    def test_actual_whole_case_metadata(self):";b="""    def test_only_annotation_offset_changes(self):
        text=(HERE/'figure.py').read_text();old=(OLD/'figure.py').read_text()
        self.assertEqual(text.replace('xytext=(30,-55)','xytext=(12,18)'),old)
        self.assertEqual(text.count('xytext=(30,-55)'),1)
        self.assertEqual(json.loads((HERE/'source-changes.json').read_text())['substitutions'],[['xytext=(12,18)','xytext=(30,-55)',1]])

"""+a;assert t.count(a)==1;t=t.replace(a,b);(H/'selfcheck.py').write_text(t)
readme=(O/'README.md').read_text().replace('This unarmed source packet derives the closed Figure31 renderer.','Revision002 preserves the numerically closed001 renderer and moves only the orange Global IP peak label offset from (12,18) to (30,−55) points. Its actual PNG and PDF001 title overlap is retained under ROOT49165d4f. All field, camera, crop, scale and runtime settings remain identical. This unarmed source packet retains the Figure31 calculations.');(H/'README.md').write_text(readme)
print(hashlib.sha256(s.encode()).hexdigest())
