#!/usr/bin/env python3
"""Small OpenUSD authoring corpus and bounded API interpreter; no arbitrary Python execution."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re

VERSION = (0,25,5)
SYSTEM = ('Write only Python code using Pixar OpenUSD 25.5. stage is an empty in-memory Usd.Stage; '
          'UsdGeom, UsdShade, Sdf and Gf are available. Use literal values, assignments and API calls; '
          'variant edit-context with blocks are allowed. No loops, functions, files, external assets or shell commands. '
          'Set /World as default prim, Z up and metersPerUnit=0.001. All geometry is synthetic, not measured Porsche data.')


def candidates(expanded=False, composition=False):
    if composition:expanded=True
    source={'id':'openusd-authored-examples','uri':'repo:training/m64-engineer/openusd.py',
            'revision_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'license':'Repository proprietary; owner-authorized local training','training_allowed':True}
    rows=[]
    counts=[('train',288),('valid',24),('test',24)] if expanded else [('train',48),('valid',6),('test',12)]
    if composition:counts=[('train',288),('test',24)]
    for split,count in counts:
        for i in range(count):
            n=i+{'train':0,'valid':100,'test':200}[split]
            kind=i%6; size=4+n%13; shift=n%9-4; label=f'Part{n}'
            if expanded:
                n=i+{'train':1000,'valid':10000,'test':20000}[split]
                if composition:n=i+{'train':30000,'test':90000}[split]
                size=3+(n*7)%29;shift=n%17-8
                label=['Core','Mount','Element','Part'][i%4]+str(n)
            path='/World/'+label
            header='root = UsdGeom.Xform.Define(stage, "/World")\nstage.SetDefaultPrim(root.GetPrim())\nUsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)\nUsdGeom.SetStageMetersPerUnit(stage, 0.001)\n'
            cube=f'part = UsdGeom.Cube.Define(stage, "{path}")\npart.CreateSizeAttr({size})\n'
            translate=f'part.AddTranslateOp().Set(Gf.Vec3d({shift}, 0, 0))\n'
            tasks=[
                (f'Create cube {path} of size {size} mm, translated by ({shift},0,0) mm.',cube+translate),
                (f'Create a triangular mesh at {path} with points (0,0,0), ({size},0,0), (0,{size},0); one face [0,1,2], subdivision none.',
                 f'part = UsdGeom.Mesh.Define(stage, "{path}")\npart.CreatePointsAttr([Gf.Vec3f(0,0,0), Gf.Vec3f({size},0,0), Gf.Vec3f(0,{size},0)])\npart.CreateFaceVertexCountsAttr([3])\npart.CreateFaceVertexIndicesAttr([0,1,2])\npart.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)\n'),
                (f'Create cube {path} of size {size} mm. Bind material /World/Material with shader /World/Material/Surface, UsdPreviewSurface, diffuseColor (0.2,0.4,0.6), roughness 0.4.',
                 cube+'material = UsdShade.Material.Define(stage, "/World/Material")\nshader = UsdShade.Shader.Define(stage, "/World/Material/Surface")\nshader.CreateIdAttr("UsdPreviewSurface")\nshader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.2,0.4,0.6))\nshader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)\nmaterial.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")\nUsdShade.MaterialBindingAPI.Apply(part.GetPrim()).Bind(material)\n'),
                (f'Create cube {path} of size {size} mm. Create {path}Copy as an internal reference to {path}, marked instanceable. Do not duplicate its size opinion.',
                 cube+f'copy = stage.DefinePrim("{path}Copy")\ncopy.GetReferences().AddInternalReference("{path}")\ncopy.SetInstanceable(True)\n'),
                (f'Create cube {path}. Author variant set detail with variants small and large, size {size} and {size*2} mm respectively, entirely inside variant contexts. Select large.',
                 f'part = UsdGeom.Cube.Define(stage, "{path}")\nvariants = part.GetPrim().GetVariantSets().AddVariantSet("detail")\nvariants.AddVariant("small")\nvariants.SetVariantSelection("small")\nwith variants.GetVariantEditContext():\n    part.CreateSizeAttr({size})\nvariants.AddVariant("large")\nvariants.SetVariantSelection("large")\nwith variants.GetVariantEditContext():\n    part.CreateSizeAttr({size*2})\n'),
                (f'Create cube {path}, size {size} mm. Animate translate from (0,0,0) at time code 1 to ({size},0,0) at time code 24; start/end 1/24 and timeCodesPerSecond=24. No default translate value.',
                 cube+f'stage.SetStartTimeCode(1)\nstage.SetEndTimeCode(24)\nstage.SetTimeCodesPerSecond(24)\nmove = part.AddTranslateOp()\nmove.Set(Gf.Vec3d(0,0,0), 1)\nmove.Set(Gf.Vec3d({size},0,0), 24)\n')]
            prompt,code=tasks[kind]
            group='parameter_holdout'
            if not expanded and split=='test' and i>=6:
                group='composition_holdout'
                prompt+=' Also create sphere /World/Probe of radius 2 mm and purpose guide.'
                code+='probe = UsdGeom.Sphere.Define(stage, "/World/Probe")\nprobe.CreateRadiusAttr(2)\nprobe.CreatePurposeAttr(UsdGeom.Tokens.guide)\n'
            # Sphere APIs are taught in an independent form, not only seen in held-out compositions.
            if not expanded and split=='train' and i%12==0:
                prompt=f'Create sphere {path}, radius {size} mm, purpose guide, translated ({shift},0,0) mm.'
                code=f'part = UsdGeom.Sphere.Define(stage, "{path}")\npart.CreateRadiusAttr({size})\npart.CreatePurposeAttr(UsdGeom.Tokens.guide)\n'+translate
            if expanded:
                if kind==4 and (i//6)%2:
                    prompt=prompt.replace('Select large.','Select small.')
                    code+='variants.SetVariantSelection("small")\n'
                # ponytail: shared API recipes, not a family-independent benchmark.
                # The third curriculum teaches triples without changing old validation cases.
                additions=[]
                if composition:additions=['sphere','cube']
                elif split=='train':
                    if (i//6)%3:additions=['sphere' if (i//6)%3==1 else 'cube']
                elif i>=12:additions=['sphere','cube']
                for shape in additions:
                    extra='/World/'+('Probe' if n%2 else 'Marker'+str(n)) if shape=='sphere' else '/World/Block'+str(n)
                    value=2+n%4
                    if shape=='sphere':
                        prompt+=f' Also create sphere {extra} of radius {value} mm and purpose guide.'
                        code+=f'probe = UsdGeom.Sphere.Define(stage, "{extra}")\nprobe.CreateRadiusAttr({value})\nprobe.CreatePurposeAttr(UsdGeom.Tokens.guide)\n'
                    else:
                        prompt+=f' Also create cube {extra} of size {value} mm, purpose guide, translated (0,{shift},0) mm.'
                        code+=f'block = UsdGeom.Cube.Define(stage, "{extra}")\nblock.CreateSizeAttr({value})\nblock.CreatePurposeAttr(UsdGeom.Tokens.guide)\nblock.AddTranslateOp().Set(Gf.Vec3d(0,{shift},0))\n'
                group='composition_holdout' if additions else 'parameter_holdout'
            prefix='usd2' if expanded else 'usd'
            if composition:prefix='usd3'
            rows.append({'id':f'{prefix}-{split}-{i:03d}','family_id':f'usd-recipe-{kind}',
                'domain':'openusd','split':split,'group':group,'recipe':kind,
                'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt},
                            {'role':'assistant','content':header+code}],
                'sources':[source],'synthetic':True,'validation':{'status':'pending','method':'not yet executed'}})
    return rows


# Exact API allowlist. No file access, imports beyond pxr names, arbitrary getattr,
# Python eval/exec, external references, functions, loops or comprehension syntax.
ALLOWED = set('''Xform Cube Sphere Mesh Xformable Material Shader MaterialBindingAPI
Tokens z y none guide default_ ValueTypeNames Color3f Float Vec3f Vec3d Define Apply
SetStageUpAxis SetStageMetersPerUnit SetDefaultPrim DefinePrim GetPrim GetPrimAtPath
CreateSizeAttr CreateRadiusAttr AddTranslateOp AddScaleOp Set CreatePointsAttr
CreateFaceVertexCountsAttr CreateFaceVertexIndicesAttr CreateSubdivisionSchemeAttr
CreatePurposeAttr CreateIdAttr CreateInput CreateSurfaceOutput ConnectToSource
ConnectableAPI Bind GetReferences AddInternalReference SetInstanceable GetVariantSets
AddVariantSet AddVariant SetVariantSelection GetVariantEditContext SetStartTimeCode
SetEndTimeCode SetTimeCodesPerSecond'''.split())


def author(code):
    from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
    if Usd.GetVersion()!=VERSION: raise RuntimeError('pin usd-core==25.5.1')
    code=re.sub(r'^```(?:python)?\s*([\s\S]*?)\s*```$',r'\1',code.strip())
    if len(code)>12000: raise ValueError('source exceeds witness limit')
    tree=ast.parse(code)
    if len(list(ast.walk(tree)))>2000: raise ValueError('source exceeds witness limit')
    stage=Usd.Stage.CreateInMemory()
    env={'stage':stage,'UsdGeom':UsdGeom,'UsdShade':UsdShade,'Sdf':Sdf,'Gf':Gf}
    def value(node):
        if isinstance(node,ast.Constant):
            v=node.value
            if type(v) not in (str,int,float,bool) or (isinstance(v,str) and len(v)>160) or (type(v) in (int,float) and not -1e6<=v<=1e6):
                raise ValueError('literal outside bounds')
            return v
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):
            n=value(node.operand)
            if type(n) not in (int,float): raise ValueError('unary minus requires number')
            return -n
        if isinstance(node,(ast.List,ast.Tuple)):
            if len(node.elts)>64: raise ValueError('array too large')
            return [value(x) for x in node.elts]
        if isinstance(node,ast.Name) and node.id in env: return env[node.id]
        if isinstance(node,ast.Attribute) and node.attr in ALLOWED: return getattr(value(node.value),node.attr)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ALLOWED:
            if node.keywords: raise ValueError('keyword calls outside witness contract')
            return value(node.func)(*[value(x) for x in node.args])
        raise ValueError('unsupported Python outside bounded USD authoring contract')
    def statements(body):
        for node in body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
                name=node.targets[0].id
                if name.startswith('_') or name in ('stage','UsdGeom','UsdShade','Sdf','Gf'): raise ValueError('reserved name')
                env[name]=value(node.value)
            elif isinstance(node,ast.Expr): value(node.value)
            elif isinstance(node,ast.With) and len(node.items)==1 and node.items[0].optional_vars is None:
                expr=node.items[0].context_expr
                if not isinstance(expr,ast.Call) or not isinstance(expr.func,ast.Attribute) or expr.func.attr!='GetVariantEditContext':
                    raise ValueError('only USD variant contexts allowed')
                with value(expr): statements(node.body)
            elif isinstance(node,ast.ImportFrom) and node.module=='pxr' and node.level==0:
                if any(x.name not in ('UsdGeom','UsdShade','Sdf','Gf') or x.asname for x in node.names): raise ValueError('unsupported import')
            else: raise ValueError('unsupported statement')
    statements(tree.body)
    return stage


def snapshot(stage):
    from pxr import UsdGeom
    def normalize(v):
        if v is None or isinstance(v,(str,bool,int)):return v
        if isinstance(v,float):return round(v,6)
        try:return [normalize(x) for x in v]
        except TypeError:return str(v)
    def attrs(prim):
        result={}
        for a in prim.GetAttributes():
            if not a.HasAuthoredValueOpinion() and not a.GetConnections():continue
            result[a.GetName()]={'type':str(a.GetTypeName()),'value':normalize(a.Get()),'samples':{str(t):normalize(a.Get(t)) for t in a.GetTimeSamples()},
                                  'connections':[str(x) for x in a.GetConnections()]}
        return result
    prims={}
    for prim in list(stage.Traverse()):
        data={'type':prim.GetTypeName(),'schemas':prim.GetAppliedSchemas(),'attributes':attrs(prim),'instanceable':prim.IsInstanceable(),
              'relationships':{r.GetName():[str(t) for t in r.GetTargets()] for r in prim.GetRelationships() if r.GetTargets()}}
        references=prim.GetMetadata('references')
        if references:data['references']=[{'asset':r.assetPath,'prim':str(r.primPath)} for r in references.GetAddedOrExplicitItems()]
        data['variants']={}
        for name in prim.GetVariantSets().GetNames():
            vs=prim.GetVariantSet(name); selected=vs.GetVariantSelection(); choices={}
            for choice in vs.GetVariantNames():
                vs.SetVariantSelection(choice);choices[choice]=attrs(prim)
            vs.SetVariantSelection(selected)
            data['variants'][name]={'selected':selected,'choices':choices}
        prims[str(prim.GetPath())]=data
    return {'metersPerUnit':UsdGeom.GetStageMetersPerUnit(stage),'upAxis':str(UsdGeom.GetStageUpAxis(stage)),
            'authored_units':stage.HasAuthoredMetadata('metersPerUnit'),'authored_axis':stage.HasAuthoredMetadata('upAxis'),
            'defaultPrim':str(stage.GetDefaultPrim().GetPath()),'start':stage.GetStartTimeCode(),'end':stage.GetEndTimeCode(),
            'timeCodesPerSecond':stage.GetTimeCodesPerSecond(),'prims':prims}


def validate(stage,folder):
    from pxr import Usd,UsdUtils,UsdGeom
    if stage.GetCompositionErrors(): raise ValueError('composition errors')
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            mesh=UsdGeom.Mesh(prim)
            valid,reason=UsdGeom.Mesh.ValidateTopology(mesh.GetFaceVertexIndicesAttr().Get(),mesh.GetFaceVertexCountsAttr().Get(),len(mesh.GetPointsAttr().Get()))
            if not valid: raise ValueError(reason)
    folder.mkdir(parents=True,exist_ok=False)
    for ext in ('usda','usdc'):
        path=folder/('scene.'+ext)
        stage.GetRootLayer().Export(str(path))
        reopened=Usd.Stage.Open(str(path))
        if not reopened or snapshot(reopened)!=snapshot(stage): raise ValueError('USD roundtrip differs')
    checker=UsdUtils.ComplianceChecker()
    # ponytail: usd-core omits the shader discovery resources. Keep other rules;
    # use a full Pixar build to add shader-registry conformance and rendering.
    skipped='ShaderPropertyTypeConformanceChecker'
    checker._rules=[r for r in checker._rules if type(r).__name__!=skipped]
    checker.CheckCompliance(str(folder/'scene.usdc'))
    if checker.GetErrors() or checker.GetFailedChecks():raise ValueError(str(checker.GetErrors()+checker.GetFailedChecks()))
    return {'usd_version':list(Usd.GetVersion()),'skipped_checks':[skipped],
            'warnings':[str(x) for x in checker.GetWarnings()],
            'usda_sha256':hashlib.sha256((folder/'scene.usda').read_bytes()).hexdigest(),
            'usdc_sha256':hashlib.sha256((folder/'scene.usdc').read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['generate','verify','prepare-pilot','score','infer'])
    p.add_argument('--input',type=Path);p.add_argument('--responses',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',type=Path);p.add_argument('--adapter',type=Path)
    p.add_argument('--replay',type=Path,help='Frozen cases.json from the previous PicoGK run')
    p.add_argument('--expanded',action='store_true',help='Generate the second curriculum; preserve the original corpus by default')
    p.add_argument('--composition',action='store_true',help='Generate 288 three-object training scenes and 24 fresh tests; no validation changes')
    p.add_argument('--split',choices=['valid','test'],default='test',help='Partition to infer/score; never selects training rows')
    a=p.parse_args()
    if a.output.exists():raise ValueError('output already exists')
    if a.action=='generate':
        rows=candidates(expanded=a.expanded,composition=a.composition)
        a.output.write_text(''.join(json.dumps(r)+'\n' for r in rows));return
    rows=[json.loads(x) for x in a.input.read_text().splitlines() if x.strip()]
    if a.action=='prepare-pilot':
        from dataset import check
        check(rows)
        replay=json.loads(a.replay.read_text())
        replay_hash=hashlib.sha256(a.replay.read_bytes()).hexdigest()
        previous=json.loads((a.replay.parent/'manifest.json').read_text())
        if previous['dataset_sha256']!=replay_hash:raise ValueError('replay hash mismatch')
        if {r['split'] for r in rows+replay}!={'train','valid','test'}:raise ValueError('invalid splits')
        a.output.mkdir(parents=True);data=a.output/'data';data.mkdir()
        counts={}
        for split in ('train','valid','test'):
            part=[r for r in rows+replay if r['split']==split]
            (data/(split+'.jsonl')).write_text(''.join(json.dumps({'messages':r['messages']})+'\n' for r in part))
            counts[split]={'openusd':sum(r['split']==split for r in rows),'picogk':sum(r['split']==split for r in replay)}
        (a.output/'usd-cases.jsonl').write_text(a.input.read_text())
        (a.output/'picogk-cases.json').write_text(a.replay.read_text())
        (a.output/'manifest.json').write_text(json.dumps({'counts':counts,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'usd_cases_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
            'picogk_cases_sha256':replay_hash,
            'data_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(data.glob('*.jsonl'))},
            'limitations':'Shared template families; parameter and small composition holdouts only. Existing PicoGK test is a regression suite, not a fresh benchmark.'},indent=2)+'\n')
        return
    if a.action=='infer':
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
        from mlx_lm import load,stream_generate
        from mlx_lm.sample_utils import make_sampler
        model,tok=load(str(a.model),adapter_path=str(a.adapter) if a.adapter else None,tokenizer_config={'trust_remote_code':False})
        tok.add_eos_token('<|im_end|>')
        with a.output.open('x') as f:
            for r in rows:
                if r['split']!=a.split:continue
                prompt=tok.apply_chat_template(r['messages'][:-1],tokenize=False,add_generation_prompt=True)
                text=''.join(x.text for x in stream_generate(model,tok,prompt=prompt,max_tokens=1024,sampler=make_sampler(temp=0)))
                f.write(json.dumps({'id':r['id'],'response':text})+'\n');f.flush()
        return
    # A missing/wrong runtime is an infrastructure failure, never a model score.
    # Tiny witnesses run serially to avoid the observed TBB stage-cleanup hang.
    os.environ.setdefault('PXR_WORK_THREAD_LIMIT','1')
    from pxr import Usd
    if Usd.GetVersion()!=VERSION:raise RuntimeError('pin usd-core==25.5.1')
    evidence=a.output.with_suffix('.evidence');evidence.mkdir(exist_ok=False)
    responses={r['id']:r['response'] for r in [json.loads(x) for x in a.responses.read_text().splitlines()]} if a.action=='score' else None
    with a.output.open('x') as f:
        for r in rows:
            if responses is not None and r['split']!=a.split:continue
            if not re.fullmatch(r'[A-Za-z0-9_-]+',r['id']):raise ValueError('invalid id')
            reference=r['messages'][-1]['content']
            text=responses[r['id']] if responses is not None else reference
            report={'id':r['id'],'group':r['group'],'passed':False,'response':text}
            try:
                stage=author(text)
                report['native']=validate(stage,evidence/r['id'])
                report['passed']=snapshot(stage)==snapshot(author(reference))
                if not report['passed']:report['error']='USD stage differs from requested authoring contract'
            except Exception as error:
                if responses is None:raise
                report['error']=type(error).__name__+': '+str(error)
            if responses is None:
                checksum=hashlib.sha256(reference.encode()).hexdigest()
                report['answer_sha256']=checksum
                receipt=evidence/(r['id']+'.json');receipt.write_text(json.dumps(report,indent=2)+'\n')
                r['validation']={'status':'verified','method':'OpenUSD API, topology, composition, USDA/USDC roundtrip and compliance rules except shader registry',
                    'answer_sha256':checksum,'evidence':[{'path':str(receipt),'sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}]}
                f.write(json.dumps(r)+'\n')
            else:f.write(json.dumps(report)+'\n')
            f.flush()

if __name__=='__main__':main()
