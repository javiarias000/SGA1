import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from classes.models import CalificacionParcial
from subjects.models import Subject


def generar_boletin_pdf(student, quimestre='Q1'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('titulo', parent=styles['Title'], fontSize=16, alignment=TA_CENTER)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER)
    label_style = ParagraphStyle('label', parent=styles['Normal'], fontSize=9, textColor=colors.gray)

    story = []

    # Encabezado
    story.append(Paragraph('Conservatorio Bolívar de Ambato', titulo_style))
    story.append(Paragraph('Boletín de Calificaciones', sub_style))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(f'Quimestre: {quimestre}', sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f'Estudiante: <b>{student.name}</b>', styles['Normal']))
    if student.grade_level:
        story.append(Paragraph(f'Nivel: {student.grade_level}', label_style))
    story.append(Spacer(1, 0.5*cm))

    # Tabla de calificaciones
    cals = CalificacionParcial.objects.filter(
        student=student, quimestre=quimestre
    ).select_related('subject', 'tipo_aporte').order_by('subject__name', 'parcial')

    materias = {}
    for c in cals:
        materias.setdefault(c.subject.name, {})[c.parcial] = float(c.calificacion)

    parciales = ['1P', '2P', '3P', '4P']
    header = ['Materia'] + parciales + ['Promedio']
    data = [header]
    for mat, notas in sorted(materias.items()):
        row = [mat]
        vals = []
        for p in parciales:
            v = notas.get(p)
            row.append(f'{v:.2f}' if v is not None else '—')
            if v is not None:
                vals.append(v)
        prom = f'{sum(vals)/len(vals):.2f}' if vals else '—'
        row.append(prom)
        data.append(row)

    if len(data) > 1:
        col_widths = [6*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4338ca')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f6f8')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(Paragraph('Sin calificaciones registradas para este quimestre.', styles['Normal']))

    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph('____________________________', label_style))
    story.append(Paragraph('Firma Docente / Secretaría', label_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
