from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .models import Usuario
from reservas.models import Reserva
from contacto.models import Resena
import random


def registro(request):

    if request.method == 'POST':

        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        rol='CLIENTE'

        if password != confirm_password:
            return render(
                request,
                'usuarios/registro.html',
                {'error': 'Las contraseñas no coinciden'}
            )

        if Usuario.objects.filter(email=email).exists():
            return render(
            request,
            'usuarios/registro.html',
            {'error': 'Este correo ya está registrado'}
    )

        Usuario.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=password,
            rol=rol
        )

        return redirect('login')

    return render(request, 'usuarios/registro.html')

def login_view(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario is None:
            return render(
                request,
                'usuarios/login.html',
                {
                    'error': 'El correo no está registrado.'
                }
            )

        if usuario.password != password:
            return render(
                request,
                'usuarios/login.html',
                {
                    'error': 'La contraseña es incorrecta.'
                }
            )

        if not usuario.activo:
            return render(
                request,
                'usuarios/login.html',
                {
                    'error': 'Tu cuenta está deshabilitada. Contacta con el Superadministrador.'
                }
            )

        request.session['usuario_id'] = usuario.id
        request.session['rol'] = usuario.rol
        request.session['nombre'] = usuario.first_name
        request.session['correo'] = usuario.email

        if usuario.rol == 'SUPERADMIN':
            return redirect('lista_usuarios')

        elif usuario.rol == 'ADMIN':
            return redirect('panel_principal')

        else:
            return redirect('inicio')
    return render(request, 'usuarios/login.html')

def recuperar_contra(request):

    if request.method == 'POST':

        email = request.POST.get('email')

        try:

            usuario = Usuario.objects.get(email=email)

            codigo = random.randint(100000,999999)

            request.session['codigo'] = codigo
            request.session['correo'] = email

            send_mail(
                'Recuperación de contraseña - CanchaFácil',
                f'''
Hola {usuario.first_name}

Tu código para recuperar la contraseña es:

{codigo}

No compartas este código con nadie.
                ''',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )

            return redirect('verificar_codigo')

        except Usuario.DoesNotExist:

            return render(
                request,
                'usuarios/recuperar_contra.html',
                {
                    'error':'No existe una cuenta con ese correo.'
                }
            )

    return render(
        request,
        'usuarios/recuperar_contra.html'
    )

def verificar_codigo(request):

    if request.method == 'POST':

        codigo_ingresado = request.POST.get('codigo')
        codigo_guardado = str(request.session.get('codigo'))

        if codigo_ingresado == codigo_guardado:
            return redirect('cambiar_contra')

        return render(
            request,
            'usuarios/verificar_codigo.html',
            {'error': 'Código incorrecto'}
        )

    return render(request, 'usuarios/verificar_codigo.html')

def cambiar_contra(request):

    email = request.session.get('correo')

    if not email:
        return redirect('login')

    usuario = Usuario.objects.get(email=email)

    if request.method == 'POST':

        password = request.POST.get('password')
        confirmar = request.POST.get('confirmar')

        if password != confirmar:

            return render(
                request,
                'usuarios/cambiar_contra.html',
                {
                    'error': 'Las contraseñas no coinciden'
                }
            )

        usuario.password = password
        usuario.save()

        request.session.pop('codigo', None)
        request.session.pop('correo', None)

        return redirect('login')

    return render(
        request,
        'usuarios/cambiar_contra.html'
    )

def login_admin(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario is None:
            return render(
                request,
                'usuarios/login_admin.html',
                {
                    'error': 'El correo no está registrado.'
                }
            )

        if usuario.password != password:
            return render(
                request,
                'usuarios/login_admin.html',
                {
                    'error': 'La contraseña es incorrecta.'
                }
            )

        if not usuario.activo:
            return render(
                request,
                'usuarios/login_admin.html',
                {
                    'error': 'Tu cuenta está deshabilitada. Contacta con el Superadministrador.'
                }
            )

        if usuario.rol not in ('ADMIN', 'SUPERADMIN'):
            return render(
                request,
                'usuarios/login_admin.html',
                {
                    'error': 'Esta cuenta no tiene permisos de administrador.'
                }
            )

        request.session['admin_id'] = usuario.id
        request.session['admin_rol'] = usuario.rol
        request.session['admin_nombre'] = usuario.first_name
        request.session['admin_correo'] = usuario.email

        if usuario.rol == 'SUPERADMIN':
            return redirect('lista_usuarios')

        return redirect('panel_principal')

    return render(request, 'usuarios/login_admin.html')

def logout_view(request):
    request.session.pop('usuario_id', None)
    request.session.pop('rol', None)
    request.session.pop('nombre', None)
    request.session.pop('correo', None)
    return redirect('inicio')

def logout_admin(request):
    request.session.pop('admin_id', None)
    request.session.pop('admin_rol', None)
    request.session.pop('admin_nombre', None)
    request.session.pop('admin_correo', None)
    return redirect('login_admin')

def lista_usuarios(request):

    if request.session.get('admin_rol') != 'SUPERADMIN':
        return redirect('inicio')

    usuarios = Usuario.objects.all()

    return render(
        request,
        'usuarios/lista_usuarios.html',
        {'usuarios': usuarios}
    )

def eliminar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)
    usuario.delete()

    return redirect('lista_usuarios')

def editar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)

    if request.method == 'POST':

        usuario.first_name = request.POST.get('first_name')
        usuario.last_name = request.POST.get('last_name')
        usuario.email = request.POST.get('email')
        usuario.phone = request.POST.get('phone')
        usuario.password = request.POST.get('password')
        usuario.rol = request.POST.get('rol')

        usuario.save()

        return redirect('lista_usuarios')

    return render(
        request,
        'usuarios/editar_usuarios.html',
        {'usuario': usuario}
    )

def deshabilitar_usuario(request, id):

    if request.session.get('admin_rol') != 'SUPERADMIN':
        return redirect('inicio')

    usuario = Usuario.objects.get(id=id)
    usuario.activo = False
    usuario.save()

    return redirect('lista_usuarios')

def habilitar_usuario(request, id):

    if request.session.get('admin_rol') != 'SUPERADMIN':
        return redirect('inicio')

    usuario = Usuario.objects.get(id=id)
    usuario.activo = True
    usuario.save()

    return redirect('lista_usuarios')


# ---------------------------------------------------------------------
# ÍCONOS DISPONIBLES PARA AVATAR
# ---------------------------------------------------------------------

ICONOS_JUGADORES = [
    {'nombre': 'Jugador 1', 'ruta': 'img/jugador1.jpg'},
    {'nombre': 'Jugador 2', 'ruta': 'img/jugador2.jpg'},
    {'nombre': 'Jugador 3', 'ruta': 'img/jugador3.jpg'},
    {'nombre': 'Jugador 4', 'ruta': 'img/jugador4.jpg'},
]

ICONOS_BANDERAS = [

    {'nombre': 'Colombia', 'ruta': 'img/colombia.jpg'},
    {'nombre': 'Argentina', 'ruta': 'img/argentina.jpg'},
    {'nombre': 'Brasil', 'ruta': 'img/brasil.jpg'},
]


# ---------------------------------------------------------------------
# PERFIL del usuario logueado
# ---------------------------------------------------------------------

def perfil(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    reservas = Reserva.objects.filter(correo=usuario.email).order_by('-fecha', '-hora')

    for r in reservas:
        r.sincronizar_estado()

    resenas = Resena.objects.filter(correo=usuario.email, archivada=False).order_by('-fecha')

    tiene_reserva_activa = reservas.filter(
        estado__in=[Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA]
    ).exists()

    return render(
        request,
        'usuarios/perfil.html',
        {
            'usuario': usuario,
            'reservas': reservas,
            'resenas': resenas,
            'tiene_reserva_activa': tiene_reserva_activa,
            'iconos_jugadores': ICONOS_JUGADORES,
            'iconos_banderas': ICONOS_BANDERAS,
            'motivos_cancelacion': Reserva.MOTIVOS_CANCELACION,
        }
    )


def editar_perfil(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        nuevo_email = request.POST.get('email', usuario.email).strip()

        if nuevo_email != usuario.email and Usuario.objects.filter(email=nuevo_email).exists():
            reservas = Reserva.objects.filter(correo=usuario.email).order_by('-fecha', '-hora')
            resenas = Resena.objects.filter(correo=usuario.email, archivada=False).order_by('-fecha')
            return render(
                request,
                'usuarios/perfil.html',
                {
                    'usuario': usuario,
                    'reservas': reservas,
                    'resenas': resenas,
                    'iconos_jugadores': ICONOS_JUGADORES,
                    'iconos_banderas': ICONOS_BANDERAS,
                    'motivos_cancelacion': Reserva.MOTIVOS_CANCELACION,
                    'error': 'Ese correo ya está en uso por otra cuenta',
                }
            )

        usuario.phone = request.POST.get('phone', usuario.phone).strip()
        usuario.email = nuevo_email

        nueva_password = request.POST.get('password', '').strip()
        if nueva_password:
            usuario.password = nueva_password

        if 'foto' in request.FILES:
            usuario.foto = request.FILES['foto']
            usuario.avatar_icono = None
        else:
            icono_elegido = request.POST.get('avatar_icono', '').strip()
            if icono_elegido:
                usuario.avatar_icono = icono_elegido
                usuario.foto = None

        usuario.save()

        request.session['nombre'] = usuario.first_name

        return redirect('perfil')

    return redirect('perfil')


# ---------------------------------------------------------------------
# CANCELACIÓN DE RESERVA (desde el perfil del usuario)
# ---------------------------------------------------------------------

@require_POST
def cancelar_reserva_perfil(request, reserva_id):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)
    reserva = get_object_or_404(Reserva, id=reserva_id, correo=usuario.email)

    if not reserva.puede_editarse:
        return render_error_perfil(request, usuario, 'Esta reserva ya no se puede cancelar.')

    motivo = request.POST.get('motivo_cancelacion', '').strip()
    detalle = request.POST.get('motivo_detalle', '').strip()
    motivos_validos = dict(Reserva.MOTIVOS_CANCELACION)

    if motivo not in motivos_validos:
        return render_error_perfil(request, usuario, 'Debes seleccionar un motivo válido de cancelación.')

    if motivo == 'otro' and len(detalle) < 10:
        return render_error_perfil(
            request, usuario,
            'Si eliges "Otro motivo", explica brevemente qué pasó (mínimo 10 caracteres).'
        )

    # Cancela: cambia el estado a 'cancelada', lo que libera automáticamente
    # las horas en cualquier consulta de disponibilidad que excluya ese estado.
    reserva.cancelar(motivo=motivo, detalle=detalle, por='usuario')

    _enviar_correo_cancelacion(reserva)

    return redirect('perfil')


def render_error_perfil(request, usuario, mensaje):
    reservas = Reserva.objects.filter(correo=usuario.email).order_by('-fecha', '-hora')
    resenas = Resena.objects.filter(correo=usuario.email, archivada=False).order_by('-fecha')
    tiene_reserva_activa = reservas.filter(
        estado__in=[Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_CONFIRMADA]
    ).exists()
    return render(
        request,
        'usuarios/perfil.html',
        {
            'usuario': usuario,
            'reservas': reservas,
            'resenas': resenas,
            'tiene_reserva_activa': tiene_reserva_activa,
            'iconos_jugadores': ICONOS_JUGADORES,
            'iconos_banderas': ICONOS_BANDERAS,
            'motivos_cancelacion': Reserva.MOTIVOS_CANCELACION,
            'error': mensaje,
        }
    )


def _enviar_correo_cancelacion(reserva):
    contexto = {
        'reserva': reserva,
        'motivo': reserva.motivo_legible,
        'detalle': reserva.motivo_detalle,
    }
    html = render_to_string('emails/cancelacion_reserva.html', contexto)
    texto = (
        f"Hola {reserva.nombre},\n\n"
        f"Tu reserva del {reserva.fecha} a las {reserva.hora} "
        f"en {reserva.cancha} fue CANCELADA.\n"
        f"Motivo: {reserva.motivo_legible}\n"
        f"{('Detalle: ' + reserva.motivo_detalle) if reserva.motivo_detalle else ''}\n\n"
        "Las horas quedaron disponibles nuevamente. — CanchaFácil"
    )
    msg = EmailMultiAlternatives(
        subject=f"Reserva cancelada — {reserva.cancha} ({reserva.fecha})",
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reserva.correo],
        bcc=[settings.DEFAULT_FROM_EMAIL],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)