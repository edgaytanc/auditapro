from datetime import datetime
from functools import reduce
from typing import Tuple, Type

import django_tables2 as tables
from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import ForeignKey, Q
from django.http import HttpRequest
from django_tables2 import RequestConfig

from audits.types import Audit as AuditType


def _get_selected_audit_id(
    selected_audit: AuditType | dict | None,
) -> int | None:
    """
    Obtiene de forma segura el ID de la auditoría seleccionada.
    """

    if not selected_audit:
        return None

    if isinstance(selected_audit, dict):
        audit_id = selected_audit.get("id")
    else:
        audit_id = getattr(
            selected_audit,
            "id",
            None,
        )

    try:
        normalized_id = int(audit_id)
    except (TypeError, ValueError):
        return None

    if normalized_id <= 0:
        return None

    return normalized_id


def _filter_by_selected_audit(
    queryset,
    Model: Type[models.Model],
    selected_audit: AuditType | dict | None,
):
    """
    Aísla un queryset por la auditoría seleccionada.

    No filtra por el usuario creador porque el acceso a la
    auditoría ya fue validado por selected_audit_required.
    Esto permite que el Jefe y los integrantes autorizados
    consulten el trabajo completo del equipo.
    """

    audit_id = _get_selected_audit_id(
        selected_audit
    )

    if audit_id is None:
        return queryset.none()

    model_field_names = {
        field.name
        for field in Model._meta.get_fields()
    }

    if "audit" not in model_field_names:
        return queryset.none()

    return queryset.filter(
        audit_id=audit_id
    )


def _build_search_query(
    search_query: str,
    filters: Tuple[str],
):
    """
    Construye una consulta OR para los campos permitidos.
    """

    queries = []

    for field in filters:
        if isinstance(field, tuple):
            lookup = (
                f"{field[0]}__"
                f"{field[1]}__icontains"
            )
        else:
            lookup = (
                f"{field}__icontains"
            )

        queries.append(
            Q(**{
                lookup: search_query,
            })
        )

    if not queries:
        return Q()

    return reduce(
        lambda current, following: (
            current | following
        ),
        queries,
    )


def search_query_table(
    req: HttpRequest,
    search_query: str,
    Model: Type[models.Model],
    filters: Tuple[str],
    selected_audit: AuditType | None = None,
    second_field: str | None = None,
    owner_field: str | None = None,
):
    """
    Busca registros y, cuando aplica, los limita a la
    auditoría seleccionada.
    """

    del second_field

    queryset = Model.objects.all()

    if selected_audit:
        queryset = _filter_by_selected_audit(
            queryset,
            Model,
            selected_audit,
        )

    if owner_field:
        queryset = queryset.filter(
            **{
                owner_field: req.user,
            }
        )

    query = _build_search_query(
        search_query,
        filters,
    )

    return queryset.filter(
        query
    )


def get_table(
    req: HttpRequest,
    search_query: str,
    Model: Type[models.Model],
    TableClass: Type[tables.Table],
    filters: Tuple[str],
    delete_url: str | None = None,
    edit_url: str | None = None,
    confirmation_field: str | None = None,
    selected_audit: AuditType | None = None,
):
    """
    Construye una tabla segura y aislada por auditoría.

    Funciona tanto para modelos cuyo propietario se llama
    `auditor` como para Activity, cuyo creador se llama
    `created_by`.
    """

    relation_fields = get_related_fields(
        Model
    )

    queryset = Model.objects.all()

    if selected_audit:
        queryset = _filter_by_selected_audit(
            queryset,
            Model,
            selected_audit,
        )

    if search_query:
        queryset = queryset.filter(
            _build_search_query(
                search_query,
                filters,
            )
        )

    values = queryset.select_related(
        *relation_fields
    )

    if (
        edit_url
        and delete_url
        and confirmation_field
    ):
        table = TableClass(
            values,
            edit_url=edit_url,
            delete_url=delete_url,
            confirmation_field=(
                confirmation_field
            ),
        )
    else:
        table = TableClass(
            values
        )

    RequestConfig(
        req,
        paginate={
            "per_page": 15,
        },
    ).configure(
        table
    )

    return table


def get_table_to_pdf(
    req: HttpRequest,
    Model: Type[models.Model],
    TableClass: Type[tables.Table],
    selected_audit: AuditType | None = None,
):
    """
    Construye la tabla destinada al PDF usando únicamente
    registros de la auditoría seleccionada.
    """

    del req

    relation_fields = get_related_fields(
        Model
    )

    queryset = Model.objects.all()

    if selected_audit:
        queryset = _filter_by_selected_audit(
            queryset,
            Model,
            selected_audit,
        )

    values = queryset.select_related(
        *relation_fields
    )

    return TableClass(
        values
    )


def get_related_fields(model):
    """
    Devuelve únicamente las relaciones ForeignKey directas.
    """

    return [
        field.name
        for field in model._meta.get_fields()
        if isinstance(
            field,
            ForeignKey,
        )
    ]


def get_and_year_months_between_dates(start_date: datetime, end_date: datetime):
    """
    Obtiene los meses y años entre dos fechas.

    Args:
        start_date (datetime): Fecha de inicio.
        end_date (datetime): Fecha de fin.

    Returns:
        tuple: Dos listas, una con los meses y otra con los años.
    """
    months = []
    years = []
    current_date = start_date.replace(
        day=1
    )  # Asegurarse de que comience al inicio del mes
    while current_date <= end_date:
        months.append(current_date.month)
        years.append(current_date.year)
        current_date += relativedelta(months=1)
    return months, years