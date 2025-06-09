from audits.errors import AuditManagerDoNotExits
from users.errors import UserDoNotExits
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_to_manage(audit_manage_id: int, user_to_manage_id: int):
    try:
        if not audit_manage_id:
            raise AuditManagerDoNotExits()
        if not user_to_manage_id:
            raise UserDoNotExits()

        # Obtener el administrador
        admin_user = User.objects.get(id=audit_manage_id)
        
        # Verificar que el administrador sea de modalidad grupal
        if admin_user.modalidad != 'G' or not admin_user.role or admin_user.role.name != "audit_manager":
            raise AuditManagerDoNotExits("El usuario no tiene permisos para gestionar auditores")

        # Obtener el usuario a gestionar y verificar que esté asociado al administrador
        user_to_manage = User.objects.get(id=user_to_manage_id, administrador=admin_user)

        if not user_to_manage:
            raise UserDoNotExits()

        return user_to_manage
    except User.DoesNotExist:
        raise UserDoNotExits("El usuario no existe o no está asociado a este administrador")
    except Exception as e:
        raise e
