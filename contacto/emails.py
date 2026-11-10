from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def enviar_correo_html(asunto, destinatario, plantilla, contexto=None, adjuntos=None):
    """
    Envía un correo HTML con el diseño de CanchaFácil.
    La plantilla debe extender 'emails/base_email.html'.

    adjuntos: lista de tuplas (nombre_archivo, contenido_en_bytes, mimetype),
              por ejemplo [('comprobante.pdf', pdf_bytes, 'application/pdf')].

    Devuelve (ok, error).
    """
    contexto = dict(contexto or {})
    contexto.setdefault('correo_contacto', getattr(settings, 'EMAIL_HOST_USER', ''))

    try:
        html = render_to_string(plantilla, contexto)
        email = EmailMultiAlternatives(
            subject=asunto,
            body=strip_tags(html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        email.attach_alternative(html, 'text/html')

        for nombre, contenido, mimetype in (adjuntos or []):
            email.attach(nombre, contenido, mimetype)

        email.send(fail_silently=False)
        return True, ''
    except Exception as e:
        return False, str(e)