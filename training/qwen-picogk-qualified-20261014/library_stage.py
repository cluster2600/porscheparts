"""Separate source-grounded library selector course; never generate or run model code."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import request_contract as contract
pilot = contract.pilot
SUITE = Path('/Users/maxime/Developer/PicoGK')
OPERATIONS = {
    'scalar_vdb': ('leap71/PicoGK_SimulationExample', 'SimpleFluidSimulationInput.oGetDensityField/oGetViscosityField; ScalarField.bGetValue; synthetic VDB field exchange, not a CFD solver.'),
    'vector_vdb': ('leap71/PicoGK_SimulationExample', 'SimpleFluidSimulationInput.oGetVelocityField; VectorField.bGetValue; inspect velocity samples from a VDB, not a CFD solver.'),
    'quasicrystal': ('leap71/LEAP71_QuasiCrystals', 'PenrosePattern and QuasiCrystal.voxGetWireframe; native wireframe and VDB roundtrip.'),
    'geometry_frame': ('leap71/PicoGK.Geometry', 'Frame2d and Frame3d coordinate-frame arithmetic; experimental isolated net10.0 library, not a direct ShapeKernel replacement.'),
}
QUESTIONS = {
    'scalar_vdb': ('Read density and viscosity scalar values from a simulation VDB.', 'Lire la densité et la viscosité comme champs scalaires dans un VDB.', 'Dichte und Viskosität als Skalarfelder aus einer VDB lesen.', 'VDBから密度と粘度のスカラー値を読み取る。', '从VDB中读取密度和黏度标量值。'),
    'vector_vdb': ('Read three-component velocity values from a simulation VDB.', 'Lire les vecteurs de vitesse à trois composantes dans un VDB.', 'Dreikomponentige Geschwindigkeitsvektoren aus einer VDB lesen.', 'VDBから三成分の速度ベクトルを読み取る。', '从VDB中读取三分量速度向量。'),
    'quasicrystal': ('Construct a quasicrystal wireframe and an aperiodic Penrose pattern.', 'Construire un réseau filaire quasi-cristallin et un pavage de Penrose apériodique.', 'Ein quasikristallines Drahtmodell und ein aperiodisches Penrose-Muster erstellen.', '準結晶のワイヤーフレームと非周期的なペンローズ模様を作成する。', '构建准晶线框和非周期性彭罗斯图案。'),
    'geometry_frame': ('Use double-precision 2D/3D coordinate frames in the experimental geometry library.', 'Utiliser des repères 2D/3D en double précision dans la bibliothèque géométrique expérimentale.', '2D/3D-Koordinatenrahmen mit doppelter Genauigkeit in der experimentellen Geometriebibliothek verwenden.', '実験的な幾何ライブラリで倍精度の2D/3D座標フレームを使用する。', '在实验性几何库中使用双精度2D/3D坐标框架。'),
}
SYSTEM = 'Choose exactly one documented operation. Return only JSON with one key operation and its identifier. No code, parameters, solver result or engineering approval. Cards: '+json.dumps(OPERATIONS)


def parse_action(text, finish):
    value = json.loads(text, object_pairs_hook=pilot.unique)
    if finish != 'stop' or not isinstance(value, dict) or set(value) != {'operation'} or type(value['operation']) is not str or value['operation'] not in OPERATIONS:
        raise ValueError('Unsupported or incomplete library operation')
    return value['operation']


def prepare(work):
    if work.exists(): raise ValueError('Use a new library-course directory')
    inventory = pilot.load(SUITE/'setup/installation.json')
    selected = {name: expected for name,expected in inventory['sha256'].items() if
                (name.startswith('libraries/') and '/bin/' not in name and '/obj/' not in name) or name.startswith('runtime/') or name in ('Workbench/Program.cs', 'Workbench/Workbench.csproj', 'Workbench/global.json')}
    for name, expected in selected.items():
        if pilot.digest(SUITE/name) != expected: raise ValueError('Installed library input changed: '+name)
    for name,expected in inventory['sha256'].items():
        if name.startswith('sdk/') and pilot.digest(SUITE/name)!=expected:raise ValueError('Installed SDK input changed: '+name)
    records = {row['repository']: row for row in inventory['libraries']}
    work.mkdir()
    for folder in ('Workbench', 'libraries', 'runtime'):
        if sys.platform == 'darwin': subprocess.run(['cp', '-cR', str(SUITE/folder), str(work/folder)], check=True)
        else: shutil.copytree(SUITE/folder, work/folder)
    (work/'global.json').write_text('{"sdk":{"version":"10.0.402","rollForward":"disable"}}\n')
    course = []
    for split, prefix in [('train', 'Select an API for this requirement: '), ('valid', 'Which documented operation addresses this request? '), ('test', 'Resolve this library capability request: ')]:
        for operation in OPERATIONS:
            for i,language in enumerate(contract.LANGUAGES):
                prompt = prefix+QUESTIONS[operation][i]
                course.append(dict(id=split+'-'+hashlib.sha256(prompt.encode()).hexdigest()[:16], split=split, language=language,
                                   expected=operation, messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt},
                                   {'role':'assistant','content':json.dumps({'operation':operation})}]))
    pilot.save(work/'cases.json', course)
    pilot.save(work/'registry.json', dict(operations={key:dict(repository=value[0], revision=records[value[0]]['revision'], license=records[value[0]]['license'], card=value[1]) for key,value in OPERATIONS.items()},
               installed_source_sha256=selected, scope='Operation selection only. Shared operations/questions with different split wrappers; not unseen geometry or full API mastery.'))
    source = Path(__file__).resolve().parents[2]
    for folder in ('qwen-picogk-qualified-20261014','qwen-picogk-robustness-20261013','qwen-picogk-20261012','qwen-research-corpus','qwen-porsche-corpus','qwen-engineering-20261002','m64-qwen','m64-engineer'):
        for path in (source/'training'/folder).rglob('*'):
            if path.is_file() and path.suffix in ('.py','.json','.cs','.lock'):
                destination=work/'source'/path.relative_to(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
    files = [p for p in work.rglob('*') if p.is_file() and '/bin/' not in str(p) and '/obj/' not in str(p)]
    files += [SUITE/name for name in inventory['sha256'] if name.startswith('sdk/')]
    pilot.save(work/'FROZEN.json', dict(files={str(p):pilot.digest(p) for p in files}))
    print('Prepared four separate source-pinned library cards; 20 train, 20 development, 20 reserved selector requests', flush=True)


def run(work, profile_path, trusted_hash):
    if pilot.digest(profile_path)!=trusted_hash:raise ValueError('Untrusted core profile')
    config = pilot.load(profile_path)
    core = Path(config['work_root'])
    spec = importlib.util.spec_from_file_location('qualified_core_loader', Path(__file__).with_name('ask.py'))
    loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
    _, base, adapter = loader.profile(profile_path, trusted_hash)
    lock = (loader.qualify.RUNTIME/'train.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    loader.qualify.verify(work)
    out=work/'run-001';out.mkdir()
    dotnet=SUITE/'sdk/dotnet'
    env=os.environ.copy();env['DYLD_LIBRARY_PATH']=str(work/'runtime')
    with (out/'native.log').open('w') as log:
        subprocess.run([str(dotnet),'build',str(work/'Workbench/Workbench.csproj'),'-c','Release','--configfile',str(work/'Workbench/NuGet.Config'),'-o',str(work/'Workbench/bin'),'--nologo','-v','q'],cwd=work/'Workbench',stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        witnesses={}
        for action in ('check','simulation'):
            response=subprocess.run([str(dotnet),str(work/'Workbench/bin/Workbench.dll'),action],env=env,capture_output=True,text=True,check=True,timeout=120)
            log.write(response.stdout+response.stderr)
            witnesses[action]=json.loads(next(line for line in reversed(response.stdout.splitlines()) if line.startswith('{')))
            if not witnesses[action]['passed']:raise ValueError('Native library reference failed')
        geometry=subprocess.run([str(dotnet),'test',str(work/'libraries/PicoGK.Geometry/PicoGK.Geometry.slnx'),'--no-restore','-c','Release','--nologo'],cwd=work,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        if geometry.returncode:raise ValueError('Isolated Geometry reference tests failed; see log')
    pilot.save(out/'native-witnesses.json',witnesses)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1',HF_HUB_DISABLE_TELEMETRY='1')
    import mlx.core as mx
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    mx.set_memory_limit(8*1024**3);mx.set_cache_limit(256*1024**2);mx.random.seed(9931312)
    model,tokenizer=load(str(base),adapter_path=str(adapter),tokenizer_config={'trust_remote_code':False});tokenizer.add_eos_token('<|im_end|>')
    rows=pilot.load(work/'cases.json');scores=[]
    for split in ('valid','test'):
        if split=='test' and not all(r['passed'] for r in scores):break
        for row in rows:
            if row['split']!=split:continue
            prompt=tokenizer.apply_chat_template(row['messages'][:2],tokenize=False,add_generation_prompt=True)
            if len(tokenizer.encode(prompt))>1024:raise ValueError('Library prompt exceeds context')
            text,last='',None
            for last in stream_generate(model,tokenizer,prompt=prompt,max_tokens=192,sampler=make_sampler(temp=0)):text+=last.text
            try: passed=parse_action(text,last.finish_reason if last else None)==row['expected']
            except (ValueError,TypeError):passed=False
            scores.append(dict(id=row['id'],split=split,passed=passed,response=text));pilot.save(out/'scores.json',scores)
            print('Library selector',len(scores),'/',40,flush=True)
    loader.qualify.verify(work)
    report=dict(development_passed=sum(r['passed'] for r in scores if r['split']=='valid'),development_total=20,
                test_opened=any(r['split']=='test' for r in scores),test_passed=sum(r['passed'] for r in scores if r['split']=='test'),
                weights_updated=False,full_api_mastery_tested=False,model_code_executed=False,manufacturing_qualified=False)
    pilot.save(out/'results.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--profile',type=Path);parser.add_argument('--profile-sha256');args=parser.parse_args()
    if args.action=='prepare':prepare(args.work.absolute())
    else:
        if not args.profile or not args.profile_sha256:parser.error('Use a trusted qualified core profile')
        run(args.work.absolute(),args.profile,args.profile_sha256)
