from dataclasses import dataclass
from typing import Literal, Tuple, Type
from django.db import models
from django.http import HttpRequest
import django_tables2 as tables


show_only = Literal["days", "seconds", "minutes", "hours"]


@dataclass
class GetTableProps:
    req = HttpRequest
    search_query = (str,)
    Model = Type[models.Model]
    TableClass = Type[tables.Table]
    filters = Tuple[str]
    delete_url = str
    edit_url = str
    confirmation_field = str
