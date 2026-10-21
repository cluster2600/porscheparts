"""Change only the linear solver in a hash-verified existing mechanics preparation."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def iterative_deck(text):
    old='*STATIC,SOLVER=SPOOLES';new='*STATIC,SOLVER=ITERATIVE CHOLESKY'
    if text.splitlines().count(old)!=1:raise ValueError('Exactly one original static solver directive required')
    lines=text.splitlines(keepends=True)
    return ''.join(line.replace(old,new)if line.rstrip('\r\n')==old else line for line in lines)


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--preparation',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh output required')
    source=args.preparation/'assessment.json';report=json.loads(source.read_text())
    for name,digest in report['output_sha256'].items():
        path=Path(name)
        if path.name!=name or sha(args.preparation/name)!=digest:raise ValueError('Retained preparation identity differs')
    decks={name:iterative_deck((args.preparation/(name+'.inp')).read_text())for name in report['loads']}
    args.output.mkdir(parents=True)
    for name in report['output_sha256']:
        target=args.output/name
        if target.stem in decks and target.suffix=='.inp':target.write_text(decks[target.stem])
        else:target.write_bytes((args.preparation/name).read_bytes())
    for name in report['loads']:report['loads'][name]['deck_sha256']=sha(args.output/(name+'.inp'))
    report.update(status='unchanged_physics_iterative_Cholesky_preparation_not_solved',linear_solver='ITERATIVE CHOLESKY',geometry_material_loads_and_supports_unchanged=True)
    report['source_sha256'].update({str(source):sha(source),str(Path(__file__)):sha(Path(__file__))})
    report['output_sha256']={p.name:sha(p)for p in args.output.iterdir()if p.is_file()}
    (args.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
