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

        user_to_manage = User.objects.get(id=user_to_manage_id)

        if not user_to_manage:
            raise UserDoNotExits()

        return user_to_manage
    except User.DoesNotExist:
        raise UserDoNotExits()
    except Exception as e:
        raise e
