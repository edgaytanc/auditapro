# Archivo: users/views.py

from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_func, login as login_func
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from .const import USER_ERROR_INSTANCES, USER_CLIENT_FIELDS
from .services import create_user as create_user_func, delete_user as delete_user_func, update_user as update_user_func
from mfa.utils import send_2fa_code

User = get_user_model()

def login(req):
    if req.method == "GET":
        return login_page(req)
    elif req.method == "POST":
        return login_user(req)

def signup(req):
    if req.method == "GET":
        return signup_page(req)
    elif req.method == "POST":
        return create_user(req)

def create_user(req):
    
    username = req.POST.get("username")
    first_name = req.POST.get("first_name")
    last_name = req.POST.get("last_name")
    email = req.POST.get("email")
    password_1 = req.POST.get("password_1")
    password_2 = req.POST.get("password_2")
    try:
        create_user_func(username, first_name, last_name, email, password_1, password_2)
        user = authenticate(email=email, password=password_1)
        login_func(req, user)
        messages.success(req, "Usuario creado y autenticado exitosamente.")
        return redirect("user")
    except ValueError as e:
        messages.error(req, "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.")
        return signup_page(req)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(req, "Ocurrió un error inesperado, por favor inténtelo de nuevo.")
        return signup_page(req)

def login_user(req):
    email = req.POST.get("email")
    password = req.POST.get("password")
    if not email or not password:
        messages.error(req, "Por favor, ingrese el correo y la contraseña.")
        return login_page(req)
    user = authenticate(request=req, email=email, password=password)
    if user is not None:
        if user.is_superuser:
            login_func(req, user)
            messages.success(req, f"Bienvenido de nuevo, {user.get_full_name() or user.username}.")
            # Si el usuario tiene rol superadmin, enviarlo al dashboard de gestión de usuarios
            if getattr(user, 'role', None) and user.role and user.role.name == 'superadmin':
                return redirect("superadmin_dashboard")
            # Para otros superusuarios, llevar al dashboard general
            return redirect("dashboard")
        else:
            send_2fa_code(user)
            req.session['pre_2fa_user_id'] = user.id
            return redirect("verify_2fa")
    else:
        messages.error(req, "Correo electrónico o contraseña incorrectos.")
        return login_page(req)


@login_required
def logout(req):
    logout_func(req)
    messages.success(req, "Sesión cerrada correctamente.")
    return redirect("home")

@login_required
def edit_user(req, field):
    value = req.POST.get("value")
    try:
        update_user_func(req, value, field)
        messages.success(req, "El campo se ha actualizado correctamente.")
        return redirect("user")
    except ValueError as e:
        messages.error(req, "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.")
        return redirect("user")
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("user")
        else:
            messages.error(req, "Ocurrió un error inesperado, por favor inténtelo de nuevo.")
            return redirect("user")

@login_required
def delete_account(req):
    email = req.POST.get("email")
    password = req.POST.get("password")
    try:
        delete_user_func(req, email, password)
        messages.success(req, "Cuenta eliminada correctamente.")
        return redirect("home")
    except ValueError as e:
        messages.error(req, "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.")
        return user_page(req)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(req, "Ocurrió un error inesperado, por favor inténtelo de nuevo.")
        return redirect("user")

def index_page(req: HttpRequest):
    if req.user.is_authenticated:
        # Si el usuario autenticado es superadmin por rol, redirigir a su dashboard específico
        if getattr(req.user, 'role', None) and req.user.role and req.user.role.name == 'superadmin':
            return redirect('superadmin_dashboard')
        return render(req, "users/index-system.html")
    else:
        return render(req, "common/home.html")

def login_page(req):
    if req.user.is_authenticated:
        return redirect('dashboard')
    return render(req, "users/login.html", {})

def signup_page(req):
    return render(req, "users/signup.html", {})

@login_required
def user_page(req):
    if req.user.role and req.user.role.name == 'superadmin':
        return redirect('superadmin_dashboard')
    data = { "user_fields": USER_CLIENT_FIELDS }
    return render(req, "users/user.html", data)

@login_required
def dashboard(req):
    if req.user.role and req.user.role.name == 'superadmin':
        return redirect('superadmin_dashboard')
    return render(req, "users/dashboard.html", {})

def demo_signup_page(req):
    storage = messages.get_messages(req)
    storage.used = True
    return render(req, "users/demo_signup.html")

def demo_signup(req):
    if req.method == "GET":
        return demo_signup_page(req)
    
    username = req.POST.get("username")
    first_name = req.POST.get("first_name")
    last_name = req.POST.get("last_name")
    email = req.POST.get("email")
    password = req.POST.get("password")
    password_confirm = req.POST.get("password_confirm")
    
    if password != password_confirm:
        messages.error(req, "Las contraseñas no coinciden.")
        return redirect("demo_signup")
    
    if User.objects.filter(username=username).exists():
        messages.error(req, "El nombre de usuario ya está en uso.")
        return redirect("demo_signup")
    
    if User.objects.filter(email=email).exists():
        messages.error(req, "El correo electrónico ya está registrado.")
        return redirect("demo_signup")
    
    try:
        from .models import Roles
        admin_role, created = Roles.objects.get_or_create(
            name="audit_manager", 
            defaults={"verbose_name": "Audit Manager"}
        )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=admin_role,
            modalidad='I',
            plan='DEMO',
        )
        
        user = authenticate(email=email, password=password)
        if user:
            login_func(req, user)
            messages.success(req, "¡Bienvenido a AuditaPro! Tu cuenta ha sido creada con éxito.")
            return redirect("dashboard")
        else:
            messages.error(req, "Error al autenticar el usuario.")
            return redirect("login")
            
    except Exception as e:
        messages.error(req, f"Error al crear el usuario: {str(e)}")
        return redirect("demo_signup")