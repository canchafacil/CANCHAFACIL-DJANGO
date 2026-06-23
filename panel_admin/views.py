from django.shortcuts import render, redirect
from usuarios.models import Usuario
from canchas.models import Cancha
from contacto.models import Resena


def registro_admin(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'auth_admin/registro_admin.html', {'error': 'Las contraseñas no coinciden'})
        if Usuario.objects.filter(email=email).exists():
            return render(request, 'auth_admin/registro_admin.html', {'error': 'Este correo ya está registrado'})

        Usuario.objects.create(
            first_name=first_name, last_name=last_name, email=email,
            phone=phone, password=password, rol='ADMIN'
        )
        return redirect('login_admin')

    return render(request, 'auth_admin/registro_admin.html')


def login_admin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            usuario = Usuario.objects.get(email=email, password=password)
            if usuario.rol == 'ADMIN':
                return redirect('panel_principal')
            return redirect('inicio')
        except Usuario.DoesNotExist:
            return render(request, 'auth_admin/login_admin.html', {'error': 'Correo o contraseña incorrectos'})
    return render(request, 'auth_admin/login_admin.html')


def panel_principal(request):
    return render(request, 'panel/panel_base.html', {
        'canchas': Cancha.objects.all(),
        'resenas_activas': Resena.objects.filter(archivada=False).order_by('-fecha'),
        'resenas_archivadas': Resena.objects.filter(archivada=True).order_by('-fecha'),
    })


def lista_usuarios(request):
    return render(request, 'auth_admin/lista_usuarios.html', {
        'usuarios': Usuario.objects.all()
    })


def eliminar_usuario(request, id):
    Usuario.objects.get(id=id).delete()
    return redirect('lista_usuarios')


def editar_usuario(request, id):
    usuario = Usuario.objects.get(id=id)
    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name')
        usuario.email = request.POST.get('email')
        usuario.phone = request.POST.get('phone')
        usuario.password = request.POST.get('password')
        usuario.save()
        return redirect('lista_usuarios')
    return render(request, 'auth_admin/editar_usuarios.html', {'usuario': usuario})