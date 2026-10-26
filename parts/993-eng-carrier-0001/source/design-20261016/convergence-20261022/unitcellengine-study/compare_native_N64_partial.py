"""Cross-check four completed native N64 fields without inventing the two missing cases."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--shared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();started=time.monotonic();N=64;phys=(N+1)**3
    report=json.loads((a.shared/'assessment.json').read_text());audit=json.loads((a.shared/'saved-field-audit.json').read_text());assert report['resolution']==64 and report['void_relative_stiffness']==1e-4 and report['status']=='independent_operator_energy_checks_passed'
    assert sha(a.shared/'fields.npz')==audit['file_sha256']['fields.npz']and sha(a.shared/'stress-all-ip.npy')==audit['file_sha256']['stress-all-ip.npy']
    f=np.load(a.shared/'fields.npz');s=np.load(a.shared/'stress-all-ip.npy',mmap_mode='r');perm=[0,1,2,3,5,4];ip=[0,4,2,6,1,5,3,7];k,j,i=np.indices((N+1,)*3);xyz=np.column_stack([i.ravel(),j.ravel(),k.ravel()])/N;rows=[];identities={}
    for mode in range(4):
        base=a.native/f'case-{mode}';receipt=json.loads((base/'actual-terminal.json').read_text());assert receipt['actual_returncode']==0 and receipt['process_reaped']and receipt['inputs_unchanged']and receipt['solver_finished_marker']
        dat=base/'case/job.dat';digest=sha(dat);assert digest==receipt['output_sha256']['job.dat'];identities[str(dat)]=digest
        H=np.zeros((3,3))
        if mode<3:H[mode,mode]=.001
        else:H[0,1]=H[1,0]=.0005
        U=xyz@H.T-.001*f['xi'][:,:,mode];F=.001*f['physical_forces'][:,:,mode];S=s[:,:,:,mode];counts={x:0 for x in ['displacements','forces','stresses']};errors={x:0. for x in counts};current=None
        with dat.open()as stream:
            for line in stream:
                stripped=line.strip()
                for key in counts:
                    if stripped.startswith(key+' ('):assert counts[key]==0;current=key
                v=stripped.split()
                if not current or len(v)!=(8 if current=='stresses'else 4)or not v[0].isdigit():continue
                q=counts[current]
                if current=='stresses':
                    element,point=divmod(q,8);assert int(v[0])==element+1 and int(v[1])==point+1;expected=.001*S[element,ip[point],perm];actual=np.array(list(map(float,v[2:])))
                else:
                    assert int(v[0])==q+1;actual=np.array(list(map(float,v[1:])))
                    if q<phys:expected=U[q]if current=='displacements'else F[q]
                    else:
                        assert q<phys+3
                        if current=='displacements':assert max(abs(actual-H[:,q-phys]))<=1e-8
                        counts[current]+=1;continue
                assert np.isfinite(actual).all();errors[current]=max(errors[current],float(np.max(abs(actual-expected))));counts[current]+=1
        assert counts==dict(displacements=phys+3,forces=phys+3,stresses=8*N**3)
        assert errors['displacements']<=1e-5 and errors['stresses']<=.01 and errors['forces']<=.01
        rows.append(dict(mode=mode,counts=counts,maximum_component_differences=errors))
    r=dict(status='four_complete_native_N64_field_crosschecks_passed',cases=rows,native_N64_tensor_complete=False,missing_native_strain_modes=[4,5],all_six_shared_strain_fields_exist=True,elapsed_seconds=time.monotonic()-started,native_DAT_sha256=identities,shared_audit_sha256=sha(a.shared/'saved-field-audit.json'),source_sha256=sha(Path(__file__)),criteria_changed=False);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
