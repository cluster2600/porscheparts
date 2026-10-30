"""Independent field, equilibrium and analytical-control checks for study decks."""
import argparse
import json
from pathlib import Path
import numpy as np

def read_frd(path, n):
    fields = {}
    name = None
    values = None
    seen = None
    with path.open() as stream:
        for line in stream:
            if line.startswith(' -4'):
                name = line.split()[1]
                values = None
                seen = np.zeros(n, bool)
            elif name is not None and line.startswith(' -1'):
                idx = int(line[3:13])-1
                assert 0 <= idx < n and not seen[idx]
                raw = line[13:].rstrip('\n')
                row = [float(raw[i:i+12]) for i in range(0,len(raw),12) if raw[i:i+12].strip()]
                if values is None: values = np.full((n,len(row)),np.nan)
                values[idx] = row
                seen[idx] = True
            elif name is not None and line.startswith(' -3'):
                assert seen.all() and np.isfinite(values).all(), name
                fields[name] = values
                name = None
    return fields

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mesh',type=Path)
    p.add_argument('case',type=Path)
    p.add_argument('--cube',action='store_true')
    a = p.parse_args()
    x=np.load(a.mesh)['nodes']
    bc=np.load(a.case/'boundary-assignments.npz')
    meta=json.loads((a.case/'assumptions.json').read_text())
    result={'scope':'numerical results for declared hypotheses; no manufacturing or engine qualification'}
    for stem in ['pressure','pressure-direct','thermal','thermal-direct','thermomechanical']:
        path=a.case/(stem+'.frd')
        if not path.exists():continue
        fields=read_frd(path,len(x))
        np.savez_compressed(a.case/(stem+'-fields.npz'),**fields)
        out={'fields':list(fields),'nodes':len(x)}
        if 'DISP' in fields:
            u=fields['DISP']
            out['displacement_mm_quantiles']=np.quantile(np.linalg.norm(u,axis=1),[0,.5,.95,.99,1]).tolist()
            rf=fields['FORC'] if 'FORC' in fields else fields['FORCE']
            reaction=rf[bc['fixed']].sum(axis=0)
            force=np.array(meta['pressure_force_N'])
            out['support_reaction_N']=reaction.tolist()
            out['force_balance_relative']=float(np.linalg.norm(reaction+force)/max(np.linalg.norm(force),1))
            s=fields['STRESS']
            vm=np.sqrt(.5*((s[:,0]-s[:,1])**2+(s[:,1]-s[:,2])**2+(s[:,2]-s[:,0])**2)+3*np.sum(s[:,3:6]**2,axis=1))
            out['nodal_von_mises_MPa_quantiles']=np.quantile(vm,[0,.5,.95,.99,1]).tolist()
            out['note']='Nodal extrapolated stresses; unconverged maxima at geometric and support discontinuities are not allowables.'
            if a.cube:
                expected=np.column_stack([.33*x[:,0]/70000,.33*x[:,1]/70000,-x[:,2]/70000])
                out['analytic_displacement_relative_max_error']=float(abs(u-expected).max()/(1/70000))
                out['analytic_von_mises_max_error_MPa']=float(abs(vm-1).max())
                if stem=='pressure-direct':
                    assert out['analytic_displacement_relative_max_error']<1e-5
                    assert out['force_balance_relative']<1e-5
        if 'NDTEMP' in fields:
            temp=fields['NDTEMP'][:,0]
            out['temperature_C_range']=[float(temp.min()),float(temp.max())]
            heat=fields['RFL'][:,0]
            qhot=float(heat[bc['hot']].sum())/1000
            qcold=float(heat[bc['cold']].sum())/1000
            out['prescribed_surface_heat_W']={'hot':qhot,'cold':qcold}
            out['heat_balance_relative']=abs(qhot+qcold)/max(abs(qhot),abs(qcold),1e-12)
            if a.cube:
                out['analytic_temperature_max_error_C']=float(abs(temp-100*x[:,0]).max())
                assert out['analytic_temperature_max_error_C']<.001
                assert abs(qhot-15)<.001
        result[stem]=out
    (a.case/'assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
