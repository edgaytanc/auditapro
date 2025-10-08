from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from users.models import User, Roles
from django.contrib.auth.hashers import make_password
from .decorators import admin_or_superadmin_required
from django import forms
import logging

# Configurar el logger
logger = logging.getLogger(__name__)

@login_required
@admin_or_superadmin_required
def user_list(request):
    """
    Vista para mostrar la lista de todos los usuarios en el sistema.
    """
    users = User.objects.all()
    
    # Seleccionar la plantilla según el rol del usuario
    if request.user.role and request.user.role.name == 'superadmin':
        template = 'user_management/superadmin_user_list.html'
    else:
        template = 'user_management/user_list.html'
    
    return render(request, template, {
        'users': users,
    })


@login_required
def user_details(request, user_id):
    """
    Vista para mostrar los detalles de un usuario específico.
    """
    user_to_view = get_object_or_404(User, id=user_id)
    
    # Obtener información adicional según el tipo de usuario
    is_auditor = user_to_view.role.name == "auditor"
    is_admin = user_to_view.is_admin()
    
    # Para auditores en modalidad grupal, mostrar a qué administrador está asignado
    assigned_to_admin = None
    if is_auditor and user_to_view.modalidad == 'G' and user_to_view.administrador:
        assigned_to_admin = user_to_view.administrador
    
    # Para administradores, mostrar sus auditores asignados
    assigned_auditors = []
    if is_admin:
        assigned_auditors = user_to_view.get_auditores()
    
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
        queryset=Roles.objects.filter(name__in=["audit_manager", "superadmin"]),
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
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("El correo electrónico ya está en uso.") 
        return email

    


@login_required
def create_user(request):
    """
    Vista para crear un nuevo usuario.
    """
    logger.info("=== INICIO create_user ===")
    logger.info(f"Método: {request.method}")
    
    if request.method == 'POST':
        logger.info("Procesando formulario POST")
        form = UserCreationForm(request.POST)
        logger.info(f"Formulario válido: {form.is_valid()}")
        
        if form.is_valid():
            # Obtener datos del formulario
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            modalidad = form.cleaned_data['modalidad']
            plan_type = form.cleaned_data['plan']
            
            logger.info(f"Datos del formulario:")
            logger.info(f"- Username: {username}")
            logger.info(f"- Role: {role.name}")
            logger.info(f"- Modalidad: {modalidad}")
            logger.info(f"- Plan: {plan_type}")
            
            # Verificar si el usuario ya existe
            if User.objects.filter(username=username).exists():
                logger.warning(f"Error: El usuario {username} ya existe")
                messages.error(request, "El nombre de usuario ya está en uso.")
                return redirect('create_user')
            
            try:
                logger.info("Creando usuario...")
                # Crear el usuario
                user = User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=make_password(password),  # Encriptar la contraseña
                    role=role
                )
                
                # Asignar modalidad y plan según el rol
                if role.name == "superadmin":
                    logger.info("Es superadmin, asignando modalidad=S y plan=NT")
                    user.modalidad = "S"  # S para superadmin
                    user.plan = "NT"      # NT para superadmin
                else:
                    logger.info(f"No es superadmin, asignando modalidad={modalidad} y plan={plan_type}")
                    user.modalidad = modalidad
                    user.plan = plan_type
                
                # Si es un auditor en modalidad grupal, asignar al administrador actual
                if role.name == "auditor" and modalidad == 'G':
                    logger.info("Es auditor en modalidad grupal")
                    # Asumimos que el creador es un administrador
                    if request.user.is_admin():
                        logger.info(f"Asignando administrador: {request.user.username}")
                        user.administrador = request.user
                
                logger.info("Guardando usuario...")
                user.save()
                logger.info(f"Usuario {username} guardado con éxito")
                messages.success(request, f"Usuario {username} creado exitosamente.")
                logger.info("Redirigiendo a user_list")
                return redirect('user_list')
            except Exception as e:
                logger.error(f"ERROR al crear usuario: {str(e)}", exc_info=True)
                messages.error(request, f"Error al crear el usuario: {str(e)}")
        else:
            logger.warning("Formulario inválido")
            logger.warning(f"Errores: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        # Si es GET, mostrar el formulario vacío
        logger.info("Mostrando formulario vacío (GET)")
        form = UserCreationForm()
    
    # Seleccionar la plantilla según el rol del usuario
    if request.user.role and request.user.role.name == 'superadmin':
        template = 'user_management/superadmin_create_user.html'
    else:
        template = 'user_management/create_user.html'
    
    logger.info(f"Renderizando plantilla: {template}")
    return render(request, template, {
        'form': form,
        'roles': Roles.objects.all(),
    })


@login_required
@admin_or_superadmin_required
def edit_user(request, user_id):
    """
    Vista para editar un usuario existente.
    """
    user_to_edit = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Obtener datos del formulario
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Actualizar los datos del usuario
        user_to_edit.first_name = first_name
        user_to_edit.last_name = last_name
        user_to_edit.email = email
        
        # Actualizar contraseña solo si se proporciona una nueva
        if password:
            user_to_edit.password = make_password(password)
        
        user_to_edit.save()
        messages.success(request, f"Usuario {user_to_edit.username} actualizado exitosamente.")
        return redirect('user_details', user_id=user_id)
    
    # Determinar qué plantilla base usar según el rol del usuario
    template = 'user_management/edit_user.html'
    if request.user.role and request.user.role.name == 'superadmin':
        template = 'user_management/superadmin_edit_user.html'
    
    return render(request, template, {
        'user_to_edit': user_to_edit,
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
    if not request.user.role or request.user.role.name != "superadmin":
        return redirect('dashboard')  # Redirigir a dashboard normal si no es superAdmin
    
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
