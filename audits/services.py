from django.contrib.auth import get_user_model
from .models import Audit
from .errors import (
    AuditDoNotExits,
    UserAlredyHaveAssignamentAuditError,
    AssignedAuditsNullError,
    AuditManagerDoNotExits,
    AuditsNullError,
    InvalidAuditCompanyError,
    InvalidAuditTitleError,
    AuditManagerUnauthorized,
    InvalidAuditIdentidadError,
    InvalidAuditDateError,
)
from users.errors import UserDoNotExits
from datetime import datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.conf import settings
from django.db import transaction
from django.db.models import Q

User = get_user_model()


def client_can_create_audit_type(owner, audit_type):
    """Creación según marcas contratadas por el cliente/jefe, sin bypass staff.

    Es intencionalmente distinta de `user_can_access_audit_type`, que puede
    conceder acceso al personal interno; aquí se exige la habilitación comercial.
    """
    return {
        "F": True,
        "R": bool(getattr(owner, "revisor_fiscal", False)),
        "I": bool(getattr(owner, "auditoria_interna", False)),
    }.get(audit_type, False)


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
    audit_identidad: str,
    audit_fecha_inicio: str,
    audit_fecha_final: str,
    audit_periodo: str,
    audit_moneda: str,
    audit_financial: bool,
    activa_revisoria: bool,
    audit_internal: bool,
    progress,
    risk_level: str,
    workflow_status: str,
    audit_manager_id: int,
):
    """
    Actualiza los datos generales y de seguimiento de una auditoría.
    """
    try:
        if not audit_manager_id:
            raise AuditManagerDoNotExits()

        if not audit_id:
            raise AuditDoNotExits()

        if not audit_title or not audit_title.strip():
            raise InvalidAuditTitleError()

        if not audit_identidad or not audit_identidad.strip():
            raise InvalidAuditIdentidadError()

        if not audit_fecha_inicio or not audit_fecha_final:
            raise InvalidAuditDateError()

        if not any([
            audit_financial,
            activa_revisoria,
            audit_internal,
        ]):
            raise ValueError(
                "Debe seleccionarse al menos un tipo de auditoría."
            )

        start_date = parse_date(
            audit_fecha_inicio
        )

        end_date = parse_date(
            audit_fecha_final
        )

        if not start_date or not end_date:
            raise InvalidAuditDateError()

        if end_date < start_date:
            raise InvalidAuditDateError()

        try:
            progress = int(progress)
        except (TypeError, ValueError):
            raise ValueError(
                "El avance de la auditoría no es válido."
            )

        if not 0 <= progress <= 100:
            raise ValueError(
                "El avance debe estar entre 0 y 100."
            )

        valid_risks = {
            value
            for value, _label
            in Audit.RISK_CHOICES
        }

        valid_statuses = {
            value
            for value, _label
            in Audit.STATUS_CHOICES
        }

        if risk_level not in valid_risks:
            raise ValueError(
                "El nivel de riesgo no es válido."
            )

        if workflow_status not in valid_statuses:
            raise ValueError(
                "El estado de la auditoría no es válido."
            )

        audit_to_update = Audit.objects.get(
            id=audit_id
        )

        if (
            audit_to_update.audit_manager_id
            != audit_manager_id
        ):
            raise AuditManagerUnauthorized()

        start_datetime = datetime.combine(
            start_date,
            time.min,
        )

        end_datetime = datetime.combine(
            end_date,
            time.max,
        )

        # Si el proyecto utiliza zonas horarias,
        # convertimos las fechas a valores aware.
        # Con USE_TZ=False se mantienen naive,
        # que es lo que SQLite necesita.
        if settings.USE_TZ:
            current_timezone = (
                timezone.get_current_timezone()
            )

            start_datetime = timezone.make_aware(
                start_datetime,
                current_timezone,
            )

            end_datetime = timezone.make_aware(
                end_datetime,
                current_timezone,
            )

        if audit_financial:
            legacy_type = "F"
        elif activa_revisoria:
            legacy_type = "R"
        else:
            legacy_type = "I"

        audit_to_update.title = (
            audit_title.strip()
        )

        audit_to_update.identidad = (
            audit_identidad.strip()
        )

        audit_to_update.fechaInit = (
            start_datetime
        )

        audit_to_update.fechaEnd = (
            end_datetime
        )

        audit_to_update.periodo_auditado = (
            audit_periodo.strip()
        )

        audit_to_update.moneda = (
            audit_moneda or "GTQ"
        )

        audit_to_update.activa_financiera = (
            audit_financial
        )

        audit_to_update.activa_revisoria = (
            activa_revisoria
        )

        audit_to_update.activa_interna = (
            audit_internal
        )

        # Compatibilidad con módulos anteriores.
        audit_to_update.tipoAuditoria = (
            legacy_type
        )

        audit_to_update.progress = progress
        audit_to_update.risk_level = risk_level
        audit_to_update.workflow_status = (
            workflow_status
        )

        audit_to_update.save()

        return audit_to_update

    except Audit.DoesNotExist:
        raise AuditDoNotExits()

def create_audit(
    audit_manager,
    audit_title: str,
    audit_identidad: str,
    audit_fechaInit: str,
    audit_fechaEnd: str,
    audit_financial: bool,
    activa_revisoria: bool,
    audit_internal: bool,
    audit_period: str,
    audit_initial_risk: str,
    audit_moneda: str,
    audit_assigned_users_ids: list[str],
):
    """
    Crea una auditoría y valida que todos los usuarios
    asignados pertenezcan al equipo del Jefe.
    """

    if not audit_manager:
        raise AuditManagerDoNotExits()

    manager_role = getattr(
        audit_manager,
        "role",
        None,
    )

    manager_role_name = getattr(
        manager_role,
        "name",
        None,
    )

    if manager_role_name != "audit_manager":
        raise AuditManagerUnauthorized()

    if not audit_title:
        raise InvalidAuditTitleError()

    if not audit_identidad:
        raise InvalidAuditIdentidadError()

    if (
        not audit_fechaInit
        or not audit_fechaEnd
    ):
        raise InvalidAuditDateError()

    # Misma regla del productivo: cada encargo nuevo es de UN tipo.
    selected_types = [
        code for code, enabled in (
            ("F", audit_financial),
            ("R", activa_revisoria),
            ("I", audit_internal),
        ) if enabled
    ]
    if len(selected_types) != 1:
        raise ValueError("Debes seleccionar exactamente un tipo de auditoría.")

    # No confiar en casillas ocultas: validar la habilitación comercial
    # del titular del equipo antes de crear el registro en la BD.
    if not client_can_create_audit_type(audit_manager, selected_types[0]):
        raise ValueError("Tu plan no tiene habilitado este tipo de auditoría.")

    if not audit_period:
        raise ValueError(
            (
                "El período auditado "
                "es obligatorio."
            )
        )

    valid_risk_levels = {
        value
        for value, _label
        in Audit.RISK_CHOICES
    }

    if (
        audit_initial_risk
        not in valid_risk_levels
    ):
        raise ValueError(
            (
                "El nivel de riesgo inicial "
                "no es válido."
            )
        )

    if not audit_assigned_users_ids:
        raise AssignedAuditsNullError()

    try:
        normalized_user_ids = {
            int(user_id)
            for user_id
            in audit_assigned_users_ids
        }

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            (
                "Uno de los usuarios asignados "
                "no es válido."
            )
        ) from error

    allowed_users = list(
        User.objects
        .filter(
            id__in=normalized_user_ids,
            is_active=True,
            is_deleted=False,
        )
        .filter(
            Q(
                id=audit_manager.id
            )
            |
            Q(
                administrador=audit_manager
            )
        )
        .select_related(
            "role",
        )
    )

    allowed_user_ids = {
        user.id
        for user
        in allowed_users
    }

    if (
        allowed_user_ids
        != normalized_user_ids
    ):
        raise ValueError(
            (
                "No puedes asignar usuarios "
                "que pertenezcan a otro equipo."
            )
        )

    if audit_financial:
        legacy_audit_type = "F"

    elif activa_revisoria:
        legacy_audit_type = "R"

    else:
        legacy_audit_type = "I"

    with transaction.atomic():
        audit = Audit.objects.create(
            title=audit_title,
            identidad=audit_identidad,
            fechaInit=audit_fechaInit,
            fechaEnd=audit_fechaEnd,

            tipoAuditoria=(
                legacy_audit_type
            ),

            activa_financiera=(
                audit_financial
            ),
            activa_revisoria=(
                activa_revisoria
            ),
            activa_interna=(
                audit_internal
            ),

            periodo_auditado=(
                audit_period
            ),
            risk_level=(
                audit_initial_risk
            ),

            moneda=(
                audit_moneda
                or "GTQ"
            ),
            audit_manager=(
                audit_manager
            ),
        )

        audit.assigned_users.set(
            allowed_users
        )

    return audit

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
