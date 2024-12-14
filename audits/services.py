from django.contrib.auth import get_user_model
from .models import Audit
from .errors import (
    AuditDoNotExits,
    UserAlredyHaveAssignamentAuditError,
    AssignedAuditsNullError,
    AuditManagerDoNotExits,
    AuditsNullError,
    InvalidAuditCompanyError,
    InvalidAuditDescriptionError,
    InvalidAuditTitleError,
    AuditManagerUnauthorized,
)
from users.errors import UserDoNotExits

User = get_user_model()


def assign_audit(audit_id, user_id, audit_manager_id):
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()
        if not audit_id:
            raise AuditDoNotExits()

        audit = Audit.objects.get(id=audit_id)

        if not audit:
            raise AuditDoNotExits()

        if audit.audit_manager.id != audit_manager_id:
            raise AuditManagerUnauthorized()

        if not user_id:
            raise UserDoNotExits()

        user_to_manage = User.objects.get(id=user_id)

        if not user_to_manage:
            raise UserDoNotExits()

        if audit.assigned_users.contains(user_to_manage):
            raise UserAlredyHaveAssignamentAuditError(
                user_username=user_to_manage.get_full_name()
            )

        audit.assigned_users.add(user_to_manage)
        return audit
    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except User.DoesNotExist:
        raise UserDoNotExits()
    except Exception as e:
        raise e


def assign_audit_to_user(user_id: int, audits_ids: list[str], audit_manager_id):
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()
        if not user_id:
            raise UserDoNotExits()
        if not audits_ids:
            raise AuditsNullError()
        for audit_id in audits_ids:
            assign_audit(audit_id, user_id, audit_manager_id)
    except Exception as e:
        raise e


def unassign_audit(audit_id: int, user_id: int, audit_manager_id):
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()

        audit = Audit.objects.get(id=audit_id)
        if not audit:
            raise AuditDoNotExits()

        if audit.audit_manager.id != audit_manager_id:
            raise AuditManagerUnauthorized()

        user_to_unassign = User.objects.get(id=user_id)
        if not user_to_unassign:
            raise UserDoNotExits()

        audit.assigned_users.remove(user_to_unassign)

    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except User.DoesNotExist:
        raise UserDoNotExits()
    except Exception as e:
        raise e


def multiple_assign_audit(user_ids: list[str], audit_id, audit_manager_id):
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()

        if not user_ids:
            raise AssignedAuditsNullError()
        for user in user_ids:
            assign_audit(audit_id, user, audit_manager_id)
    except Exception as e:
        raise e


def update_audit(
    audit_id: int,
    audit_title: str,
    audit_description: str,
    audit_company: str,
    audit_manager_id,
):
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()
        if not audit_id:
            raise AuditDoNotExits()
        if not audit_title:
            raise InvalidAuditTitleError()
        if not audit_description:
            raise InvalidAuditDescriptionError()
        if not audit_company:
            raise InvalidAuditCompanyError()

        audit_to_update = Audit.objects.get(id=audit_id)
        if not audit_to_update:
            raise AuditDoNotExits()

        if audit_to_update.audit_manager.id != audit_manager_id:
            raise AuditManagerUnauthorized()

        audit_to_update.title = audit_title
        audit_to_update.description = audit_description
        audit_to_update.company = audit_company
        audit_to_update.save()

    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except Exception as e:
        raise e


def create_audit(
    audit_manager,
    audit_title: str,
    audit_description: str,
    audit_company: str,
    audit_assigned_users_ids: list[str],
):
    audit = None
    try:
        if not audit_manager:
            raise AuditManagerDoNotExits()

        if not audit_title:
            raise InvalidAuditTitleError()

        if not audit_description:
            raise InvalidAuditDescriptionError()

        if not audit_company:
            raise InvalidAuditCompanyError()

        if not audit_assigned_users_ids:
            raise AssignedAuditsNullError()

        audit = Audit.objects.create(
            title=audit_title,
            description=audit_description,
            company=audit_company,
            audit_manager=audit_manager,
        )

        for assigned_user in audit_assigned_users_ids:
            user = User.objects.get(id=assigned_user)
            if not user:
                raise UserDoNotExits()

            audit.assigned_users.add(user)

        audit.save()

    except User.DoesNotExist:
        if audit:
            audit.delete()
        raise UserDoNotExits()
    except Exception as e:
        if audit:
            audit.delete()
        raise e


def delete_audit(audit_id, audit_manager_id):
    try:
        if not audit_id:
            raise AuditDoNotExits()
        if not audit_manager_id:
            raise AuditManagerDoNotExits()

        audit_to_delete = Audit.objects.get(id=audit_id)

        if not audit_to_delete:
            raise AuditDoNotExits()
        if audit_to_delete.audit_manager.id != audit_manager_id:
            raise AuditManagerUnauthorized()
        audit_to_delete.delete()

    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except User.DoesNotExist:
        raise UserDoNotExits()
    except Exception as e:
        raise e
