import ast,hashlib,importlib.util,json,math,os
from pathlib import Path
PENDING=('protected_interfaces','surface_topology_and_distance','STEP_exchange','FEA')
BASELINE='de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63'
def require(value,message):
    if not value:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()

def write(path,value):
    with Path(path).open('x')as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def retain_cut_helpers(path,namespace):
    run=next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
    names=('entities','bbox','summary');nodes=[]
    for key in names:
        matches=[n for n in ast.walk(run)if isinstance(n,ast.FunctionDef)and n.name==key]
        require(len(matches)==1,'Unique retained raw-cut helper required');nodes.append(matches[0])
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace);return namespace['summary']

def local_gate_flags(residue,valid,solid_count,mass,bounds,plan):
    require(residue['native_topologically_empty'],'Baseline material removed: strict native Cut is nonempty')
    require(valid and solid_count==1,'Exactly one valid Solid required')
    require(math.isfinite(mass)and 0<mass<=1.3,'Existing 1.30kg mass ceiling failed')
    require(all(math.isfinite(c)for row in bounds for c in row),'Nonfinite bounds')
    require(all(bounds[0][i]>=plan['minimum_xyz_mm'][i]-plan['existing_bound_guard_mm']and bounds[1][i]<=plan['maximum_xyz_mm'][i]+plan['existing_bound_guard_mm']for i in range(3)),'Existing global bounds failed')
    return dict(local_geometry_checks_passed=True,candidate_qualified=False,downstream_checks={k:'PENDING'for k in PENDING})
