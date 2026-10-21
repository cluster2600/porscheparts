"""Read-only actual-PDF page raster QA in a fresh tmp/pdfs directory; no PDF authoring."""
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image

H=Path(__file__).resolve().parent
PDF=H/'render-001/carrier-first-window-stock-comparison.pdf'
EXPECTED='e86ab3018ff9b8764f5679699b5105e453382cce41fd57c71d2120d64cf6726d'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pixels(p):
    with Image.open(p)as image:
        rgb=image.convert('RGB')
        return dict(width=rgb.width,height=rgb.height,mode=rgb.mode,RGB_pixel_sha256=hashlib.sha256(rgb.tobytes()).hexdigest())

assert sha(PDF)==EXPECTED
out=H/'tmp/pdfs/qa-001';assert not out.exists();out.mkdir(parents=True)
prefix=out/'page1'
argv=['/opt/homebrew/bin/pdftoppm','-f','1','-singlefile','-r','130','-png',str(PDF),str(prefix)]
result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
assert result.returncode==0 and not result.stderr.strip()
png=prefix.with_suffix('.png');actual=pixels(png);previous=pixels(H/'pdf-qa-001.png')
assert actual==previous and sha(PDF)==EXPECTED
report=dict(schema='Figure32-fresh-tmp-Poppler-page-QA-1',status='READ_ONLY_PAGE_RASTER_IDENTICAL_TO_PREVIOUSLY_VIEWED_PAGE',
    source_sha256=sha(__file__),PDF_sha256_before=EXPECTED,PDF_sha256_after=sha(PDF),
    pdftoppm_physical_path=str(Path(argv[0]).resolve()),pdftoppm_binary_sha256=sha(Path(argv[0]).resolve()),
    argv=argv,actual_returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
    raster_path=str(png),raster_file_sha256=sha(png),pixel_record=actual,previous_raster_file_sha256=sha(H/'pdf-qa-001.png'),
    whole_RGB_pixels_equal_to_previous_viewed_PDF=True,PDF_authored_or_changed=False)
with(out/'report.json').open('x')as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(report))
