from urllib import request
from django.shortcuts import render, redirect
from .models import Usuario
import random
from django.core.mail import send_mail
from django.conf import settings

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

def registro_admin(request):

    if request.method == 'POST':

        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        rol='ADMIN'

        if password != confirm_password:
            return render(
                request,
                'usuarios/registro_admin.html',
                {'error': 'Las contraseñas no coinciden'}
            )

        if Usuario.objects.filter(email=email).exists():
            return render(
            request,
            'usuarios/registro_admin.html',
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

    return render(request, 'usuarios/registro_admin.html')

def login_view(request):
    """Renderiza la pantalla de inicio de sesión."""
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

        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            usuario = Usuario.objects.get(
                email=email,
                password=password
            )

            if not usuario.activo:
                return render(
                    request,
                    'usuarios/login_admin.html',
                    {'error': 'Tu cuenta está deshabilitada. Contacta con el Superadministrador.'}
                )

            request.session['usuario_id'] = usuario.id
            request.session['rol'] = usuario.rol
            request.session['nombre'] = usuario.first_name

            if usuario.rol == 'SUPERADMIN':
                return redirect('lista_usuarios')

            elif usuario.rol == 'ADMIN':
                return redirect('panel_principal')

            else:
                return redirect('inicio')

        except Usuario.DoesNotExist:
            return render(
                request,
                'usuarios/login_admin.html',
                {'error': 'Correo o contraseña incorrectos'}
            )

    return render(request, 'usuarios/login_admin.html')

def lista_usuarios(request):

    if request.session.get('rol') != 'SUPERADMIN':
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

    if request.session.get('rol') != 'SUPERADMIN':
        return redirect('inicio')

    usuario = Usuario.objects.get(id=id)
    usuario.activo = False
    usuario.save()

    return redirect('lista_usuarios')

def habilitar_usuario(request, id):

    if request.session.get('rol') != 'SUPERADMIN':
        return redirect('inicio')

    usuario = Usuario.objects.get(id=id)
    usuario.activo = True
    usuario.save()

    return redirect('lista_usuarios')