#!/usr/bin/env python3
"""Verify published artifact integrity and cross-stage study identity contracts."""
import hashlib,json,math
from pathlib import Path


def verify(root):
    read=lambda p:json.loads((root/p).read_text())
    manifest=read('manifest.json');errors=[]
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.relative_to(root).parts[0]!='work'}
    if actual!=set(manifest['files']):errors.append('Manifest inventory differs from published study files')
    for name,entry in manifest['files'].items():
        p=root/name
        if not p.is_file() or p.stat().st_size!=entry['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:errors.append('Artifact integrity: '+name)
    r0=read('parameters/R0.json');v5=read('parameters/V5.json');v2=read('parameters/V2.json')
    keys=set(r0)-{'configuration_id'}
    if {k for k in keys if r0[k]!=v5[k]}!={'web_thickness_ratio'} or not math.isclose(v5['web_thickness_ratio']/r0['web_thickness_ratio'],1.3):errors.append('V5 changes other parameters')
    if {k for k in keys if r0[k]!=v2[k]}!={'root_pitch_deg'} or v2['root_pitch_deg']!=36 or r0['root_pitch_deg']!=42:errors.append('V2 changes other parameters')
    for label in ['R0','V5','V2']:
        g=read('results/geometry/'+label+'.json')
        if g['functional_interfaces_verified'] or g['physical_validation_established'] or g['manufacturing_authorized']:errors.append('Unsupported geometry qualification: '+label)
        if len(g['components'])!=8 or g['components']['rotor']['solids']!=1:errors.append('Wrong solid topology: '+label)
        if not all(c['brep_valid'] and c['volume_mm3']>0 and c['step_roundtrip_volume_relative_error']<1e-7 for c in g['components'].values()):errors.append('Invalid BRep/roundtrip: '+label)
        if hashlib.sha256((root/'source/build_analytical_system.py').read_bytes()).hexdigest()!=g['builder_sha256']:errors.append('Builder identity: '+label)
        if hashlib.sha256((root/(label+'-rotor.step')).read_bytes()).hexdigest()!=g['components']['rotor']['step_sha256']:errors.append('Rotor geometry identity: '+label)
    for label in ['R0','V5','V2']:
        g=read('results/geometry/'+label+'.json')
        for size in ['h3p6','h4p5']:
            r=read('results/mechanics/mesh-'+label+'-'+size+'.json');m=r['mesh']
            if m['minimum_Gauss4_jacobian']<=0 or m['relative_volume_error']>.02 or m['source_step_sha256']!=g['components']['rotor']['step_sha256']:errors.append('Mechanical mesh gate: '+label+size)
            if r['safe_rpm_range'] is not None or r.get('physical_validation_established',m['physical_validation_established']):errors.append('Unsupported mechanics qualification')
    cfd=read('results/cfd/mesh-and-protocol-records.json')
    if not cfd['cfd-R0-h7-local-symmetric/independent-mesh-gate.json']['accepted_for_bounded_pilot']:errors.append('Reference mesh gate rejected')
    f=read('results/cfd/reference-flow-600-summary-complete-fields.json')
    if not all(f['criteria_checks'].values()) or f['physical_validation_established'] or f['performance_improvement_proven']:errors.append('Reference flow gates/qualification')
    if f['file_sha256']['reference-protocol.json']!=hashlib.sha256((root/'parameters/reference-flow-continuation600-protocol.json').read_bytes()).hexdigest():errors.append('Frozen flow protocol identity')
    lpbf=read('results/lpbf/lpbf-screen.json')
    if lpbf['source_STL_sha256']!=read('results/geometry/R0.json')['components']['rotor']['stl_sha256'] or lpbf['slice_integrated_volume_relative_error']>.01 or lpbf['process_qualification_established']:errors.append('LPBF scope/volume/geometry')
    for label in ['R0','V5']:
        usd=read('omniverse/'+label+'.json')
        if usd['USD_sha256']!=hashlib.sha256((root/'omniverse'/(label+'.usda')).read_bytes()).hexdigest():errors.append('USD artifact identity')
    from verify_continuation import verify as verify_continuation
    verify_continuation(root)
    from verify_s1_diagnostic import verify as verify_s1
    verify_s1(root)
    if errors:raise ValueError('\n'.join(errors))
    print('Study integrity and cross-stage identity checks passed ('+str(len(manifest['files']))+' artifacts)')


if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
