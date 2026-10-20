"""Authorized metadata-only selected CPython/provider/stdlib/OS query."""
import copy,ctypes,fractions,hashlib,importlib.util,itertools,json,math,os,pathlib,re,resource,signal,struct,subprocess,sys,time,traceback,unittest
class DlInfo(ctypes.Structure):
    _fields_=[("name",ctypes.c_char_p),("base",ctypes.c_void_p),("symbol",ctypes.c_char_p),("address",ctypes.c_void_p)]
info=DlInfo();dladdr=ctypes.CDLL(None).dladdr
dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];dladdr.restype=ctypes.c_int
ok=dladdr(ctypes.cast(ctypes.pythonapi.Py_GetVersion,ctypes.c_void_p),ctypes.byref(info))
if not ok or not info.name:raise RuntimeError("Selected Python provider metadata unavailable")
provider=info.name.decode("utf-8")
modules={}
for name,module in sorted(sys.modules.items()):
    if name=="__main__" or module is None:continue
    spec=getattr(module,"__spec__",None);origin=getattr(spec,"origin",None)
    modules[name]=dict(origin=origin,file=getattr(module,"__file__",None))
os_build=subprocess.run(["/usr/bin/sw_vers","-buildVersion"],capture_output=True,text=True,check=True,timeout=5)
print(json.dumps(dict(schema="962-current24-flip-synthetic-selected-python-query/v1",executable=sys.executable,resolved_executable=str(pathlib.Path(sys.executable).resolve()),version=sys.version,version_info=list(sys.version_info),implementation=sys.implementation.name,byteorder=sys.byteorder,pointer_bytes=struct.calcsize("P"),base_prefix=sys.base_prefix,prefix=sys.prefix,flags=dict(isolated=sys.flags.isolated,no_user_site=sys.flags.no_user_site,ignore_environment=sys.flags.ignore_environment,dont_write_bytecode=sys.flags.dont_write_bytecode,optimize=sys.flags.optimize),Py_GetVersion_provider=provider,resolved_provider=str(pathlib.Path(provider).resolve()),OS_build=os_build.stdout.strip(),uname=dict(sysname=os.uname().sysname,release=os.uname().release,machine=os.uname().machine),module_origins=modules,environment_dumped=False,worker_fixture_or_real_data_imported=False,scientific_package_imported=False),sort_keys=True,indent=2))
