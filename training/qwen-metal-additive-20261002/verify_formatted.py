"""Check v2 Qwen exports without model/tokenizer dependencies."""
import argparse
import hashlib
import json
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]

def verify(root, output):
    m = json.loads((output/'manifest.json').read_text())
    for relative, expected in m['input_hashes'].items():
        if sha(root/relative) != expected:
            raise ValueError('Changed input: '+relative)
    for relative, expected in m['output_hashes'].items():
        if sha(output/relative) != expected:
            raise ValueError('Changed output: '+relative)
    attribution = {r['source_id']:r for r in json.loads((output/'sources.json').read_text())}
    cpt = rows(output/'cpt-provenance.jsonl')
    sft = rows(output/'sft-provenance.jsonl')
    for row in cpt+sft:
        if {m['source_assignment'][s] for s in row['source_ids']} != {row['split']}:
            raise ValueError('Source partition leakage')
        if any(s not in attribution for s in row['source_ids']):
            raise ValueError('Attribution missing')
    for kind in ('cpt','sft','metadata'):
        for split in ('train','valid','test'):
            tokens = rows(output/(kind+'_tokens')/(split+'.jsonl'))
            text_kind = 'cpt_text' if kind == 'cpt' else kind+'_messages'
            raw = rows(output/text_kind/(split+'.jsonl'))
            expected = [r for r in cpt if r['split']==split] if kind=='cpt' else [r for r in sft if r['split']==split and r['dataset']==kind]
            if len(tokens) != len(raw) or len(tokens) != len(expected):
                raise ValueError('Trainer rows and provenance differ')
            for row, plain, reference in zip(tokens,raw,expected):
                ids, mask, labels = row['input_ids'], row['attention_mask'], row['labels']
                if not len(ids)==len(mask)==len(labels) or not ids or any(x!=1 for x in mask):
                    raise ValueError('Invalid unpadded token arrays')
                if len(ids) > m['cpt_limit' if kind=='cpt' else 'sft_limit']:
                    raise ValueError('Token limit exceeded')
                if kind=='cpt':
                    if labels != ids or ids[-1] != m['eos_token_id']:
                        raise ValueError('CPT labels or EOS incorrect')
                    if hashlib.sha256(plain['text'].encode()).hexdigest()!=reference['text_sha256']:
                        raise ValueError('CPT text and provenance differ')
                else:
                    start,end = reference['assistant_start'], reference['assistant_eos']
                    if not 0<start<=end<len(ids) or ids[end]!=m['eos_token_id']:
                        raise ValueError('Assistant span invalid')
                    if labels[:start] != [-100]*start or labels[start:end+1] != ids[start:end+1] or any(x!=-100 for x in labels[end+1:]):
                        raise ValueError('Prompt masking or assistant labels incorrect')
                    if hashlib.sha256(json.dumps(plain['messages'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()!=reference['messages_sha256']:
                        raise ValueError('SFT text and provenance differ')
    return {'status':'pass','counts':m['counts'],'maximum_tokens':m['maximum_tokens'],
            'scope':'Format, hashes, source partitions, EOS and loss masking; not scientific approval or model performance'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'formatted-v2')
    a=p.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parent,a.output.resolve()),indent=2))
