# Archivo: users/views.py

from django.http import HttpRequest, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_func, login as login_func
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Roles
from django.contrib.auth.hashers import make_password
from user_management.decorators import admin_or_superadmin_required 
from django import forms
from django.utils.crypto import get_random_string
import random
import string
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import login as auth_login
from users.emails import send_admin_notification_email

from .const import USER_ERROR_INSTANCES, USER_CLIENT_FIELDS
from .services import create_user as create_user_func, delete_user as delete_user_func, update_user as update_user_func
from mfa.utils import send_2fa_code
from django.contrib.auth.decorators import user_passes_test
from .models import RegistroInvitacion
from users.emails import send_autoregistro_email
from datetime import timedelta
import uuid
from django.utils import timezone
import logging
from users.emails.autoregistro_email import (
    send_autoregistro_email,
    send_autoregistro_admin_notification,
    send_autoregistro_success_admin_notification,
)


User = get_user_model()
logger = logging.getLogger(__name__)

#  NUEVO: Función auxiliar para validar permisos

def socio_o_superadmin(user):
    """
    Permite acceso solo a:
    - Superadmin (user.is_superuser == True)
    - Jefe de auditoría con 'socio' = True
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if getattr(user, "role", None) and user.role.name == "audit_manager" and getattr(user, "socio", False):
        return True
    return False


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
    storage = messages.get_messages(req)
    for _ in storage:
        pass
    storage.used = True
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
            messages.error(req, "Ocurrió un error inesperado, por favor, inténtelo de nuevo.")
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
            messages.error(req, "Ocurrió un error inesperado, por favor, inténtelo de nuevo.")
        return redirect("user")

def index_page(req: HttpRequest):
    if req.user.is_authenticated:
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
    data = {"user_fields": USER_CLIENT_FIELDS}
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

def login_audit_manager(request):
    """
    Login exclusivo para socios (jefes de auditoría con 'socio' activado). 
    Si el usuario autenticado tiene rol válido, lo manda al formulario de alta.
    """
    if request.user.is_authenticated:
        r = getattr(request.user, 'role', None)

        # ✅ Solo permitir socios o superadmin
        if r and (
            (r.name == 'audit_manager' and getattr(request.user, 'socio', False))
            or r.name == 'superadmin'
        ):
            return redirect('partner_create_user')

        messages.error(request, "No tienes permisos para esta sección.")
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request=request, email=email, password=password)
        if not user:
            messages.error(request, "Credenciales inválidas.")
            return render(request, "users/login_audit_manager.html")

        r = getattr(user, 'role', None)

        # ✅ Solo permitir jefes de auditoría con socio=True o superadmin
        if not (
            r and (
                (r.name == 'audit_manager' and getattr(user, 'socio', False))
                or r.name == 'superadmin'
            )
        ):
            messages.error(request, "No tienes permisos para esta sección.")
            return render(request, "users/login_audit_manager.html")

        login_func(request, user)
        return redirect('partner_create_user')

    return render(request, "users/login_audit_manager.html")



class PartnerUserForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label="Nombre",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellido",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    role = forms.ModelChoiceField(
        queryset=Roles.objects.filter(name__in=["audit_manager"]),
        label="Rol",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    plan = forms.ChoiceField(
        choices=[('A', 'Anual')],
        label="Plan",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    modalidad = forms.ChoiceField(
        choices=[('I', 'Individual')],
        label="Modalidad",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 🔍 Validación adicional
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        from users.models import User
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("El usuario con este correo ya existe.")
        return email


@login_required
@user_passes_test(socio_o_superadmin)
@login_required
@user_passes_test(socio_o_superadmin)
def partner_create_user(request):
    """
    Formulario para que socios creen usuarios (auditor o audit_manager).
    Envía un correo de activación liviano al nuevo usuario.
    """
    if not socio_o_superadmin(request.user):
        messages.error(request, "No tienes permisos para crear usuarios.")
        return redirect("dashboard")

    if request.method == "POST":
        form = PartnerUserForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            random_password = get_random_string(
                length=8, allowed_chars=string.ascii_letters + string.digits
            )

            try:
                # 🔥🔥🔥 VALIDACIÓN DE CUPOS
                if request.user.modalidad == "G":
                    actuales = request.user.auditores.filter(is_deleted=False).count()
                    limite = request.user.auditor_slots or 3

                    if actuales >= limite:
                        messages.error(
                            request,
                            f"Has alcanzado el límite de {limite} auditores para tu plan."
                        )
                        return redirect("partner_create_user")

                user = User(
                    username=cd['email'],
                    first_name=cd['first_name'],
                    last_name=cd['last_name'],
                    email=cd['email'],
                    password=make_password(random_password),
                    role=cd['role'],
                    modalidad=cd['modalidad'],
                    plan=cd['plan'],
                )

                # Registrar quién creó el usuario
                if hasattr(request.user, "id"):
                    user.created_by_id = request.user.id

                # Si es auditor grupal, asignar administrador
                if (
                    cd['role'].name == 'auditor'
                    and cd['modalidad'] == 'G'
                    and hasattr(request.user, 'is_admin')
                    and request.user.is_admin()
                ):
                    user.administrador = request.user

                user.save()

                # ✅ Import local
                from users.emails.user_welcome_email import send_activation_email_light

                send_activation_email_light(user, random_password)

                # Notificación interna
                if getattr(request.user, "socio", False):
                    send_admin_notification_email(request.user, user)

                messages.success(
                    request,
                    f"Usuario creado correctamente. Se envió un correo de activación a {user.email}."
                )
                return redirect("partner_create_user")

            except Exception as e:
                messages.error(request, f"Ocurrió un error al crear el usuario: {e}")
        else:
            error_messages = " ".join(
                [str(e) for errs in form.errors.values() for e in errs]
            )
            messages.error(
                request,
                error_messages or "No se pudo crear el usuario. Verifica los datos ingresados."
            )
    else:
        form = PartnerUserForm()

    return render(request, "users/partner_create_user.html", {"form": form})




def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, " Su cuenta ha sido activada exitosamente. Inicie sesión con su correo y contraseña.")
        return redirect("login")
    else:
        messages.error(request, " El enlace de activación no es válido o ha expirado.")
        return redirect("login")


class SocioAutoRegistroForm(forms.Form):
    email = forms.EmailField(
        label="Correo de la persona",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "correo@ejemplo.com",
        })
    )


@login_required
def socio_autoregistro(request):
    """
    Pantalla donde el socio escribe el correo del cliente
    para enviarle un enlace único de autoregistro.
    """
    # Solo socios (y si quieres, superadmin) pueden usar esto
    if not (getattr(request.user, "socio", False) or request.user.is_superuser):
        raise Http404("Página no encontrada")

    if request.method == "POST":
        form = SocioAutoRegistroForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            # 1) Si ya existe un usuario con ese correo, no tiene sentido invitarlo
            if User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "Ya existe un usuario registrado con ese correo. No se envió invitación."
                )
                return redirect("socio_autoregistro")

            # 2) Invalidar invitaciones anteriores NO usadas para ese correo
            RegistroInvitacion.objects.filter(
                email__iexact=email,
                usado=False,
            ).update(usado=True, usado_en=timezone.now())

            # 3) Crear token único y registro de invitación
            token = uuid.uuid4().hex
            invitacion = RegistroInvitacion.objects.create(
                email=email,
                token=token,
                socio=request.user,   # el socio que invita
                usado=False,          # por si el default cambia en el futuro
            )

            # 4) Enviar el correo con el enlace + notificar al dueño (admin)
            try:
                send_autoregistro_email(invitacion, request)

                # ✅ Notificación informativa al dueño/administrador
                try:
                    send_autoregistro_admin_notification(invitacion)
                except Exception as e:
                    logger.error(
                        f"[AUTOREGISTRO] Error notificando al dueño: {e}",
                        exc_info=True
                    )

                messages.success(
                    request,
                    f"Se ha enviado un enlace de autoregistro a {email}."
                )
            except Exception as e:
                messages.error(
                    request,
                    "Ocurrió un error al enviar el correo de invitación. Intenta de nuevo."
                )
                logger.error(f"[AUTOREGISTRO] Error enviando correo: {e}", exc_info=True)

            # Volver a la pantalla de creación de usuarios del socio
            return redirect("partner_create_user")
    else:
        form = SocioAutoRegistroForm()

    return render(request, "users/partner_autoregistro.html", {"form": form})


class AutoRegistroSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label="Nombre",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Nombre",
        })
    )
    last_name = forms.CharField(
        max_length=150,
        label="Apellido",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Apellido",
        })
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Contraseña",
        })
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Repite la contraseña",
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned


def autoregistro_registro(request, token):
    """
    Vista que recibe el token de invitación, muestra el formulario
    y crea el usuario una sola vez.
    """
    # 1) Buscar invitación
    try:
        invitacion = RegistroInvitacion.objects.get(token=token)
    except RegistroInvitacion.DoesNotExist:
        messages.error(request, "El enlace de invitación no es válido.")
        return render(request, "users/autoregistro_invalid.html")

    now = timezone.now()

    # 2) Validar si ya fue usada
    if invitacion.usado:
        messages.error(request, "Este enlace ya fue utilizado.")
        return render(request, "users/autoregistro_invalid.html")

    # 3) Expirar después de 7 días usando creado_en
    if invitacion.creado_en and invitacion.creado_en < now - timedelta(days=7):
        invitacion.usado = True
        invitacion.usado_en = now
        invitacion.save()
        messages.error(request, "Este enlace ha expirado.")
        return render(request, "users/autoregistro_invalid.html")

    # 4) Validar si ya existe un usuario con ese correo (por seguridad)
    if User.objects.filter(email__iexact=invitacion.email).exists():
        invitacion.usado = True
        invitacion.usado_en = now
        invitacion.save()
        messages.error(
            request,
            "Ya existe un usuario registrado con este correo. No es posible usar esta invitación."
        )
        return render(request, "users/autoregistro_invalid.html")

    if request.method == "POST":
        form = AutoRegistroSignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            password = cd["password1"]

            # Rol por defecto para el invitado: audit_manager
            try:
                role = Roles.objects.get(name="audit_manager")
            except Roles.DoesNotExist:
                role = None

            # Crear usuario
            user = User(
                username=invitacion.email,
                email=invitacion.email,
                first_name=cd["first_name"],
                last_name=cd["last_name"],
                password=make_password(password),
                modalidad="I",  # Individual
                plan="A",       # Anual
            )
            if role:
                user.role = role

            # Guardar quién lo invitó (el socio)
            if invitacion.socio_id:
                user.created_by_id = invitacion.socio_id

            # Si el socio que invitó es revisor fiscal → marcar también al nuevo usuario
            if invitacion.socio and getattr(invitacion.socio, "revisor_fiscal", False):
                user.revisor_fiscal = True

            user.save()

            # Marcar la invitación como usada
            invitacion.usado = True
            invitacion.usado_en = now
            invitacion.save()

            # ✅ Notificar al dueño que el autoregistro fue exitoso y se creó el usuario
            try:
                send_autoregistro_success_admin_notification(invitacion, user)
            except Exception as e:
                logger.error(
                    f"[AUTOREGISTRO] Error notificando éxito al dueño: {e}",
                    exc_info=True
                )

            # Autenticar y loguear al usuario recién creado
            from django.contrib.auth import authenticate
            auth_user = authenticate(request=request, email=user.email, password=password)

            if auth_user is not None:
                login_func(request, auth_user)
                messages.success(
                    request,
                    "Tu cuenta ha sido creada correctamente. ¡Bienvenido a AuditaPro!"
                )
                return redirect("dashboard")
            else:
                messages.success(
                    request,
                    "Tu cuenta ha sido creada correctamente. Ahora puedes iniciar sesión con tu correo y contraseña."
                )
                return redirect("login")
    else:
        form = AutoRegistroSignupForm()

    return render(
        request,
        "users/autoregistro_signup.html",
        {
            "form": form,
            "email_destino": invitacion.email,  # solo para mostrarlo en el template
        },
    )
