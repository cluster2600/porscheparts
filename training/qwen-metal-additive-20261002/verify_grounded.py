"""Verify provenance, holdouts and loss masks without ML dependencies."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(root, output):
    manifest = load(output/'manifest.json')
    for relative,expected in manifest['input_hashes'].items():
        if sha(root/relative)!=expected:
            raise ValueError('Changed input: '+relative)
    for relative,expected in manifest['output_hashes'].items():
        if sha(output/relative)!=expected:
            raise ValueError('Changed output: '+relative)
    assignment = manifest['source_assignment']
    passages = {p['passage_id']:p for p in rows(output/'passages.jsonl')}
    provenance = rows(output/'provenance.jsonl')
    case_split = {}
    for row in provenance:
        if assignment[row['source_id']]!=row['split']:
            raise ValueError('Source leakage')
        for passage_id in row.get('passage_ids',[row.get('passage_id')]):
            if passages[passage_id]['source_id']!=row['source_id']:
                raise ValueError('Evidence source mismatch')
        if row['dataset']=='sft':
            previous = case_split.setdefault(row['case_id'],row['split'])
            if previous!=row['split']:
                raise ValueError('Translation/task family leakage')
    for kind in ('cpt','sft'):
        for split in ('train','valid','test'):
            plain = rows(output/('cpt_text' if kind=='cpt' else 'sft_messages')/(split+'.jsonl'))
            tokens = rows(output/(kind+'_tokens')/(split+'.jsonl'))
            refs = [r for r in provenance if r['dataset']==kind and r['split']==split]
            if len(plain)!=len(tokens) or len(tokens)!=len(refs) or len(tokens)!=manifest['counts'][kind+'_tokens'][split]:
                raise ValueError('Counts or row alignment incorrect')
            for raw,row,ref in zip(plain,tokens,refs):
                ids,mask,labels = row['input_ids'],row['attention_mask'],row['labels']
                if not ids or not len(ids)==len(mask)==len(labels) or any(x!=1 for x in mask):
                    raise ValueError('Invalid token arrays')
                if len(ids)>manifest[kind+'_limit']:
                    raise ValueError('Overlong row')
                if kind=='cpt':
                    if labels!=ids or ids[-1]!=manifest['eos_token_id']:
                        raise ValueError('CPT labels/EOS')
                    key = hashlib.sha256(raw['text'].encode()).hexdigest()
                    if key!=ref['text_sha256']:
                        raise ValueError('CPT correspondence')
                else:
                    start,end = ref['assistant_start'],ref['assistant_eos']
                    if not 0<start<=end<len(ids) or ids[end]!=manifest['eos_token_id']:
                        raise ValueError('Assistant span invalid')
                    expected = [-100]*start+ids[start:end+1]+[-100]*(len(ids)-end-1)
                    if labels!=expected:
                        raise ValueError('Assistant-only masking lost')
                    key = hashlib.sha256(json.dumps(raw['messages'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                    if key!=ref['messages_sha256']:
                        raise ValueError('SFT correspondence')
                    if passages[ref['passage_id']]['text'] not in raw['messages'][1]['content']:
                        raise ValueError('Grounding passage missing from prompt')
                    if ref['passage_id'] not in raw['messages'][2]['content']:
                        raise ValueError('Target citation missing')
    questions = rows(output/'evaluation/questions.jsonl')
    rubrics = rows(output/'evaluation/rubrics.jsonl')
    if len(questions)!=manifest['evaluation_count'] or {q['id'] for q in questions}!={r['id'] for r in rubrics}:
        raise ValueError('Evaluation coverage mismatch')
    if len({q['id'] for q in questions})!=len(questions):
        raise ValueError('Repeated evaluation ID')
    for question in questions:
        if assignment[question['source_id']]=='train' or question['split']!=assignment[question['source_id']]:
            raise ValueError('Evaluation entered training')
    if any(r['cross_split'] for r in rows(output/'near-duplicates.jsonl')):
        raise ValueError('Near duplicate crosses partitions')
    return {'status':'pass','counts':manifest['counts'],'evaluation_count':len(questions),
            'languages':dict(Counter(r['language'] for r in provenance if r['dataset']=='sft')),
            'expert_validated':False,'scope':'Integrity and preparation only; no model performance score'}

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'grounded-v3')
    args = parser.parse_args()
    print(json.dumps(verify(HERE,args.output.resolve()),indent=2))
