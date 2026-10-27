from datetime import date, datetime, timedelta

from django.db import transaction

from .models import (
    InternalAuditPlan,
    InternalAuditReport,
    InternalAuditSchedulePhase,
)


DEFAULT_PHASES = [
    "Planificación",
    "Evaluación de controles",
    "Pruebas sustantivas / trabajo de campo",
    "Hallazgos y validación con el cliente",
    "Informe final",
]


def _to_date(value):
    """
    Convierte fechas o textos a date.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        value = value.strip()

        for date_format in (
            "%Y-%m-%d",
            "%d/%m/%Y",
        ):
            try:
                return datetime.strptime(
                    value,
                    date_format,
                ).date()

            except ValueError:
                continue

    return None


def _display_user(user):
    """
    Obtiene un nombre legible del usuario.
    """

    if user is None:
        return ""

    full_name = (
        user.get_full_name().strip()
        if hasattr(user, "get_full_name")
        else ""
    )

    return (
        full_name
        or getattr(user, "username", "")
        or getattr(user, "email", "")
    )


def _build_team(audit):
    """
    Construye el equipo asignado sin duplicados.
    """

    team = []

    manager_name = _display_user(
        audit.audit_manager
    )

    if manager_name:
        team.append(
            f"{manager_name} — Jefe de Auditoría"
        )

    for user in audit.assigned_users.all():
        user_name = _display_user(
            user
        )

        if (
            user_name
            and user_name != manager_name
        ):
            team.append(
                f"{user_name} — Auditor"
            )

    return team


def _phase_dates(
    start_date,
    end_date,
):
    """
    Distribuye las cinco fases dentro del período
    de la auditoría.

    En auditorías muy cortas algunas fases pueden
    quedar en la misma fecha.
    """

    total_days = max(
        (
            end_date
            - start_date
        ).days,
        0,
    )

    percentages = [
        0.00,
        0.15,
        0.35,
        0.70,
        0.90,
        1.00,
    ]

    dates = []

    for index in range(
        len(DEFAULT_PHASES)
    ):
        phase_start = (
            start_date
            + timedelta(
                days=round(
                    total_days
                    * percentages[index]
                )
            )
        )

        phase_end = (
            start_date
            + timedelta(
                days=round(
                    total_days
                    * percentages[index + 1]
                )
            )
        )

        if phase_end < phase_start:
            phase_end = phase_start

        dates.append(
            (
                phase_start,
                phase_end,
            )
        )

    return dates


def ensure_internal_audit_defaults(
    request,
    audit,
):
    """
    Genera los datos base de la Auditoría Interna
    solamente cuando todavía no existen.
    """

    start_date = (
        _to_date(
            getattr(
                audit,
                "fechaInit",
                None,
            )
        )
        or date.today()
    )

    end_date = (
        _to_date(
            getattr(
                audit,
                "fechaEnd",
                None,
            )
        )
        or (
            start_date
            + timedelta(
                days=30
            )
        )
    )

    if end_date < start_date:
        end_date = start_date

    team = _build_team(
        audit
    )

    team_text = ", ".join(
        team
    )

    with transaction.atomic():
        plan, plan_created = (
            InternalAuditPlan.objects
            .get_or_create(
                audit=audit,
                defaults={
                    "client_name": (
                        audit.identidad
                        or ""
                    ),
                    "methodology": (
                        "NIA 315 / NIA 330 — "
                        "enfoque basado en riesgos"
                    ),
                    "budgeted_hours": 0,
                    "start_date": start_date,
                    "estimated_end_date": (
                        end_date
                    ),
                    "assigned_team": (
                        team_text
                    ),
                    "created_by": (
                        request.user
                    ),
                    "updated_by": (
                        request.user
                    ),
                },
            )
        )

        report, report_created = (
            InternalAuditReport.objects
            .get_or_create(
                audit=audit,
                defaults={
                    "prepared_by": (
                        request.user
                    ),
                    "reviewed_by": (
                        audit.audit_manager
                    ),
                    "issue_date": (
                        end_date
                    ),
                },
            )
        )

        phases_created = 0

        if not (
            InternalAuditSchedulePhase.objects
            .filter(
                audit=audit,
            )
            .exists()
        ):
            phase_dates = _phase_dates(
                start_date,
                end_date,
            )

            responsible_names = [
                item.split(
                    " — ",
                    1,
                )[0]
                for item in team
            ]

            if not responsible_names:
                responsible_names = [
                    _display_user(
                        request.user
                    )
                ]

            phases = []

            for index, phase_name in enumerate(
                DEFAULT_PHASES
            ):
                phase_start, phase_end = (
                    phase_dates[index]
                )

                responsible = (
                    responsible_names[
                        index
                        % len(
                            responsible_names
                        )
                    ]
                )

                phases.append(
                    InternalAuditSchedulePhase(
                        audit=audit,
                        phase=phase_name,
                        start_date=phase_start,
                        end_date=phase_end,
                        responsible=responsible,
                        sort_order=(
                            index + 1
                        ) * 10,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                )

            InternalAuditSchedulePhase.objects.bulk_create(
                phases
            )

            phases_created = len(
                phases
            )

    return {
        "plan": plan,
        "report": report,
        "phases": (
            InternalAuditSchedulePhase.objects
            .filter(
                audit=audit,
            )
            .order_by(
                "sort_order",
                "id",
            )
        ),
        "created": {
            "plan": plan_created,
            "report": report_created,
            "phases": phases_created,
        },
    }