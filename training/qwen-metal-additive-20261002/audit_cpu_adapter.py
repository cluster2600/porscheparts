"""Check finite trained adapter tensors; this is not a scientific performance score."""
import argparse
import json
from pathlib import Path
import verify_grounded

def audit(path):
    import torch
    from safetensors import safe_open
    result={'tensors':0,'parameters':0,'all_finite':True,'lora_b_tensors':0,'nonzero_lora_b_tensors':0}
    with safe_open(path,framework='pt',device='cpu') as handle:
        for key in handle.keys():
            tensor=handle.get_tensor(key)
            result['tensors']+=1
            result['parameters']+=tensor.numel()
            result['all_finite'] &= bool(torch.isfinite(tensor).all())
            if 'lora_B' in key:
                result['lora_b_tensors']+=1
                result['nonzero_lora_b_tensors']+=int(bool(torch.count_nonzero(tensor)))
    result['sha256']=verify_grounded.sha(path)
    result['auditor_sha256']=verify_grounded.sha(Path(__file__).resolve())
    if not result['all_finite'] or not 0<result['nonzero_lora_b_tensors']==result['lora_b_tensors']:
        raise ValueError('Adapter contains nonfinite values or untrained zero B tensors')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh audit output path')
    result=audit(args.adapter.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
