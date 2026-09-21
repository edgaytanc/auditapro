from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from users.models import User, Roles
from django.contrib.auth.hashers import make_password
from .decorators import admin_or_superadmin_required
from django import forms
import logging
from users.emails import send_activation_email_html as send_welcome_email_html, send_admin_notification_email as send_admin_summary_email
from django.views.decorators.http import require_POST
from django.db import transaction
from audits.models import Audit

# Configurar el logger
logger = logging.getLogger(__name__)

@login_required
@admin_or_superadmin_required
def user_list(request):
    users = User.objects.all()
    total_count = User.objects.count()
    active_count = User.objects.filter(is_deleted=False).count()
    inactive_count = User.objects.filter(is_deleted=True).count()


    # ✅ Filtro por estado (querystring ?status=active|inactive|all)
    status = request.GET.get("status", "active")
    if status == "active":
        users = users.filter(is_deleted=False)
    elif status == "inactive":
        users = users.filter(is_deleted=True)

    # Mantén tu lógica de template por rol
    if request.user.role and request.user.role.name == 'superadmin':
        template = 'user_management/superadmin_user_list.html'
    else:
        template = 'user_management/user_list.html'

    return render(request, template, {
    "users": users,
    "status": status,
    "total_count": total_count,
    "active_count": active_count,
    "inactive_count": inactive_count,
})


@login_required
def user_details(request, user_id):
    """
    Vista para mostrar los detalles de un usuario específico.
    """
    user_to_view = get_object_or_404(User, id=user_id)
    
    # Obtener información adicional según el tipo de usuario
    is_auditor = user_to_view.role.name == "auditor"
    is_admin = user_to_view.role and user_to_view.role.name == "audit_manager"

    
    # Para auditores en modalidad grupal, mostrar a qué administrador está asignado
    assigned_to_admin = None
    if is_auditor and user_to_view.modalidad == 'G' and user_to_view.administrador:
        assigned_to_admin = user_to_view.administrador
    
    # Para administradores, mostrar sus auditores asignados
    assigned_auditors = []
    if is_admin:
        assigned_auditors = User.objects.filter(administrador=user_to_view)
    
    # Para todos los usuarios, mostrar quién los creó (no tenemos esta info en el modelo actual)
    # Esto requeriría añadir un campo 'created_by' al modelo User
    
    # Seleccionar la plantilla según el rol del usuario
    template = 'user_management/user_details.html'
    if request.user.role and request.user.role.name == 'superadmin':
        template = 'user_management/superadmin_user_details.html'
    
    return render(request, template, {
        'user_to_view': user_to_view,
        'is_auditor': is_auditor,
        'is_admin': is_admin,
        'assigned_to_admin': assigned_to_admin,
        'assigned_auditors': assigned_auditors,
    })


class UserCreationForm(forms.Form):
    username = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    first_name = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )
    role = forms.ModelChoiceField(
        queryset=Roles.objects.filter(name__in=["audit_manager", "auditor"]),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    modalidad = forms.ChoiceField(
        choices=[('I', 'Individual'), ('G', 'Grupal'), ('S', 'Superadmin')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    plan = forms.ChoiceField(
        choices=[('M', 'Mensual'), ('A', 'Anual'), ('D', 'Demo'), ('NT', 'No Tiene')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegura class="form-control" y agrega is-invalid / is-valid al ligar el form
        for name, field in self.fields.items():
            base = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (base + ' form-control').strip()

        if self.is_bound:  # el usuario ya envió datos
            for name, field in self.fields.items():
                cls = field.widget.attrs.get('class', '')
                if self.errors.get(name):
                    field.widget.attrs['class'] = f'{cls} is-invalid'
                else: field.widget.attrs['class'] = f'{cls} is-valid'
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        plan = cleaned_data.get('plan')
        
        # Si el rol es superadmin, asignar valores específicos
        if role and role.name == 'superadmin':
            cleaned_data['modalidad'] = 'S'
            cleaned_data['plan'] = 'NT'
            logger.info(f"Asignando valores para superadmin: modalidad=S, plan=NT")
        
        # Si el plan es Demo, asignar modalidad Individual y rol audit_manager
        elif plan == 'D':
            cleaned_data['modalidad'] = 'I'
            # Buscar y asignar el rol audit_manager
            audit_manager_role = Roles.objects.filter(name='audit_manager').first()
            if audit_manager_role:
                cleaned_data['role'] = audit_manager_role
                logger.info(f"Plan Demo seleccionado: asignando modalidad=I (Individual), rol=audit_manager")
            else:
                logger.error("No se encontró el rol audit_manager en la base de datos")
            
        return cleaned_data
    
    def clean_email(self):
        """
        Valida que el correo electrónico no exista previamente
        y asegura que username sea igual al email.
        """
        email = self.cleaned_data.get('email', '').strip().lower()

        # Validar duplicado de correo
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("El correo electrónico ya está en uso.")

        # Validar duplicado de username (como el username es igual al email en Audita)
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con este correo electrónico.")

        # Forzar coherencia username=email
        self.cleaned_data['username'] = email

        return email


    def clean_username(self):
        """
        Valida que el nombre de usuario sea único (por si no coincide con el correo).
        """
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está en uso.")
        return username
    

from django.http import Http404

from django.http import Http404

@login_required
def create_user(request):
    """
    Vista para crear un nuevo usuario.

    Acceso permitido únicamente a:
      - Superadministradores del sistema (role.name == 'superadmin')
      - Socios (cuando aplique en tu flujo)
    Si no cumple, responde con 404 (sin redirecciones).

    Además:
      - Envía un correo HTML al nuevo usuario con sus credenciales,
        guía PDF, plantilla Excel y enlace al video de demostración.
      - Envía un correo resumen interno a sistemaaudita@gmail.com
        con los datos del creador y del nuevo usuario.
    """

    u = request.user
    role_name = getattr(getattr(u, "role", None), "name", None)

    #  Gate de acceso (sin redirecciones)
    if not (u.is_superuser or role_name == "superadmin" or getattr(u, "socio", False)):
        raise Http404("Página no encontrada.")

    logger.info("=== INICIO create_user ===")
    logger.info(f"Método: {request.method}")

    if request.method == 'POST':
        logger.info("Procesando formulario POST")
        form = UserCreationForm(request.POST)
        logger.info(f"Formulario válido: {form.is_valid()}")

        if form.is_valid():
            # --- Datos del formulario ---
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']  # ⚠️ Guarda antes de encriptar
            role = form.cleaned_data['role']
            modalidad = form.cleaned_data['modalidad']
            plan_type = form.cleaned_data['plan']

            # 🔹 Nuevo: leer la marca de Revisor Fiscal desde el checkbox
            revisor_fiscal = request.POST.get("revisor_fiscal") == "on"

            logger.info(
                f"Datos del formulario: username={username}, role={role.name}, "
                f"modalidad={modalidad}, plan={plan_type}, revisor_fiscal={revisor_fiscal}"
            )

            # --- Validaciones de duplicados ---
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, "El correo electrónico ya está en uso.")
                return render(
                    request,
                    'user_management/superadmin_create_user.html' if role_name == 'superadmin' or u.is_superuser else 'user_management/create_user.html',
                    {'form': form, 'roles': Roles.objects.all()}
                )

            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, "El nombre de usuario ya está en uso.")
                return render(
                    request,
                    'user_management/superadmin_create_user.html' if role_name == 'superadmin' or u.is_superuser else 'user_management/create_user.html',
                    {'form': form, 'roles': Roles.objects.all()}
                )

            try:
                # --- Creación del usuario ---
                user = User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=make_password(password),
                    role=role,
                    revisor_fiscal=revisor_fiscal,  # 🔹 NUEVO: guardar la marca
                )

                # --- Asignar modalidad y plan ---
                if role.name == "superadmin":
                    user.modalidad = "S"
                    user.plan = "NT"
                else:
                    user.modalidad = modalidad
                    user.plan = plan_type

                # --- Si es auditor grupal, asignar al administrador creador ---
                if (
                    role.name == "auditor"
                    and modalidad == 'G'
                    and hasattr(request.user, "is_admin")
                    and request.user.is_admin()
                ):
                    user.administrador = request.user

                # --- Marcar como socio si se seleccionó ---
                user.socio = True if request.POST.get('socio') == 'on' else False

                # --- Guardar usuario ---
                user.save()
                logger.info(f"Usuario {username} guardado con éxito.")
                messages.success(request, f"Usuario {username} creado exitosamente.")

                # --- Envío de correos solo si el usuario se guardó correctamente ---
                if user.id:
                    try:
                        # Correo HTML al nuevo usuario (credenciales + adjuntos)
                        send_welcome_email_html(user, password)

                        # Correo resumen interno (quién creó a quién)
                        send_admin_summary_email(request.user, user)

                        logger.info("Correos enviados correctamente al usuario %s.", user.email)

                    except Exception as e:
                        logger.error(f"Error al enviar correos de bienvenida o notificación: {e}", exc_info=True)
                        messages.warning(
                            request,
                            "El usuario fue creado correctamente, pero hubo un problema al enviar los correos de notificación."
                        )
                else:
                    logger.error("El usuario no tiene ID asignado tras guardarse. No se enviaron correos.")
                    messages.warning(
                        request,
                        "El usuario fue creado, pero no se pudo confirmar el envío de correos de bienvenida."
                    )

                # --- Volver a mostrar formulario limpio ---
                empty_form = UserCreationForm()
                template = (
                    'user_management/superadmin_create_user.html'
                    if (role_name == 'superadmin' or u.is_superuser)
                    else 'user_management/create_user.html'
                )
                return render(request, template, {'form': empty_form, 'roles': Roles.objects.all()})

            except Exception as e:
                logger.error(f"ERROR al crear usuario: {str(e)}", exc_info=True)
                messages.error(request, f"Error al crear el usuario: {str(e)}")
                template = (
                    'user_management/superadmin_create_user.html'
                    if (role_name == 'superadmin' or u.is_superuser)
                    else 'user_management/create_user.html'
                )
                return render(request, template, {'form': form, 'roles': Roles.objects.all()})
        else:
            # --- Errores del formulario ---
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        logger.info("Mostrando formulario vacío (GET)")
        form = UserCreationForm()

    # --- Render final ---
    template = (
        'user_management/superadmin_create_user.html'
        if (role_name == 'superadmin' or u.is_superuser)
        else 'user_management/create_user.html'
    )
    return render(request, template, {
        'form': form,
        'roles': Roles.objects.all(),
    })


@login_required
@admin_or_superadmin_required
@login_required
@admin_or_superadmin_required
def edit_user(request, user_id):
    """
    Vista para editar un usuario existente.
    Permite al superadmin modificar campos básicos + socio/revisor_fiscal + modalidad/plan + cupos.
    """
    user_to_edit = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        # Datos básicos
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 🔥 Nuevo
        auditor_slots = request.POST.get("auditor_slots")

        # Checks
        socio = request.POST.get("socio")
        revisor_fiscal = request.POST.get("revisor_fiscal")

        # Selects
        modalidad = request.POST.get("modalidad")   # I / G
        plan_type = request.POST.get("plan_type")   # mensual / anual

        # Actualizar básicos
        user_to_edit.first_name = first_name
        user_to_edit.last_name = last_name
        user_to_edit.email = email

        # Solo superadmin puede cambiar estructura comercial
        if request.user.role and request.user.role.name == "superadmin":
            user_to_edit.socio = (socio == "on")
            user_to_edit.revisor_fiscal = (revisor_fiscal == "on")

            # Modalidad
            if modalidad in ("I", "G"):
                user_to_edit.modalidad = modalidad

            # Plan
            plan_map = {
                "mensual": "M",
                "anual": "A",
            }
            if plan_type in plan_map:
                user_to_edit.plan = plan_map[plan_type]

            # 🔥🔥🔥 GUARDAR CUPOS
            if modalidad == "G":
                try:
                    auditor_slots_int = int(auditor_slots or 3)
                    if auditor_slots_int < 3:
                        auditor_slots_int = 3
                    user_to_edit.auditor_slots = auditor_slots_int
                except ValueError:
                    user_to_edit.auditor_slots = 3

        # Password solo si cambia
        if password:
            user_to_edit.password = make_password(password)

        user_to_edit.save()

        messages.success(
            request,
            f"Usuario {user_to_edit.username} actualizado exitosamente."
        )
        return redirect("user_details", user_id=user_id)

    template = "user_management/edit_user.html"
    if request.user.role and request.user.role.name == "superadmin":
        template = "user_management/superadmin_edit_user.html"

    return render(request, template, {
        "user_to_edit": user_to_edit,
        "is_superadmin": request.user.role.name == "superadmin",
    })



@login_required
@admin_or_superadmin_required
def deactivate_user(request, user_id):
    """
    Vista para dar de baja a un usuario.
    Si el usuario es un administrador en modalidad grupal, también se darán de baja todos sus auditores asociados.
    """
    user_to_deactivate = get_object_or_404(User, id=user_id)
    
    # Verificar si el usuario ya está dado de baja
    if user_to_deactivate.is_deleted:
        messages.warning(request, f"El usuario {user_to_deactivate.username} ya está dado de baja.")
        return redirect('user_details', user_id=user_id)
    
    # Verificar si es un auditor en modalidad grupal (solo se pueden dar de baja a través de su administrador)
    if user_to_deactivate.role.name == "auditor" and user_to_deactivate.modalidad == 'G' and user_to_deactivate.administrador:
        messages.error(
            request, 
            f"No se puede dar de baja directamente a un auditor en modalidad grupal. "
            f"Debe dar de baja al administrador {user_to_deactivate.administrador.username}."
        )
        return redirect('user_details', user_id=user_id)
    
    # Proceder con la baja
    user_to_deactivate.deactivate_user()
    
    # Mensaje de éxito con información adicional si se dieron de baja auditores asociados
    if user_to_deactivate.is_admin() and user_to_deactivate.modalidad == 'G':
        auditores_count = user_to_deactivate.auditores.filter(is_deleted=True).count()
        if auditores_count > 0:
            messages.success(
                request, 
                f"Usuario {user_to_deactivate.username} y {auditores_count} auditores asociados dados de baja exitosamente."
            )
        else:
            messages.success(request, f"Usuario {user_to_deactivate.username} dado de baja exitosamente.")
    else:
        messages.success(request, f"Usuario {user_to_deactivate.username} dado de baja exitosamente.")
    
    return redirect('user_list')


@login_required
@admin_or_superadmin_required
def reactivate_user(request, user_id):
    """
    Vista para reactivar a un usuario que ha sido dado de baja.
    """
    user_to_reactivate = get_object_or_404(User, id=user_id)
    
    # Verificar si el usuario ya está activo
    if not user_to_reactivate.is_deleted:
        messages.warning(request, f"El usuario {user_to_reactivate.username} ya está activo.")
        return redirect('user_details', user_id=user_id)
    
    # Reactivar usuario y sus auditores asociados si corresponde
    auditores_reactivados = user_to_reactivate.reactivate_user()
    
    # Mostrar mensaje apropiado según el resultado
    if user_to_reactivate.is_admin() and user_to_reactivate.modalidad == 'G' and auditores_reactivados > 0:
        messages.success(
            request, 
            f"Usuario {user_to_reactivate.username} y {auditores_reactivados} auditores asociados reactivados exitosamente."
        )
    else:
        messages.success(request, f"Usuario {user_to_reactivate.username} reactivado exitosamente.")
    
    return redirect('user_details', user_id=user_id)


@login_required
def superadmin_dashboard(request):
    """
    Vista de dashboard para usuarios con rol superAdmin.
    Solo muestra acceso al módulo de gestión de usuarios.
    """
    # Verificar si el usuario es superAdmin
    user = request.user
    role_name = getattr(getattr(user, "role", None), "name", None)

    # Solo bloqueamos si NO es superadmin ni superusuario
    if not (user.is_superuser or role_name == "superadmin"):
        return redirect('dashboard')

    
    #if not request.user.role or request.user.role.name != "superadmin":
     #   return redirect('dashboard')  # Redirigir a dashboard normal si no es superAdmin
    
    # Obtener estadísticas básicas de usuarios
    total_users = User.objects.count()
    admin_users = User.objects.filter(role__name="audit_manager").count()
    auditor_users = User.objects.filter(role__name="auditor").count()
    superadmin_users = User.objects.filter(role__name="superadmin").count()
    
    return render(request, 'user_management/superadmin_dashboard.html', {
        'total_users': total_users,
        'admin_users': admin_users,
        'auditor_users': auditor_users,
        'superadmin_users': superadmin_users,
    })

@login_required
@admin_or_superadmin_required
@require_POST
def hard_delete_users(request):
    """
    Borra definitivamente (DELETE) usuarios seleccionados,
    pero SOLO si están dados de baja (is_deleted=True)
    y cumpliendo reglas de seguridad (blindaje).
    """
    ids = request.POST.getlist("selected_user_ids")

    if not ids:
        messages.error(request, "No seleccionaste usuarios.")
        return redirect("user_list")

    qs = User.objects.filter(id__in=ids)

    # 1) Nunca permitir hard-delete de superusers
    if qs.filter(is_superuser=True).exists():
        messages.error(request, "No puedes eliminar definitivamente cuentas superusuario.")
        return redirect("user_list")

    # 2) Solo permitir hard-delete de usuarios dados de baja
    if qs.filter(is_deleted=False).exists():
        messages.error(request, "Solo puedes eliminar definitivamente usuarios que estén dados de baja.")
        return redirect("user_list")

    # 3) Evitar borrar usuarios con auditorías asociadas como audit_manager (evita CASCADE)
    user_ids = list(qs.values_list("id", flat=True))
    if Audit.objects.filter(audit_manager_id__in=user_ids).exists():
        messages.error(
            request,
            "No puedes eliminar definitivamente usuarios que tengan auditorías asociadas. "
            "Reasigna o cierra esas auditorías primero."
        )
        return redirect("user_list")

    # 4) (Opcional recomendado) Evitar borrar rol superadmin aunque NO sea is_superuser
    if qs.filter(role__name__iexact="superadmin").exists():
        messages.error(request, "No puedes eliminar definitivamente cuentas con rol Super Admin.")
        return redirect("user_list")

    with transaction.atomic():
        deleted_count, _ = qs.delete()

    messages.success(request, f"Se eliminaron definitivamente {deleted_count} usuarios.")
    return redirect("user_list")
