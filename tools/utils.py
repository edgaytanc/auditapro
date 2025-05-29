from datetime import datetime
import django_tables2 as tables
from django.http import HttpRequest
from audits.types import Audit as AuditType
from django.db import models
from typing import Type, Tuple
from django.db.models import Q
from django_tables2 import RequestConfig
from django.db.models import ForeignKey
from functools import reduce
from dateutil.relativedelta import relativedelta


def search_query_table(
    req: HttpRequest,
    search_query: str,
    Model: Type[models.Model],
    filters: Tuple[str],
    selected_audit: AuditType | None = None,
    second_field: str | None = None,
    owner_field: str | None = None,
):
    # Obtiene el campo del modelo Verifica si es un ForeignKey Accede al segundo campo si modelo relacionado
    queries = []

    for field in filters:
        if isinstance(field, tuple):
            queries.append(Q(**{f"{field[0]}__{field[1]}__icontains": search_query}))
        else:
            queries.append(Q(**{f"{field}__icontains": search_query}))

    # Combina las consultas Q usando reduce
    query = reduce(lambda x, y: x | y, queries)
    if owner_field:
        query &= Q(**{f"{owner_field}": req.user})
    if selected_audit:
        query &= Q(**{"audit__id": selected_audit["id"]})

    return Model.objects.filter(query)


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
    # Aquí lo que hace es primero, obtener los campos que sean relaciones del modelo pasado, luego, va a obtener los valores, los cuales serán distintos si hay un campo de filtrado, luego, filtrará los campos usando la auditoría seleccionada y también si el dueño es el usuario que hizo la petición.
    relation_fields = get_related_fields(Model)

    values = (
        (
            search_query_table(
                req, search_query, Model, filters, selected_audit=selected_audit
            )
            if search_query
            else Model.objects.filter(
                auditor=req.user, audit__id=selected_audit["id"]
            ).select_related(*relation_fields)
        )
        if selected_audit
        else (
            search_query_table(req, search_query, Model, filters)
            if search_query
            else Model.objects.select_related(*relation_fields)
        )
    )

    if edit_url and delete_url and confirmation_field:
        table = TableClass(
            values,
            edit_url=edit_url,
            delete_url=delete_url,
            confirmation_field=confirmation_field,
        )
    else:
        table = TableClass(
            values,
        )
    RequestConfig(req, paginate={"per_page": 15}).configure(table)
    return table


def get_table_to_pdf(
    req: HttpRequest,
    Model: Type[models.Model],
    TableClass: Type[tables.Table],
    selected_audit: AuditType | None = None,
):
    relation_fields = get_related_fields(Model)
    values = (
        Model.objects.filter(
            auditor=req.user, audit__id=selected_audit["id"]
        ).select_related(*relation_fields)
        if selected_audit
        else Model.objects.filter().select_related(*relation_fields)
    )

    table = TableClass(values)
    return table


# Devuelve los campos que sean relaciones
def get_related_fields(model):
    return [
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, ForeignKey)
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
