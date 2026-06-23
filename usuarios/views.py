from django.shortcuts import render

def login_view(request):
    return render(request, 'usuarios/login.html')

def registro(request):
    return render(request, 'usuarios/registro.html')

def inicioadmi(request):
    return render(request, 'auth_admin/login_admin.html')
