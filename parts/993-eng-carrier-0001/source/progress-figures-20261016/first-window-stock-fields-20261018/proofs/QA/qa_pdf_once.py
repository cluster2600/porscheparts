"""Read actual PDF metadata and rasterize its one page for visual QA only."""
import hashlib,json,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;Q=H/'tmp/pdfs/qa-001';pdf=H/'render-001/carrier-first-window-stock-stress-displacement.pdf'
d=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=d(pdf);require=before=='4d3e89eb92b3a19b48b52f5e75e5e69e787c068c5245b1f8e3823ec5cb1e9b33';assert require
commands=[['/opt/homebrew/bin/pdfinfo',str(pdf)],['/opt/homebrew/bin/pdftoppm','-r','110','-png','-singlefile',str(pdf),str(Q/'page1')]]
rows=[]
for i,argv in enumerate(commands):
 with(Q/(str(i)+'.stdout.log')).open('xb')as out,(Q/(str(i)+'.stderr.log')).open('xb')as err:r=subprocess.run(argv,stdout=out,stderr=err,timeout=30)
 assert r.returncode==0;rows.append(dict(argv=argv,actual_returncode=r.returncode,binary_sha256=d(Path(argv[0]).resolve())))
assert d(pdf)==before;assert 'Pages:           1' in(Q/'0.stdout.log').read_text()
result={'schema':'actual-Figure33-PDF-page-raster-QA-source-1','PDF_sha256':before,'commands':rows,'raster_sha256':d(Q/'page1.png'),'source_sha256':d(Path(__file__)),'PDF_unchanged':True,'no_new_PDF_authoring':True,'visual_review':None}
(Q/'raster-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
