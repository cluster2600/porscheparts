"""Build an offline workshop guide and PDF from a single reviewed description."""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'scripts/templates/part-workflow.html.in'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_files(data, output):
    copied = {}
    for stage in data['stages']:
        for item in stage['files'] + ([stage['image']] if stage.get('image') else []):
            source = (ROOT / item.pop('source')).resolve()
            if not source.is_relative_to(ROOT) or not source.is_file():
                raise ValueError('Guide asset must be an existing repository/work file')
            key = source.relative_to(ROOT).as_posix()
            expected = digest(source)
            target = 'files/' + expected[:10] + '-' + source.name
            if key not in copied:
                shutil.copyfile(source, output / target)
                if digest(output / target) != expected or digest(source) != expected:
                    raise ValueError('Guide asset changed while being copied')
                copied[key] = {'file': target, 'sha256': expected, 'bytes': source.stat().st_size}
            item['path' if 'alt' in item else 'href'] = target
    data['files'] = [item for stage in data['stages'] for item in stage['files']]
    return copied


def make_pdf(data, output):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.pagesizes import A4

    font = Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    bold = Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    regular_name, bold_name = 'Helvetica', 'Helvetica-Bold'
    if font.is_file() and bold.is_file():
        pdfmetrics.registerFont(TTFont('Workshop', str(font)))
        pdfmetrics.registerFont(TTFont('Workshop-Bold', str(bold)))
        pdfmetrics.registerFontFamily('Workshop', normal='Workshop', bold='Workshop-Bold')
        regular_name, bold_name = 'Workshop', 'Workshop-Bold'
    ink, muted, orange = colors.HexColor('#192c38'), colors.HexColor('#58656c'), colors.HexColor('#bd4a26')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('WorkshopTitle', fontName=bold_name, fontSize=30, leading=33, textColor=ink, spaceAfter=18))
    styles.add(ParagraphStyle('WorkshopHeading', fontName=bold_name, fontSize=18, leading=22, textColor=ink, spaceAfter=10, spaceBefore=15))
    styles.add(ParagraphStyle('WorkshopBody', fontName=regular_name, fontSize=10, leading=14, textColor=ink, spaceAfter=9))
    styles.add(ParagraphStyle('WorkshopSmall', fontName=regular_name, fontSize=8, leading=11, textColor=muted, spaceAfter=6))
    styles.add(ParagraphStyle('WorkshopLabel', fontName=bold_name, fontSize=9, leading=12, textColor=orange, spaceAfter=9))
    styles.add(ParagraphStyle('WorkshopCode', fontName='Courier', fontSize=7.5, leading=11, textColor=ink, spaceBefore=8, spaceAfter=9))
    safe = lambda value: html.escape(str(value)).replace('\n', '<br/>')
    para = lambda value, style='WorkshopBody': Paragraph(safe(value), styles[style])
    story = [para('PORSCHEPARTS / ATELIER NUMÉRIQUE', 'WorkshopLabel'), para(data['title'], 'WorkshopTitle'),
             para(data['subtitle']), para(data['revision'], 'WorkshopSmall'), Spacer(1, 12)]
    metrics = Table([[para(m['value'], 'WorkshopHeading') for m in data['metrics']],
                     [para(m['label'], 'WorkshopSmall') for m in data['metrics']]], colWidths=[123] * 4)
    metrics.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEABOVE', (0, 0), (-1, 0), 1, ink), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story += [metrics, Spacer(1, 20), para('Le parcours commun', 'WorkshopHeading')]
    route = Table([[para(f"{i+1:02d}  {s['title']}") for i, s in enumerate(data['stages'][:3])],
                   [para(f"{i+4:02d}  {s['title']}") for i, s in enumerate(data['stages'][3:])]], colWidths=[164] * 3)
    route.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#d8ddda')), ('INNERGRID', (0, 0), (-1, -1), .5, colors.HexColor('#d8ddda')), ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    story += [route, Spacer(1, 18)]
    for source in data['inputs']:
        story += [para(source['title'], 'WorkshopLabel'), para(source['description'])]
    story.append(PageBreak())
    for index, stage in enumerate(data['stages']):
        story += [para(stage['state_label'], 'WorkshopLabel'),
                  para(f"{index+1:02d} / {stage['title']}", 'WorkshopHeading'), para(stage['purpose']),
                  para('Logiciels : ' + ' ; '.join(stage['tools']), 'WorkshopSmall')]
        rows = [[para(item['label']), para(item['value'])] for item in stage['checks']]
        if rows:
            table = Table(rows, colWidths=[270, 222], hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#d8ddda')), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 6)]))
            story.append(table)
        if stage.get('image'):
            image = Image(str(output / stage['image']['path']))
            scale = min(492 / image.imageWidth, 350 / image.imageHeight)
            image.drawWidth, image.drawHeight = image.imageWidth * scale, image.imageHeight * scale
            story += [Spacer(1, 10), image, para(stage['image']['alt'], 'WorkshopSmall')]
        story += [para('Fichiers : ' + ' ; '.join(item['label'] for item in stage['files']), 'WorkshopSmall')]
        if stage['commands']:
            story += [para('Commande reproductible', 'WorkshopLabel'),
                      para('\n\n'.join(stage['commands']), 'WorkshopCode')]
        if index + 1 < len(data['stages']):
            story.append(PageBreak())
    story += [PageBreak(), para('La remise à l’atelier', 'WorkshopTitle'), para(data['delivery_note']),
              para('Fiche de retour de pose', 'WorkshopHeading'), para('À compléter avec la révision exacte et des photos repérées. Le retour permet de corriger les dimensions ou les dégagements de la prochaine révision.')]
    fields = [('Révision / date / véhicule', ''), ('Position et orientation de montage', ''),
              ('Fixation ou portée concernée', ''), ('Cote prévue / cote observée', ''),
              ('Contact, jeu ou dégagement observé', ''), ('Modification nécessaire', ''),
              ('Fonctionnement observé / durée / régime', ''), ('Photos et observations', '')]
    worksheet = Table([[para(a), para(b)] for a, b in fields], colWidths=[220, 272], rowHeights=[44] * len(fields))
    worksheet.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d8ddda')), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(worksheet)
    document = SimpleDocTemplate(str(output / 'guide-atelier.pdf'), pagesize=A4,
                                 leftMargin=52, rightMargin=51, topMargin=42, bottomMargin=44,
                                 title=data['title'], author='PorscheParts')
    def footer(canvas, doc):
        canvas.setFont(regular_name, 8)
        canvas.setFillColor(muted)
        canvas.drawString(52, 24, 'PorscheParts / ' + data['revision'])
        canvas.drawRightString(A4[0] - 51, 24, str(doc.page))
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def build(description, output):
    data = copy.deepcopy(json.loads(description.read_text()))
    if len(data['stages']) != 6 or not data['inputs']:
        raise ValueError('The workshop guide needs its six stages and source choices')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'files').mkdir()
    assets = publish_files(data, output)
    serialized = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    document = TEMPLATE.read_text().replace('__WORKFLOW_DATA__', serialized)
    (output / 'index.html').write_text(document)
    make_pdf(data, output)
    manifest = {'description_sha256': digest(description), 'builder_sha256': digest(Path(__file__)),
                'template_sha256': digest(TEMPLATE), 'sources': assets,
                'outputs_sha256': {p.name: digest(p) for p in (output / 'index.html', output / 'guide-atelier.pdf')}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('description', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.description.resolve(), args.output.resolve())
    print(args.output.resolve() / 'index.html')
