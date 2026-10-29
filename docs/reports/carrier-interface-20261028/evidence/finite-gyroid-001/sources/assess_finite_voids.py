"""Compare finite void volumes; this does not establish mechanical convergence."""
import argparse,hashlib,json
from pathlib import Path


def compare(levels, parameters):
    assert len(levels)==3
    levels=sorted(levels,key=lambda r:-r['size_mm'])
    assert [r['size_mm']for r in levels]==parameters['finite_sizes_mm']
    assert len({r['rank']for r in levels})==1
    assert len({r['core_volume_mm3']for r in levels})==1
    assert len({r['source_sha256']for r in levels})==1
    changes=[]
    for before,after in zip(levels,levels[1:]):
        changes.append(abs(after['void_volume_mm3']-before['void_volume_mm3'])/after['void_volume_mm3'])
    limit=parameters['maximum_relative_volume_change']
    assert 0<limit<=.02 and parameters['required_successive_volume_comparisons']==2
    return dict(rank=levels[0]['rank'],levels=levels,relative_volume_changes=changes,
                volume_stabilized=all(x<=limit for x in changes))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--directories',type=Path,nargs='+',required=True);p.add_argument('--networks',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert len(a.directories)==12 and len(set(a.directories))==12 and len(a.networks)==12 and len(set(a.networks))==12 and not a.output.exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    groups={i:[]for i in range(4)};parameters=None;inputs={}
    for directory in a.directories:
        report=directory/'assessment.json';r=json.loads(report.read_text());contract=json.loads((directory/'contract.json').read_text())
        assert r['status']=='finite_sharp_clipped_gyroid_void_baseline_passed'
        assert not any(r[k]for k in ['carrier_geometry_changed','smooth_transition_generated','powder_escape_demonstrated','manufacturing_authorized'])
        assert r['exact_oriented_triangle_roundtrip'] and r['relative_export_volume_error']<=1e-10
        assert r['maximum_abs_phase_residual']<=1e-4 and r['rank']==contract['rank'] and r['size_mm']==contract['size_mm']
        assert sha(directory/'void-tool.npz')==r['output_sha256']
        assert json.loads((directory/'containment-observation.json').read_text())['outside_is_empty']
        assert all(c['passed']for c in json.loads((directory/'analytic-controls.json').read_text())[1:])
        if parameters is None:parameters=contract['parameters']
        assert contract['parameters']==parameters
        assert r['pitch_mm']==parameters['finite_pitch_mm']
        groups[r['rank']].append(r);inputs[str(report)]=sha(report)
    regions=[compare(groups[i],parameters)for i in range(4)]
    cleaned={i:[]for i in range(4)};seen=set()
    for directory in a.networks:
        path=directory/'assessment.json';n=json.loads(path.read_text());key=(n['rank'],n['size_mm']);assert key not in seen;seen.add(key)
        assert n['status']=='dominant_void_network_per_analytic_sign_retained' and len(n['selected'])==2
        assert sorted(c['branch']for c in n['selected'])==[-1,1]
        assert not n['carrier_geometry_changed'] and not n['powder_escape_demonstrated'] and not n['manufacturing_authorized']
        raw=next(r for r in groups[n['rank']]if r['size_mm']==n['size_mm'])
        assert abs(n['raw_void_volume_mm3']-raw['void_volume_mm3'])/raw['void_volume_mm3']<=1e-10
        for selected in n['selected']:assert selected['exact_oriented_triangle_roundtrip'] and sha(directory/selected['file'])==selected['sha256']
        assert n['filled_pocket_volume_mm3']>=0 and n['retained_void_volume_mm3']<=n['raw_void_volume_mm3']
        code=[v for k,v in n['source_sha256'].items()if Path(k).name=='finite_gyroid_networks.py'];assert len(code)==1
        cleaned[n['rank']].append(dict(raw,void_volume_mm3=n['retained_void_volume_mm3'],source_sha256=code[0]))
        inputs[str(path)]=sha(path)
    cleaned_regions=[compare(cleaned[i],parameters)for i in range(4)]
    retained_volume=sum(r['levels'][-1]['void_volume_mm3']for r in cleaned_regions)
    out=dict(status='finite_void_volume_series_assessed',regions=regions,
             finite_volume_stabilized=all(r['volume_stabilized']for r in regions),
             cleaned_regions=cleaned_regions,cleaned_volume_stabilized=all(r['volume_stabilized']for r in cleaned_regions),
             finest_retained_void_volume_mm3=retained_volume,titanium_void_volume_equivalent_mass_g=retained_volume*.00442,
             finite_topology_converged=False,complete_carrier_mechanics_converged=False,
             carrier_geometry_changed=False,powder_escape_demonstrated=False,manufacturing_authorized=False,
             source_sha256={str(Path(__file__)):sha(Path(__file__))},input_sha256=inputs)
    a.output.mkdir();(a.output/'assessment.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(finite_volume_stabilized=out['finite_volume_stabilized'],cleaned_volume_stabilized=out['cleaned_volume_stabilized'],titanium_void_volume_equivalent_mass_g=out['titanium_void_volume_equivalent_mass_g'],regions=[{k:r[k]for k in ['rank','relative_volume_changes','volume_stabilized']}for r in regions])))


if __name__=='__main__':main()
