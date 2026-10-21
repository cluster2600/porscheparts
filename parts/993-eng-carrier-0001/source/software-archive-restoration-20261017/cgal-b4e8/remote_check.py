"""Exact owned-prefix/scopes and read-only dependencies for this restoration."""
import hashlib,json,pathlib,platform,re,shutil,subprocess,sys
mode,p=sys.argv[1],json.loads(sys.argv[2]);root=pathlib.Path(p['prefix'])
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def query(unit):
    r=subprocess.run(['systemctl','--user','show',unit,'--no-pager','-p','LoadState','-p','ActiveState','-p','ControlGroup'],capture_output=True,text=True,timeout=5)
    d=dict(line.split('=',1)for line in r.stdout.splitlines()if '='in line)
    if r.returncode not in (0,1,4)or'LoadState'not in d or'ActiveState'not in d:raise ValueError('Query failure is not absence')
    if d['LoadState']=='not-found':
        if d['ActiveState']!='inactive'or d.get('ControlGroup'):raise ValueError('Invalid absent scope')
        return dict(d,absent=True)
    if r.returncode!=0:raise ValueError('Loaded scope query failed')
    return dict(d,absent=False)
def owner():
    if json.loads((root/'owner.json').read_text())!=p['owner']:raise ValueError('New prefix ownership differs')
def runtime():
    if platform.system()!='Linux'or platform.machine()!='x86_64':raise ValueError('Linux x86_64 required')
    if sha(p['support_receipt'])!=p['support_receipt_sha256']:raise ValueError('Retained dependency receipt changed')
    paths=dict(p['runtime_files']);paths[p['archive']]=p['archive_sha256']
    if any(sha(q)!=h for q,h in paths.items()):raise ValueError('Archive or runtime changed')
    mpfr=pathlib.Path(p['mpfr_header']);paths[str(mpfr.resolve())]=sha(mpfr)
    compiler=pathlib.Path(shutil.which('g++')).resolve();cmake=pathlib.Path(shutil.which('cmake')).resolve()
    if pathlib.Path('/usr/bin/g++').resolve()!=compiler or pathlib.Path('/usr/bin/cmake').resolve()!=cmake or pathlib.Path('/usr/bin/c++').resolve()!=compiler:raise ValueError('Sandbox tool paths differ')
    cc1=pathlib.Path(subprocess.run([str(compiler),'-print-prog-name=cc1plus'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()).resolve()
    tools={str(q):sha(q)for q in [compiler,cmake,cc1]}
    version=subprocess.run([str(compiler),'--version'],capture_output=True,text=True,check=True,timeout=5).stdout.splitlines()[0]
    return dict(runtime_files_sha256=paths,compiler_cmake_sha256=tools,compiler_version=version)
def sources():
    for name,h in p['copied_files'].items():
        q=root/name
        if q.is_symlink()or not q.is_file()or sha(q)!=h:raise ValueError('Uploaded source changed')
def restored():
    receipt=root/'source-restoration.json';d=json.loads(receipt.read_text())
    if d['status']!='pinned_experimental_source_restored'or d['archive_sha256']!=p['archive_sha256']or d['API_header_sha256']!=p['api_sha256']:raise ValueError('Restored archive receipt differs')
    base=root/'src'
    actual={str(q.relative_to(base)):sha(q)for q in base.rglob('*')if q.is_file()and not q.is_symlink()}
    links={str(q.relative_to(base)):str(q.readlink())for q in base.rglob('*')if q.is_symlink()}
    if actual!=d['source_files_sha256']or links!=d['source_symlinks']:raise ValueError('Restored source files or symlinks changed')
    return dict(source_restoration_receipt_sha256=sha(receipt),source_file_count=len(actual),source_symlink_count=len(links))
if mode=='preflight':
    state=runtime()
    if root.resolve()!=root or root.exists()or root.is_symlink():raise ValueError('Fresh exact prefix required')
    for unit in p['units']:
        if not query(unit)['absent']:raise ValueError('Scope not fresh')
    root.mkdir(mode=0o700)
    with (root/'owner.json').open('x')as f:json.dump(p['owner'],f,sort_keys=True)
    state.update(status='fresh_owned_prefix_preflight_passed',prefix=str(root),owner=p['owner'])
elif mode=='cleanup':
    owner();states={}
    for unit in p['attempted_units']:
        d=query(unit)
        if not d['absent']and d['ActiveState']not in ('inactive','failed'):
            if pathlib.PurePosixPath(d.get('ControlGroup','')).name!=unit:raise ValueError('Scope ownership differs')
            for action in ('kill','stop'):
                q=subprocess.run(['systemctl','--user',action,unit],capture_output=True,text=True,timeout=8)
                if q.returncode!=0:raise ValueError('Exact scope cleanup failed')
            d=query(unit)
        if not d['absent']and d['ActiveState']not in ('inactive','failed'):raise ValueError('Scope still active')
        states[unit]=d
    state=dict(status='owned_scopes_inactive_or_absent_verified',scopes=states)
elif mode in ('uploaded','restored','built','post'):
    owner();state=runtime()
    if state!=p['runtime_before']:raise ValueError('Read-only toolchain changed')
    sources();state.update(status='copied_sources_and_runtime_verified',copied_sources_sha256=p['copied_files'])
    if mode in ('restored','built','post'):state.update(restored())
    if mode in ('built','post'):
        binary=root/'build/carrier_soup_boolean';dep=root/'build/CMakeFiles/carrier_soup_boolean.dir/soup_boolean.cpp.o.d'
        if not binary.is_file()or binary.is_symlink():raise ValueError('New binary missing')
        linked=subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=True,timeout=5).stdout
        libraries={str(pathlib.Path(q).resolve()):sha(pathlib.Path(q).resolve())for q in re.findall(r'(/[^\s()]+)',linked)if pathlib.Path(q).is_file()}
        headers={str(pathlib.Path(q).resolve()):sha(q)for q in dep.read_text().replace('\\\n',' ').split()[1:]if pathlib.Path(q).is_file()}
        state.update(binary_sha256=sha(binary),linked_libraries_sha256=libraries,compiled_headers_sha256=headers)
    if mode=='post':
        smoke=root/'smoke/smoke-receipt.json';d=json.loads(smoke.read_text())
        if d.get('status')!='three_existing_binary_witnesses_passed'or d['binary_sha256']!=state['binary_sha256']or len(d['cases'])!=3:raise ValueError('Native smoke missing or refused')
        for row in d['cases']:
            job=root/'smoke'/row['name']
            if any(sha(job/name)!=row[key]for name,key in [('audit.json','audit_sha256'),('native.json','native_sha256'),('result.npz','result_sha256'),('result.mesh64.exact','exact_result_sha256')]):raise ValueError('Smoke output changed')
        state.update(smoke_receipt_sha256=sha(smoke),smoke=d)
else:raise ValueError('Unknown exact metadata mode')
print(json.dumps(state,sort_keys=True))
