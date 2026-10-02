"""Private, page-addressable Porsche corpus; source copies never enter Git."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def reference(value):
    return re.sub(r'[^A-Z0-9]', '', value.upper())


def partition(key):
    number = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 10
    return 'test' if number == 0 else 'valid' if number == 1 else 'train'


def site_records(site):
    """Preserve all catalogue occurrences; never promote machine transcription."""
    listed = json.loads((site/'data/oem-listed.json').read_text())['listings']
    for i, row in enumerate(listed):
        if row['generationId'] != '993':
            continue
        yield {'id': f'pet-{i}', 'kind': 'pet', 'reference': reference(row['oemReference']),
               'source': row['petSourceId'], 'page': row['petPage'],
               'assembly': row['petIllustration'], 'status': 'listed_not_fitment_verified',
               'split_key': 'part:'+reference(row['oemReference']), 'data': row}
    for kind in ('technical-data', 'torque-specs', 'procedures'):
        rows = json.loads((site/'data/993-manual'/f'{kind}.json').read_text())['entries']
        for i, row in enumerate(rows):
            yield {'id': f'{kind}-{i}', 'kind': kind, 'reference': '',
                   'source': '993-workshop-manual-derived', 'page': row['page'],
                   'assembly': '', 'status': 'derived_transcription_not_page_verified',
                   'split_key': f'manual-page:{row["page"]}', 'data': row}
    reviewed = json.loads((site/'data/oem-parts.json').read_text())['oemParts']
    for i, row in enumerate(reviewed):
        if row.get('generationId') == '993':
            yield {'id': f'read-{i}', 'kind': 'site-review',
                   'reference': reference(row['oemReference']),
                   'source': row.get('petSourceId', 'site-review'),
                   'page': row.get('petIllustrationPage'),
                   'assembly': row.get('petIllustration', ''),
                   'status': 'site_authored_claims_not_independently_revalidated',
                   'split_key': 'part:'+reference(row['oemReference']), 'data': row}


def document_records(source, path):
    """Read every PDF page; do not infer diagram topology from extracted text."""
    if path.suffix.lower() == '.pdf':
        text = subprocess.check_output(['pdftotext', '-layout', str(path), '-'], text=True)
    else:
        text = path.read_text()
    pages = text.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    for page, content in enumerate(pages, 1):
        yield {'id': f'{source}-page-{page}', 'kind': 'document-page',
               'reference': '', 'source': source, 'page': page, 'assembly': '',
               'status': 'text_extracted_not_visually_validated',
               'split_key': f'{source}-page-{page}', 'data': {'text': content}}


def build(site, output, documents):
    output.mkdir(parents=True, exist_ok=True)
    db = output/'knowledge.sqlite'
    if db.exists():
        raise ValueError('Refusing to overwrite an existing corpus; use a new directory')
    files = [site/'data/oem-listed.json', site/'data/oem-parts.json']
    files += [site/'data/993-manual'/f'{k}.json' for k in ('technical-data','torque-specs','procedures')]
    rows = list(site_records(site))
    for source, path in documents:
        if not re.fullmatch(r'[a-z0-9-]+', source):
            raise ValueError('Document source IDs must be lowercase letters/digits/hyphens')
        files.append(path)
        rows.extend(document_records(source, path))
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate record/source IDs')
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE records (id TEXT PRIMARY KEY, kind TEXT, reference TEXT, source TEXT, page INTEGER, assembly TEXT, payload TEXT)')
        conn.execute('CREATE INDEX by_reference ON records(reference)')
        conn.execute('CREATE INDEX by_assembly ON records(source,assembly)')
        conn.execute('CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, text)')
        for row in rows:
            body = compact(row)
            conn.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)',
                         tuple(row[k] for k in ('id','kind','reference','source','page','assembly'))+(body,))
            conn.execute('INSERT INTO search VALUES (?,?)', (row['id'], compact(row['data'])))
        assert conn.execute('SELECT count(*) FROM records').fetchone()[0] == len(rows)
    (output/'records.jsonl').write_text(''.join(compact(r)+'\n' for r in rows))
    manifest = {'inputs': {str(f.resolve()): digest(f) for f in files},
                'records': len(rows), 'counts': dict(collections.Counter(r['kind'] for r in rows)),
                'references': len({r['reference'] for r in rows if r['reference']}),
                'assemblies_by_source': len({(r['source'],r['assembly']) for r in rows if r['assembly']}),
                'empty_document_pages': [r['id'] for r in rows if r['kind']=='document-page' and not r['data']['text'].strip()],
                'document_pages': dict(collections.Counter(r['source'] for r in rows if r['kind']=='document-page')),
                'corpus_sha256': digest(output/'records.jsonl'),
                'limits': 'Assembly membership is catalogue co-occurrence, not attachment topology. Source errors remain visible. Raw sources and records stay local.'}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def query(db, text, limit=8, assembly=False):
    if not 1 <= limit <= 100:
        raise ValueError('limit must be 1..100')
    # ponytail: exact references + SQLite FTS; multilingual semantic search is not provided.
    with sqlite3.connect(f'file:{db.resolve()}?mode=ro', uri=True) as conn:
        rows = conn.execute('SELECT payload FROM records WHERE reference=? ORDER BY id', (reference(text),)).fetchall()
        if assembly and rows:
            groups = {(json.loads(x[0])['source'],json.loads(x[0])['assembly']) for x in rows}
            rows = [r for source, group in sorted(groups) if group for r in conn.execute(
                'SELECT payload FROM records WHERE source=? AND assembly=? ORDER BY id', (source,group))]
        elif not rows:
            words = re.findall(r'\w+', text)
            if not words:
                return []
            terms = ' AND '.join('"'+w+'"' for w in words)
            rows = conn.execute('SELECT records.payload FROM search JOIN records ON records.id=search.id WHERE search MATCH ? ORDER BY bm25(search) LIMIT ?', (terms,limit)).fetchall()
        return [json.loads(x[0]) for x in rows[:limit]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['build','query'])
    p.add_argument('--site', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--document', action='append', default=[], help='source-id=/absolute/file.pdf or layout.txt')
    p.add_argument('--text'); p.add_argument('--assembly', action='store_true')
    p.add_argument('--limit', type=int, default=8)
    a = p.parse_args()
    if a.action == 'build':
        if not a.site: p.error('--site required for build')
        docs = [(s,Path(f)) for s,f in (x.split('=',1) for x in a.document)]
        print(json.dumps(build(a.site,a.output,docs),indent=2))
    else:
        if not a.text: p.error('--text required for query')
        print(json.dumps(query(a.output/'knowledge.sqlite',a.text,a.limit,a.assembly),indent=2,ensure_ascii=False))


if __name__ == '__main__':
    main()
