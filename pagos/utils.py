import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from reservas.models import Reserva

# ========== DATOS DE LA EMPRESA ==========
EMPRESA = {
    'nombre': getattr(settings, 'EMPRESA_NOMBRE', 'CanchaFácil'),
    'nit': getattr(settings, 'EMPRESA_NIT', '900.123.456-7'),
    'direccion': getattr(settings, 'EMPRESA_DIRECCION', 'Calle Falsa 123, Bogotá'),
    'telefono': getattr(settings, 'EMPRESA_TELEFONO', '+57 300 123 4567'),
    'correo': getattr(settings, 'EMPRESA_CORREO', 'info@canchafacil.com'),
    'logo': getattr(settings, 'EMPRESA_LOGO', 'img/logo-green.png'),
}

# ========== COLORES ==========
COLOR_VERDE_OSCURO = colors.HexColor('#1B5E20')
COLOR_VERDE_CLARO = colors.HexColor('#E8F5E9')
COLOR_BLANCO = colors.white
COLOR_NEGRO = colors.black


def encontrar_logo():
    """Busca el archivo del logo en varias ubicaciones posibles."""
    logo_relativo = EMPRESA['logo']

    if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
        ruta = os.path.join(settings.STATIC_ROOT, logo_relativo)
        if os.path.exists(ruta):
            return ruta

    if hasattr(settings, 'STATICFILES_DIRS'):
        for static_dir in settings.STATICFILES_DIRS:
            ruta = os.path.join(static_dir, logo_relativo)
            if os.path.exists(ruta):
                return ruta

    base_dir = getattr(settings, 'BASE_DIR', None)
    if base_dir:
        ruta = os.path.join(base_dir, 'static', logo_relativo)
        if os.path.exists(ruta):
            return ruta

    app_dir = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(app_dir, 'static', logo_relativo)
    if os.path.exists(ruta):
        return ruta

    return None


def generar_factura_pdf(reserva_id):
    """
    Genera un PDF de factura para la reserva con ID reserva_id.
    Sin IVA. Usa SIEMPRE los datos reales guardados en la reserva
    (precio_por_hora vía el modelo Cancha, horas reservadas, método
    de pago, tipo de pago y saldo) en vez de recalcularlos con
    valores hardcodeados, para que la factura nunca se desincronice
    de lo que realmente se cobró.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    try:
        reserva = Reserva.objects.get(id=reserva_id)
    except Reserva.DoesNotExist:
        return None

    # ========== CÁLCULOS (SIN IVA) ==========
    # Precio por hora real, consultado desde el modelo Cancha (misma
    # fuente que usa el formulario de reservas y el cálculo del total).
    precio_hora = Decimal(reserva.precio_por_hora())

    horas_reservadas = reserva.get_horas()  # ej. ["18:00", "19:00", "20:00"]
    cantidad_horas = len(horas_reservadas) if horas_reservadas else Decimal(reserva.duracion_minutos()) / 60

    # Si ya hay un precio_total guardado en la reserva (lo que realmente
    # se cobró), usarlo. Si no, calcularlo con la misma lógica del modelo.
    total = reserva.precio_total if reserva.precio_total else reserva.calcular_total()

    # Reusa el número de factura ya guardado en la reserva si existe;
    # solo genera uno nuevo como respaldo si nunca se asignó.
    if reserva.numero_factura:
        num_factura = reserva.numero_factura
    else:
        anio = reserva.fecha.strftime('%Y')
        mes = reserva.fecha.strftime('%m')
        num_factura = f"FAC-{anio}-{mes}-{reserva.id:04d}"

    metodo_pago_texto = reserva.metodo_pago or "No especificado"
    estado_texto = reserva.get_estado_display()

    # ========== ESTILOS ==========
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=COLOR_VERDE_OSCURO,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    estilo_normal = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_NEGRO,
    )
    estilo_negrita = ParagraphStyle(
        'Negrita',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_NEGRO,
        fontName='Helvetica-Bold',
    )
    estilo_encabezado_tabla = ParagraphStyle(
        'EncabezadoTabla',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_BLANCO,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )
    estilo_celda_tabla = ParagraphStyle(
        'CeldaTabla',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_NEGRO,
        alignment=TA_CENTER,
    )
    estilo_total = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLOR_VERDE_OSCURO,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
    )

    # ========== ELEMENTOS DEL PDF ==========
    elementos = []

    # ----- ENCABEZADO (logo + datos empresa) -----
    logo_path = encontrar_logo()

    if logo_path and os.path.exists(logo_path):
        logo = Image(logo_path, width=1.2 * inch, height=1.2 * inch)
    else:
        logo = Paragraph("CanchaFácil", estilo_titulo)

    datos_empresa = [
        [Paragraph(f"<b>{EMPRESA['nombre']}</b>", estilo_negrita)],
        [Paragraph(f"NIT: {EMPRESA['nit']}", estilo_normal)],
        [Paragraph(f"Dirección: {EMPRESA['direccion']}", estilo_normal)],
        [Paragraph(f"Tel: {EMPRESA['telefono']}", estilo_normal)],
        [Paragraph(f"Email: {EMPRESA['correo']}", estilo_normal)],
    ]
    tabla_empresa = Table(datos_empresa, colWidths=[3 * inch])
    tabla_empresa.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    encabezado = Table([[logo, tabla_empresa]], colWidths=[1.5 * inch, 4.5 * inch])
    encabezado.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(encabezado)
    elementos.append(Spacer(1, 0.2 * inch))

    # ----- TÍTULO -----
    elementos.append(Paragraph("FACTURA DE RESERVA", estilo_titulo))
    elementos.append(Spacer(1, 0.1 * inch))

    # ----- DATOS DE LA FACTURA -----
    datos_factura = [
        [Paragraph("<b>Número de factura:</b>", estilo_negrita), Paragraph(num_factura, estilo_normal)],
        [Paragraph("<b>Fecha de emisión:</b>", estilo_negrita), Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), estilo_normal)],
        [Paragraph("<b>Estado:</b>", estilo_negrita), Paragraph(estado_texto, estilo_normal)],
        [Paragraph("<b>Método de pago:</b>", estilo_negrita), Paragraph(metodo_pago_texto, estilo_normal)],
    ]
    tabla_datos = Table(datos_factura, colWidths=[1.5 * inch, 4 * inch])
    tabla_datos.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 0.2 * inch))

    # ----- DATOS DEL CLIENTE -----
    datos_cliente = [
        [Paragraph("<b>Cliente:</b>", estilo_negrita), Paragraph(reserva.nombre, estilo_normal)],
        [Paragraph("<b>Correo:</b>", estilo_negrita), Paragraph(reserva.correo, estilo_normal)],
        [Paragraph("<b>Teléfono:</b>", estilo_negrita), Paragraph(reserva.telefono or "No registrado", estilo_normal)],
    ]
    tabla_cliente = Table(datos_cliente, colWidths=[1.5 * inch, 4 * inch])
    tabla_cliente.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_cliente)
    elementos.append(Spacer(1, 0.2 * inch))

    # ----- DETALLE DE LA RESERVA (TABLA) -----
    # Muestra TODAS las horas reservadas (no solo la primera), tal como
    # las guarda reserva.horas / reserva.get_horas().
    horas_texto = ", ".join(horas_reservadas) if horas_reservadas else reserva.hora.strftime('%I:%M %p')

    data_tabla = [
        [
            Paragraph("<b>Cancha</b>", estilo_encabezado_tabla),
            Paragraph("<b>Fecha</b>", estilo_encabezado_tabla),
            Paragraph("<b>Horas</b>", estilo_encabezado_tabla),
            Paragraph("<b>Duración</b>", estilo_encabezado_tabla),
            Paragraph("<b>Precio/hora</b>", estilo_encabezado_tabla),
            Paragraph("<b>Total</b>", estilo_encabezado_tabla),
        ],
        [
            Paragraph(reserva.cancha, estilo_celda_tabla),
            Paragraph(reserva.fecha.strftime("%d/%m/%Y"), estilo_celda_tabla),
            Paragraph(horas_texto, estilo_celda_tabla),
            Paragraph(f"{cantidad_horas} h", estilo_celda_tabla),
            Paragraph(f"${precio_hora:,.0f}", estilo_celda_tabla),
            Paragraph(f"${total:,.0f}", estilo_celda_tabla),
        ]
    ]

    tabla_detalle = Table(data_tabla, colWidths=[1.6 * inch, 1.1 * inch, 1.3 * inch, 0.9 * inch, 1.1 * inch, 1.2 * inch])
    tabla_detalle.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_OSCURO),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_BLANCO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_VERDE_CLARO),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_detalle)
    elementos.append(Spacer(1, 0.2 * inch))

    # ----- RESUMEN DE PAGO (SIN IVA) -----
    # Si la reserva se pagó con abono (50%), lo refleja en vez de mostrar
    # el total como si ya estuviera todo pagado.
    resumen_data = [
        [Paragraph("<b>Total de la reserva</b>", estilo_negrita), Paragraph(f"${total:,.0f}", estilo_normal)],
    ]

    if reserva.tipo_pago == reserva.TIPO_PAGO_ABONO:
        resumen_data.append([
            Paragraph("<b>Abono pagado (50%)</b>", estilo_negrita),
            Paragraph(f"${reserva.monto_pagado:,.0f}", estilo_normal),
        ])
        resumen_data.append([
            Paragraph("<b>Saldo pendiente</b>", estilo_negrita),
            Paragraph(f"${reserva.saldo_pendiente:,.0f}", estilo_normal),
        ])
    else:
        resumen_data.append([
            Paragraph("<b>Monto pagado</b>", estilo_negrita),
            Paragraph(f"${reserva.monto_pagado:,.0f}", estilo_normal),
        ])

    resumen_data.append([
        Paragraph("<b>TOTAL A PAGAR</b>", estilo_total),
        Paragraph(f"${total:,.0f}", estilo_total),
    ])

    tabla_resumen = Table(resumen_data, colWidths=[4 * inch, 2 * inch])
    tabla_resumen.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (1, -1), COLOR_VERDE_CLARO),
    ]))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 0.3 * inch))

    # ----- PIE DE PÁGINA -----
    elementos.append(Paragraph("Gracias por reservar con CanchaFácil.", estilo_normal))
    elementos.append(Spacer(1, 0.1 * inch))
    elementos.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_normal))

    # ----- FOOTER (número de página) -----
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(0.75 * inch, 0.5 * inch, f"Página {doc.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer