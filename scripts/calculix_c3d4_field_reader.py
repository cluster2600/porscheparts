"""Batch native decimal fields while preserving strict row and section checks."""
from pathlib import Path
import warnings
import numpy as np

def parse_dat(path,output,nv,ne,fixed):
    shapes={'u':(nv,3),'rf':(len(fixed),3),'s':(ne,6),'ener':(ne,)}
    assert all(not (output/(k+'.npy')).exists() for k in shapes),'Fresh result fields required'
    arrays={k:np.lib.format.open_memmap(output/(k+'.npy'),mode='w+',dtype='<f8',shape=shape) for k,shape in shapes.items()}
    headers={'displacements (':'u','forces (':'rf','stresses (':'s','internal energy density (':'ener'}
    counts={k:0 for k in arrays};seen=set();mode=None;buffer=[]
    def flush():
        if not buffer:return
        start=counts[mode];n=len(buffer);assert start+n<=shapes[mode][0],('Extra rows',mode)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            values=np.fromstring(' '.join(buffer),dtype='<f8',sep=' ')
        columns=3 if mode=='ener' else 8 if mode=='s' else 4
        assert values.size==n*columns,'Incomplete or malformed numeric token'
        values=values.reshape(n,columns);assert np.isfinite(values).all(),'Nonfinite result'
        expected=fixed[start:start+n]+1 if mode=='rf' else np.arange(start+1,start+n+1,dtype=np.int64)
        assert np.array_equal(values[:,0],expected),('Missing, reordered or duplicate ID',mode,start)
        if mode in ('s','ener'):assert np.all(values[:,1]==1),'C3D4 integration-point roster differs'
        data=values[:,2:] if mode in ('s','ener') else values[:,1:]
        arrays[mode][start:start+n]=data[:,0] if mode=='ener' else data
        counts[mode]+=n;buffer.clear()
    with path.open() as stream:
        for line in stream:
            stripped=line.strip()
            if stripped and stripped[0].isdigit():
                assert mode is not None,'Numeric row outside expected section'
                tokens=stripped.split();columns=3 if mode=='ener' else 8 if mode=='s' else 4
                assert len(tokens)==columns and tokens[0].isascii() and tokens[0].isdigit(),'Malformed numeric row'
                if mode in ('s','ener'):assert tokens[1]=='1','C3D4 must have one integration point'
                buffer.append(' '.join(tokens))
                if len(buffer)>=32768:flush()
            else:
                matched=next((key for key in headers if stripped.startswith(key)),None)
                if matched:
                    flush();mode=headers[matched];assert mode not in seen,('Repeated section',mode);seen.add(mode)
        flush()
    assert all(counts[k]==shape[0] for k,shape in shapes.items()),('Incomplete fields',counts,shapes)
    assert {'u','s','ener'}<=seen and (not len(fixed) or 'rf' in seen)
    for a in arrays.values():a.flush()
    return arrays,counts

def main():
    """Parse complete contiguous C3D4 study fields into a fresh directory."""
    import argparse
    import hashlib
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dat', type=Path, required=True)
    parser.add_argument('--nodes', type=int, required=True)
    parser.add_argument('--elements', type=int, required=True)
    parser.add_argument('--groups', type=Path, required=True,
                        help='NPZ with the expected zero-based fixed-node roster')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.nodes <= 0 or args.elements <= 0 or args.output.exists():
        parser.error('Positive counts and a fresh output directory are required')
    with np.load(args.groups, allow_pickle=False) as groups:
        fixed = groups['fixed']
    if (fixed.ndim != 1 or fixed.dtype.kind not in 'iu'
            or np.any(fixed < 0) or np.any(fixed >= args.nodes)
            or np.any(fixed[1:] <= fixed[:-1])):
        parser.error('Expected fixed nodes must be unique, ordered integer indices')
    fixed = fixed.astype(np.int64, copy=False)

    def digest(path):
        result = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                result.update(block)
        return result.hexdigest()

    inputs = {str(path.resolve()): digest(path)
              for path in (args.dat, args.groups, Path(__file__))}
    args.output.mkdir(parents=True)
    arrays, counts = parse_dat(args.dat, args.output, args.nodes,
                               args.elements, fixed)
    assert inputs == {str(path.resolve()): digest(path)
                      for path in (args.dat, args.groups, Path(__file__))}, 'Inputs changed'
    report = {
        'status': 'complete_c3d4_field_rosters_parsed',
        'counts': counts,
        'input_sha256': inputs,
        'output_sha256': {name: digest(args.output / (name + '.npy'))
                          for name in arrays},
        'scope': 'Complete field intake; equilibrium, energy and mesh convergence are separate checks.',
    }
    (args.output / 'reader-report.json').write_text(
        json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': counts}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
