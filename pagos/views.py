# pagos/views.py
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reservas.models import Reserva
from .utils import generar_factura_pdf



def vista_pago(request):
    # Esta vista podría ser similar a la que ya tienes, pero mejor usar la de reservas
    # Si quieres mantenerla, asegúrate de pasar total
    reserva_id = request.session.get("reserva_pendiente_id")
    reserva = None
    total = 0
    if reserva_id:
        try:
            reserva = Reserva.objects.get(id=reserva_id)
            total = reserva.calcular_total()
        except Reserva.DoesNotExist:
            pass
    return render(request, 'pagos/pago.html', {'reserva': reserva, 'total': total})


def descargar_factura(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    pdf_buffer = generar_factura_pdf(reserva_id)
    if pdf_buffer is None:
        return HttpResponse("Reserva no encontrada", status=404)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{reserva_id}.pdf"'
    return response