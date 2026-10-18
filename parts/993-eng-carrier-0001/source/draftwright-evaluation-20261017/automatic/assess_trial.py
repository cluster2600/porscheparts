"""Record the bounded trial outcome without another drawing build."""
from pathlib import Path
import hashlib,json,re
import pypdfium2
BASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
execution=json.loads((BASE/'execution-receipt.json').read_text())
files=list((BASE/'drawing-001').rglob('*')) if (BASE/'drawing-001').exists() else []
pdfs=[p for p in files if p.suffix=='.pdf'];texts={}
for pdf in pdfs:
 document=pypdfium2.PdfDocument(pdf)
 texts[pdf.name]='\n'.join(document[i].get_textpage().get_text_range() for i in range(len(document)))
(BASE/'pdf-text.json').write_text(json.dumps(texts,indent=2,ensure_ascii=False)+'\n')
reports=[p for p in files if p.name.endswith('.draftwright.json')]
report=json.loads(reports[0].read_text()) if len(reports)==1 else None
summary=dict(schema='carrier-draftwright-isolated-trial-assessment-1',
 status='rejected_timeout_no_drawing' if execution['timeout_triggered'] else 'drawing_requires_content_and_visual_review' if execution['returncode']==0 else 'rejected_cli_error',
 execution_receipt_sha256=sha(BASE/'execution-receipt.json'),plan_sha256=sha(BASE/'plan.json'),provenance_sha256=sha(BASE/'provenance.json'),
 nominal_model_inspection_sha256=sha(BASE/'nominal-model-inspection.json'),pdf_text_sha256=sha(BASE/'pdf-text.json'),
 CLI_returncode=execution['returncode'],CLI_seconds=execution['seconds'],timeout_triggered=execution['timeout_triggered'],
 produced_files=execution['output_files_sha256'],STEP_and_source_inputs_unchanged=execution['inputs_unchanged'],
 lint_report_present=report is not None,lint_report_sha256=sha(reports[0]) if len(reports)==1 else None,
 lint=report.get('lint') if report else None,
 pdf_text_checks={name:dict(nominal_numeric_tokens={n:bool(re.search(r'(?<![\d.])'+re.escape(n)+r'(?![\d.])',text)) for n in ['592','73','52','560','100','40','11','13.5']},
  ISO2768_present=bool(re.search(r'ISO\s*2768',text)),plus_minus_present='±' in text) for name,text in texts.items()},
 comparison_scope='Model inspection reads analytic STEP cylinders and kernel bounds. Recognized/printed drawing dimensions are separate observations; no dimensional fit, tolerance, ISO compliance or manufacturing approval is inferred.',
 adoption=False,another_CLI_attempt=False,core_sources_changed=False,staged_software_modified_by_this_trial=False)
(BASE/'assessment.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:summary[k] for k in ['status','CLI_returncode','CLI_seconds','timeout_triggered','produced_files','lint_report_present']},indent=2));print('assessment_sha256',sha(BASE/'assessment.json'))
