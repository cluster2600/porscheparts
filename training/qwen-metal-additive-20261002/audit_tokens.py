"""Audit complete examples against an exact LOCAL tokenizer; never truncate data."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--max-length', type=int, required=True)
    parser.add_argument('--dataset', choices=('cpt','sft'), default='sft')
    args = parser.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(args.tokenizer.resolve()), local_files_only=True, trust_remote_code=False)
    results = {}
    for split in ('train','valid','test'):
        path = Path(__file__).resolve().parent/'data'/args.dataset/(split+'.jsonl')
        lengths = []
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if 'messages' in row:
                ids = tok.apply_chat_template(row['messages'], tokenize=True, add_generation_prompt=False)
            else:
                ids = tok(row['text'], add_special_tokens=True)['input_ids']
            if isinstance(ids, dict):
                ids = ids['input_ids']
            lengths.append(len(ids))
        results[split] = {'maximum_tokens': max(lengths), 'total_tokens': sum(lengths),
                          'over_limit': sum(n > args.max_length for n in lengths)}
    print(json.dumps(results, indent=2))
    if any(r['over_limit'] for r in results.values()):
        raise SystemExit('Examples exceed the registered limit. Change chunking/configuration deliberately; do not silently truncate.')

if __name__ == '__main__':
    main()
