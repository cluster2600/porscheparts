"""Audit future predictions and create independent-review worksheets; no LLM judge."""
import argparse
import hashlib
import json
from pathlib import Path
import verify_grounded

HERE=Path(__file__).resolve().parent
FIELDS=('correctness','grounding','scope_and_uncertainty','units_and_numbers')

def evaluate(export,predictions,reviews=None):
    questions=verify_grounded.rows(export/'evaluation/questions.jsonl')
    rubrics={r['id']:r for r in verify_grounded.rows(export/'evaluation/rubrics.jsonl')}
    expected={r['id'] for r in questions}
    predicted={}
    for row in predictions:
        if row['id'] in predicted or row['id'] not in expected or not isinstance(row.get('response'),str) or not row['response'].strip():
            raise ValueError('Duplicate/unknown ID or empty prediction')
        predicted[row['id']]=row['response']
    if set(predicted)!=expected:
        raise ValueError('Incomplete evaluation coverage')
    manual={}
    for row in reviews or []:
        if row['id'] in manual or row['id'] not in expected:
            raise ValueError('Duplicate/unknown review ID')
        scores=row.get('scores',{})
        if set(scores)!=set(FIELDS) or any(type(scores[k]) is not int or scores[k] not in (0,1,2) for k in FIELDS):
            raise ValueError('Each rubric score must be 0, 1 or 2')
        if not isinstance(row.get('reviewer'),str) or not row['reviewer'].strip():
            raise ValueError('Independent reviewer identity required for manual scores')
        if row.get('prediction_sha256')!=hashlib.sha256(predicted[row['id']].encode()).hexdigest():
            raise ValueError('Review belongs to a different prediction')
        manual[row['id']]=row
    worksheet=[]
    for question in questions:
        id=question['id'];rubric=rubrics[id]
        worksheet.append({**rubric,'messages':question['messages'],'response':predicted[id],
                          'prediction_sha256':hashlib.sha256(predicted[id].encode()).hexdigest(),
                          'citation_present':rubric['required_citation'] in predicted[id],
                          'scores':manual[id]['scores'] if id in manual else rubric['scores'],
                          'reviewer':manual[id]['reviewer'] if id in manual else None})
    complete=len(manual)==len(expected)
    groups={split:[r for r in worksheet if r['split']==split] for split in ('valid','test')}
    return {'status':'predictions_audited','examples':len(expected),
            'citation_presence_rate':sum(r['citation_present'] for r in worksheet)/len(worksheet),
            'by_split':{split:{'examples':len(group),'citation_presence_rate':sum(r['citation_present'] for r in group)/len(group)} for split,group in groups.items() if group},
            'manually_reviewed':len(manual),'complete_manual_review':complete,
            'manual_mean_scores':{k:sum(r['scores'][k] for r in manual.values())/len(manual) for k in FIELDS} if complete else None,
            'scope':'Citation presence is syntactic, not proof of correctness. Manual scores require independent review; no training-release approval is implied.'},worksheet

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions',type=Path,required=True)
    parser.add_argument('--reviews',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    export=HERE/'grounded-v3'
    verify_grounded.verify(HERE,export)
    if args.output.exists():
        parser.error('Use a fresh report directory')
    report,worksheet=evaluate(export,verify_grounded.rows(args.predictions),verify_grounded.rows(args.reviews) if args.reviews else None)
    args.output.mkdir(parents=True)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (args.output/'review.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in worksheet),encoding='utf-8')
    print(json.dumps(report,indent=2))
