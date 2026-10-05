"""Qwen-specific exports from immutable licensed inputs; no training execution."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import unicodedata

HERE = Path(__file__).resolve().parent
SPLITS = ('train', 'valid', 'test')
ASSIGNMENT = {'MET001': 'train', 'MET002': 'train',
              'thermal_en_prediction': 'train', 'thermal_en_critical': 'train',
              'thermal_en_flow': 'train', 'MET003': 'valid', 'MET004': 'test'}
ADMIN = re.compile(r'author contributions|funding|acknowledg|conflict|references|ethics|rights|supplement|data availability', re.I)
RESERVED = re.compile(r'<\|[^<>]+\|>')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def save_rows(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))

def normalize(text):
    # NFC preserves scientific symbols; NFKC could change superscripts and units.
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()

def verify_identity(soup, source):
    meta = lambda key: [t.get('content', '') for t in soup.select(f'meta[name="{key}"]')]
    if source['doi'].lower() not in [s.strip().lower() for s in meta('citation_doi')]:
        raise ValueError('Snapshot DOI mismatch: ' + source['source_id'])
    if normalize(source['title']).casefold() not in [normalize(s).casefold() for s in meta('citation_title')]:
        raise ValueError('Snapshot title mismatch: ' + source['source_id'])

def extract_paragraphs(soup, source_id):
    accepted, rejected = [], []
    candidates = soup.select('.html-p') or soup.select('.c-article-section__content p')
    seen = set()
    for ordinal, p in enumerate(candidates):
        original = normalize(p.get_text(' ', strip=True))
        if not original:
            continue
        key = sha(original.encode())
        ancestors = list(p.parents)
        section = next((a for a in ancestors if a.name == 'section' or 'c-article-section' in (a.get('class') or [])), None)
        heading = section.find(['h2','h3']) if section else None
        title = normalize(heading.get_text(' ', strip=True)) if heading else ''
        sid = section.get('id', '') if section else ''
        classes = ' '.join(' '.join(a.get('class') or []) for a in [p, *ancestors])
        reason = None
        if not (sid == 'html-abstract' or sid == 'Abs1-section' or sid.lower().startswith('sec')) or ADMIN.search(title):
            reason = 'outside_scientific_sections'
        elif any(a.name in ('figure','figcaption','table') for a in ancestors) or re.search(r'figure|caption|table', classes, re.I):
            reason = 'figure_or_table_context'
        elif p.find(['math','img']) or p.find(class_=re.compile(r'math|formula|equation', re.I)) or re.search(r'\\\(|\\\[', original):
            reason = 'formula_or_image_requires_visual_review'
        elif RESERVED.search(original):
            reason = 'reserved_token_literal'
        elif key in seen:
            reason = 'duplicate_paragraph'
        elif len(original) < 80:
            reason = 'short_fragment_or_label'
        seen.add(key)
        if reason:
            rejected.append({'source_id': source_id, 'paragraph': ordinal,
                             'reason': reason, 'original_sha256': key})
            continue
        text = re.sub(r'\[\s*[\d,;\s–—-]+\]', '', original)
        text = normalize(text)
        accepted.append({'source_id': source_id, 'paragraph': ordinal,
                         'section': title or sid, 'text': text,
                         'original_sha256': key, 'text_sha256': sha(text.encode())})
    return accepted, rejected

def paragraph_chunks(paragraphs, tok, limit):
    chunks, rejected, current = [], [], []
    def emit():
        if current:
            chunks.append(list(current))
            current.clear()
    for paragraph in paragraphs:
        if len(tok.encode(paragraph['text'], add_special_tokens=False)) + 1 > limit:
            emit()
            rejected.append({**{k:v for k,v in paragraph.items() if k != 'text'}, 'reason': 'whole_paragraph_over_token_budget'})
            continue
        # Preserve original paragraph order; never merge across a rejected gap.
        if current and paragraph['paragraph'] != current[-1]['paragraph'] + 1:
            emit()
        candidate = '\n\n'.join(p['text'] for p in [*current, paragraph])
        if len(tok.encode(candidate, add_special_tokens=False)) + 1 > limit:
            emit()
        current.append(paragraph)
    emit()
    return chunks, rejected

def assistant_tokens(messages, tok, limit):
    if [m['role'] for m in messages] != ['system','user','assistant']:
        raise ValueError('Expected a complete system/user/assistant example')
    if any(not isinstance(m['content'], str) or not m['content'].strip() or RESERVED.search(m['content']) for m in messages):
        raise ValueError('Empty message or embedded reserved token')
    kwargs = {'tokenize': True, 'enable_thinking': False}
    full = tok.apply_chat_template(messages, add_generation_prompt=False, **kwargs)
    prefix = tok.apply_chat_template(messages[:-1], add_generation_prompt=True, **kwargs)
    if full[:len(prefix)] != prefix:
        raise ValueError('Chat template prompt prefix differs from completed example')
    if len(full) > limit:
        raise ValueError('Complete SFT example exceeds budget; no truncation permitted')
    eos = tok.eos_token_id
    try:
        end = full.index(eos, len(prefix))
    except ValueError as error:
        raise ValueError('Assistant EOS missing') from error
    labels = [-100] * len(full)
    labels[len(prefix):end+1] = full[len(prefix):end+1]
    if not any(n != -100 for n in labels):
        raise ValueError('No assistant training target')
    return {'input_ids': full, 'attention_mask': [1] * len(full), 'labels': labels}, len(prefix), end

def build(root, tokenizer_path, output, cpt_limit=2048, sft_limit=1024):
    from bs4 import BeautifulSoup
    from transformers import AutoTokenizer
    if output.exists():
        raise ValueError('Use a fresh export directory; existing exports are immutable')
    if min(cpt_limit, sft_limit) < 16:
        raise ValueError('Token budget too small')
    # Check v1 input hashes without regenerating or modifying the historical data.
    frozen = json.loads((root/'manifest.json').read_text())['input_and_data_sha256']
    for relative, expected in frozen.items():
        if sha((root/relative).read_bytes()) != expected:
            raise ValueError('Frozen input changed: ' + relative)
    tok = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=False)
    if tok.eos_token_id is None or not tok.chat_template:
        raise ValueError('Tokenizer needs an EOS token and native chat template')
    eos = tok.eos_token_id
    sources = json.loads((root/'input/documents.json').read_text())
    corrections = json.loads((root/'format-input/corrections.json').read_text())
    registry, quarantine, cpt_provenance, sft_provenance = [], [], [], []
    datasets = {kind: {s: [] for s in SPLITS} for kind in ('cpt_text','cpt_tokens','sft_messages','sft_tokens','metadata_messages','metadata_tokens')}
    for original_source in sources:
        source = dict(original_source)
        if source['source_id'] in corrections:
            source.update({k:v for k,v in corrections[source['source_id']].items() if k in ('original_path','authors','license_evidence')})
            correct = corrections[source['source_id']]
            if sha((root/correct['original_path']).read_bytes()) != correct['sha256']:
                raise ValueError('Correction snapshot changed')
            source['provenance_correction'] = correct['reason']
        if source['license'] != 'CC BY 4.0':
            raise ValueError('Source is outside the license allowlist')
        snapshot = root/source['original_path']
        soup = BeautifulSoup(snapshot.read_bytes(), 'html.parser')
        verify_identity(soup, source)
        source['authors'] = [m.get('content') for m in soup.select('meta[name="citation_author"]')]
        if not source['authors']:
            raise ValueError('Author attribution missing')
        source['snapshot_sha256'] = sha(snapshot.read_bytes())
        source['split'] = ASSIGNMENT[source['source_id']]
        registry.append(source)
        paragraphs, rejects = extract_paragraphs(soup, source['source_id'])
        quarantine.extend(rejects)
        chunks, rejects = paragraph_chunks(paragraphs, tok, cpt_limit)
        quarantine.extend(rejects)
        if not chunks:
            raise ValueError('No admissible scientific prose: ' + source['source_id'])
        for number, chunk in enumerate(chunks):
            text = '\n\n'.join(p['text'] for p in chunk)
            ids = tok.encode(text, add_special_tokens=False) + [eos]
            split = source['split']
            datasets['cpt_text'][split].append({'text': text})
            datasets['cpt_tokens'][split].append({'input_ids': ids, 'attention_mask': [1]*len(ids), 'labels': ids})
            cpt_provenance.append({'id': f"{source['source_id']}-prose-{number:04d}", 'source_ids':[source['source_id']],
                                   'split':split, 'paragraphs':[p['paragraph'] for p in chunk],
                                   'sections':[p['section'] for p in chunk], 'text_sha256':sha(text.encode()),
                                   'tokens':len(ids), 'scientific_review':'not_expert_validated',
                                   'transformation':'NFC; whitespace normalized; numeric reference markers removed; whole prose paragraphs grouped without overlap; tables, figures and detected math excluded. EOS added to tokenized rows only.'})
    by_id = {s['source_id']:s for s in registry}
    for row in rows(root/'data/sft-records.jsonl'):
        splits = {ASSIGNMENT[s] for s in row['source_ids']}
        if len(splits) != 1:
            raise ValueError('SFT source leakage')
        split = splits.pop()
        messages = [{**m, 'content': unicodedata.normalize('NFC', m['content']).strip()} for m in row['messages']]
        kind = 'metadata' if row['task'] == 'metadata_extraction' else 'sft'
        if kind == 'sft':
            # Supply the reference identifiers that the existing targets cite.
            references = [{k:by_id[s][k] for k in ('source_id','title','doi','url')} for s in row['source_ids']]
            messages[1]['content'] += '\n\nSource references (bibliographic context, not full-text evidence):\n' + json.dumps(references, ensure_ascii=False)
        token_row, start, end = assistant_tokens(messages, tok, sft_limit)
        datasets[kind+'_messages'][split].append({'messages': messages})
        datasets[kind+'_tokens'][split].append(token_row)
        sft_provenance.append({'id':row['id'], 'source_ids':row['source_ids'], 'split':split,
                              'dataset':kind, 'language':row['language'], 'task':row['task'],
                              'review_status':row.get('review_status'), 'assistant_start':start,
                              'assistant_eos':end, 'tokens':len(token_row['input_ids']),
                              'loss_tokens':sum(n != -100 for n in token_row['labels']),
                              'messages_sha256':sha(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode())})
    # Each article is its own source family; never deduplicate by a split alone.
    for kind in ('cpt_text','sft_messages','metadata_messages'):
        seen = {}
        for split in SPLITS:
            for record in datasets[kind][split]:
                key = sha(json.dumps(record, sort_keys=True, ensure_ascii=False).encode())
                if key in seen:
                    raise ValueError('Duplicate example in ' + kind + ': ' + seen[key] + '/' + split)
                seen[key] = split
    # Inputs containing errors stay historical; these v2 exports use corrected evidence.
    for kind, splits in datasets.items():
        for split, records in splits.items():
            save_rows(output/kind/(split+'.jsonl'), records)
    save(output/'sources.json', registry)
    save_rows(output/'cpt-provenance.jsonl', cpt_provenance)
    save_rows(output/'sft-provenance.jsonl', sft_provenance)
    save_rows(output/'quarantine.jsonl', quarantine)
    # LLaMA-Factory reads native messages as ShareGPT using explicit role mappings.
    dataset_info = {}
    for kind in ('sft','metadata'):
        for split in SPLITS:
            dataset_info[f'metal_{kind}_{split}'] = {'file_name':f'{kind}_messages/{split}.jsonl', 'formatting':'sharegpt',
                'columns':{'messages':'messages'}, 'tags':{'role_tag':'role','content_tag':'content','user_tag':'user','assistant_tag':'assistant','system_tag':'system'}}
    save(output/'dataset_info.json', dataset_info)
    tokenizer_hashes = {p.name:sha(p.read_bytes()) for p in sorted(tokenizer_path.iterdir()) if p.is_file() and p.name != 'download-receipt.json'}
    files = {str(p.relative_to(output)):sha(p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()}
    profile = {'status':'formatted_not_trained', 'tokenizer_files_sha256':tokenizer_hashes,
               'libraries':{name:importlib.metadata.version(name) for name in ('transformers','tokenizers','beautifulsoup4','jinja2')},
               'chat_template_sha256':sha(tok.chat_template.encode()), 'eos_token':tok.eos_token, 'eos_token_id':eos,
               'cpt_limit':cpt_limit, 'sft_limit':sft_limit,
               'counts':{k:{s:len(v) for s,v in d.items()} for k,d in datasets.items()},
               'maximum_tokens':{k:max(len(r['input_ids']) for v in datasets[k].values() for r in v) for k in ('cpt_tokens','sft_tokens','metadata_tokens')},
               'quarantine_reasons':dict(Counter(q['reason'] for q in quarantine)),
               'source_assignment':ASSIGNMENT, 'packing':'whole contiguous paragraphs within one source, without overlap; no SFT packing or padding',
               'sft_labels':'assistant content plus its EOS only; system/user/assistant header/trailing newline use -100',
               'cpt_labels':'every token including one EOS per row; no chat template',
               'sft_default':'technical explanations only; metadata is an optional separate curriculum, not mixed by default',
               'input_hashes':{str(p.relative_to(root)):sha(p.read_bytes()) for p in [root/'format_qwen.py',root/'format-input/corrections.json',root/'format-input/MET004.license.txt',*(root/s['original_path'] for s in registry)]},
               'output_hashes':files, 'expert_validated':False, 'training_run':False,
               'limits':['No universal optimal format; tokenized exports are bound to this exact tokenizer/template.',
                         'Formula detection is conservative and incomplete; other numerical claims still need review.',
                         'SFT targets are synthetic; supplied bibliographic references do not constitute passage-level evidence.',
                         'Technical SFT validation/test are very small; no measured model performance is claimed.']}
    save(output/'manifest.json', profile)
    return profile

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cpt-limit', type=int, default=2048)
    p.add_argument('--sft-limit', type=int, default=1024)
    a = p.parse_args()
    result = build(HERE, a.tokenizer.resolve(), a.output.resolve(), a.cpt_limit, a.sft_limit)
    print(json.dumps({k:result[k] for k in ('status','counts','maximum_tokens','quarantine_reasons')}, indent=2))

if __name__ == '__main__':
    main()
