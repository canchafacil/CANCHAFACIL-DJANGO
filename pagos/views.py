# pagos/views.py
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reservas.models import Reserva
from .utils import generar_factura_pdf


def descargar_factura(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    pdf_buffer = generar_factura_pdf(reserva_id)
    if pdf_buffer is None:
        return HttpResponse("Reserva no encontrada", status=404)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{reserva_id}.pdf"'
    return response