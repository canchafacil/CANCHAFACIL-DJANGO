from io import BytesIO
from datetime import datetime

from django.http import HttpResponse
from django.db.models import Sum, Count
from django.utils import timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

from reservas.models import Reserva

VERDE = colors.HexColor('#62ff00')
NEGRO = colors.HexColor('#0a0a0a')
GRIS = colors.HexColor('#1a1a1a')

ESTADOS_PAGADOS = [Reserva.ESTADO_CONFIRMADA, Reserva.ESTADO_COMPLETADA]


def _estilos():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TituloCancha', fontSize=22, textColor=NEGRO,
        fontName='Helvetica-Bold', spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='Subtitulo', fontSize=11, textColor=colors.grey,
        fontName='Helvetica', spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name='SeccionTitulo', fontSize=14, textColor=NEGRO,
        fontName='Helvetica-Bold', spaceBefore=18, spaceAfter=10,
    ))
    return styles


def _encabezado(styles, subtitulo):
    fecha_generacion = timezone.localtime().strftime('%d/%m/%Y %H:%M')
    elementos = [
        Paragraph('CanchaFácil', styles['TituloCancha']),
        Paragraph(subtitulo, styles['Subtitulo']),
        Paragraph(f'Generado el {fecha_generacion}', styles['Subtitulo']),
    ]
    return elementos


def _tabla_resumen(filas, col_widths=None):
    """Tabla simple de dos columnas: etiqueta / valor."""
    tabla = Table(filas, colWidths=col_widths or [8 * cm, 8 * cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GRIS),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return tabla


def generar_reporte_general(request):
    """
    Reporte histórico completo: desde que existe la primera reserva
    hasta hoy. Ingresos totales, estados, cancha más popular, cliente
    frecuente, e ingresos mes a mes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = _estilos()
    story = []

    primera_reserva = Reserva.objects.order_by('fecha').first()
    fecha_inicio = primera_reserva.fecha.strftime('%d/%m/%Y') if primera_reserva else '—'

    story += _encabezado(styles, f'Reporte General de Ingresos — Histórico desde {fecha_inicio}')
    story.append(Spacer(1, 10))

    # ── Resumen general ──────────────────────────────────────────
    todas = Reserva.objects.all()
    pagadas = todas.filter(estado__in=ESTADOS_PAGADOS)
    total_historico = pagadas.aggregate(total=Sum('monto_pagado'))['total'] or 0

    conteo_estados = todas.values('estado').annotate(total=Count('id'))
    mapa_estados = {c['estado']: c['total'] for c in conteo_estados}

    story.append(Paragraph('Resumen General', styles['SeccionTitulo']))
    story.append(_tabla_resumen([
        ['Indicador', 'Valor'],
        ['Ingresos totales históricos', f"${total_historico:,.0f}".replace(',', '.')],
        ['Total de reservas registradas', str(todas.count())],
        ['Reservas confirmadas', str(mapa_estados.get(Reserva.ESTADO_CONFIRMADA, 0))],
        ['Reservas completadas', str(mapa_estados.get(Reserva.ESTADO_COMPLETADA, 0))],
        ['Reservas pendientes', str(mapa_estados.get(Reserva.ESTADO_PENDIENTE, 0))],
        ['Reservas canceladas', str(mapa_estados.get(Reserva.ESTADO_CANCELADA, 0))],
    ]))

    # ── Cancha más reservada / cliente frecuente ────────────────
    top_cancha = (
        todas.exclude(estado=Reserva.ESTADO_CANCELADA)
        .values('cancha').annotate(total=Count('id')).order_by('-total').first()
    )
    top_cliente = (
        todas.exclude(estado=Reserva.ESTADO_CANCELADA)
        .values('nombre').annotate(total=Count('id')).order_by('-total').first()
    )

    story.append(Paragraph('Destacados', styles['SeccionTitulo']))
    story.append(_tabla_resumen([
        ['Indicador', 'Valor'],
        ['Cancha más reservada', f"{top_cancha['cancha']} ({top_cancha['total']} reservas)" if top_cancha else '—'],
        ['Cliente más frecuente', f"{top_cliente['nombre']} ({top_cliente['total']} reservas)" if top_cliente else '—'],
    ]))

    # ── Ingresos por mes (histórico completo) ────────────────────
    story.append(Paragraph('Ingresos por Mes', styles['SeccionTitulo']))

    ingresos_por_mes = {}
    for r in pagadas:
        clave = r.fecha.strftime('%Y-%m')
        ingresos_por_mes[clave] = ingresos_por_mes.get(clave, 0) + float(r.monto_pagado)

    filas_mes = [['Mes', 'Ingresos']]
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    for clave in sorted(ingresos_por_mes.keys()):
        anio, mes = clave.split('-')
        nombre_mes = meses_es[int(mes) - 1]
        filas_mes.append([f'{nombre_mes} {anio}', f"${ingresos_por_mes[clave]:,.0f}".replace(',', '.')])

    if len(filas_mes) > 1:
        story.append(_tabla_resumen(filas_mes))
    else:
        story.append(Paragraph('No hay ingresos registrados todavía.', styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    nombre_archivo = f"reporte_general_canchafacil_{timezone.localdate().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


def generar_reporte_mes_actual(request):
    """
    Reporte del mes en curso: mismas cifras que se ven en el tab
    'Reporte de Ingresos', más el detalle de transacciones.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = _estilos()
    story = []

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    nombre_mes_actual = f'{meses_es[hoy.month - 1]} {hoy.year}'

    story += _encabezado(styles, f'Reporte de Ingresos — {nombre_mes_actual}')
    story.append(Spacer(1, 10))

    reservas_mes = Reserva.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy,
        estado__in=ESTADOS_PAGADOS,
    )
    total_mes = reservas_mes.aggregate(total=Sum('monto_pagado'))['total'] or 0
    cantidad = reservas_mes.count()
    dias_transcurridos = hoy.day
    promedio_diario = round(total_mes / dias_transcurridos) if dias_transcurridos else 0

    story.append(Paragraph('Resumen del Mes', styles['SeccionTitulo']))
    story.append(_tabla_resumen([
        ['Indicador', 'Valor'],
        ['Total del mes', f"${total_mes:,.0f}".replace(',', '.')],
        ['Reservas pagadas', str(cantidad)],
        ['Promedio diario', f"${promedio_diario:,.0f}".replace(',', '.')],
    ]))

    # ── Detalle de transacciones del mes ─────────────────────────
    story.append(Paragraph('Detalle de Transacciones', styles['SeccionTitulo']))

    transacciones = Reserva.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=hoy,
    ).order_by('-fecha', '-hora')

    filas = [['Fecha', 'Cliente', 'Cancha', 'Total', 'Estado']]
    for t in transacciones:
        filas.append([
            t.fecha.strftime('%d/%m'),
            t.nombre[:20],
            t.cancha,
            f"${t.monto_pagado:,.0f}".replace(',', '.'),
            t.get_estado_display(),
        ])

    if len(filas) > 1:
        tabla = Table(filas, colWidths=[2.2 * cm, 4.5 * cm, 3.3 * cm, 3 * cm, 3 * cm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRIS),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(tabla)
    else:
        story.append(Paragraph('No hay transacciones registradas este mes.', styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    nombre_archivo = f"reporte_mensual_canchafacil_{hoy.strftime('%Y%m')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response