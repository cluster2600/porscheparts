"""Inspect existing authored exports only; never builds a drawing or recognition."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
import pypdfium2
from PIL import Image
BASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=json.loads((BASE/'execution-receipt.json').read_text())
if run['returncode']!=0:
 result=dict(status='refused_execution',returncode=run['returncode'],timeout_triggered=run['timeout_triggered'],
 seconds=run['seconds'],last_stdout=(BASE/'stdout.log').read_text(),stderr=(BASE/'stderr.log').read_text(),exports_reviewed=False)
else:
 pdf=BASE/'drawing/carrier-F0.pdf';svg=BASE/'drawing/carrier-F0.svg';png=BASE/'drawing/carrier-F0.png'
 doc=pypdfium2.PdfDocument(pdf);pages=[];texts=[]
 for index in range(len(doc)):
  page=doc[index];width,height=page.get_size();text=page.get_textpage();value=text.get_text_range();texts.append(value);outside=[]
  for k in range(text.count_chars()):
   x0,y0,x1,y1=text.get_charbox(k)
   if not (0<=x0<=x1<=width and 0<=y0<=y1<=height):outside.append(dict(index=k,text=text.get_text_range(k,1),bbox_pt=[x0,y0,x1,y1]))
  pages.append(dict(width_mm=width*25.4/72,height_mm=height*25.4/72,text_characters=text.count_chars(),out_of_page_characters=outside))
 (BASE/'pdf-text.txt').write_text('\n'.join(texts))
 root=ET.parse(svg).getroot();svgt=' '.join(n.text or '' for n in root.iter() if n.tag.endswith('text') or n.tag.endswith('tspan'))
 (BASE/'svg-text.txt').write_text(svgt)
 raw=' '.join(texts)+' '+svgt
 tokens={n:bool(re.search(r'(?<![\d.])'+n.replace('.','[.,]')+r'(?![\d.])',raw)) for n in ['592','73','52','560','100','40','11','13.5']}
 with Image.open(png) as image:png_size=list(image.size)
 result=dict(status='exports_present_pending_visual_root_review',execution_receipt_sha256=sha(BASE/'execution-receipt.json'),
 page_count=len(doc),pages=pages,svg=dict(width=root.get('width'),height=root.get('height'),viewBox=root.get('viewBox')),
 PNG_pixels=png_size,expected_eight_F0_numeric_tokens_found=tokens,ISO2768_present=bool(re.search(r'ISO\s*2768',raw)),plus_minus_present='±' in raw,
 placement_lint=json.loads((BASE/'placement-lint.json').read_text()),physical_recognition_lint_performed=False,
 STEP_and_sources_unchanged=run['inputs_unchanged'],adopted=False,
 scope='PDF text boxes and SVG page extent are inspected, alongside placement-only lint; this is not full recognition/physical completeness or automatic drawing acceptance.')
(BASE/'review.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(result,indent=2,ensure_ascii=False));print('review_sha256',sha(BASE/'review.json'))
