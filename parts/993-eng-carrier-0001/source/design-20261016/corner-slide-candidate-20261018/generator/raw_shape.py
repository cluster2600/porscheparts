import importlib.util
from pathlib import Path
p=Path(__file__).with_name('local_gates.py')
s=importlib.util.spec_from_file_location('_raw_local_gate',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
require,sha=m.require,m.sha
def preserved_shape(raw,path,writer):
    if raw is None:return dict(path=None,sha256=None,reason='no_safe_native_result_available')
    if raw.IsNull():return dict(path=None,sha256=None,reason='native_result_is_null')
    require(writer(raw,str(path))is True,'Raw native BREP preservation failed');return dict(path=path.name,sha256=sha(path),reason=None)
