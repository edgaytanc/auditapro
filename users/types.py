from typing import Dict, TypedDict, Literal
from datetime import datetime

from common.utils import is_valid_date

ROLES = Literal["auditor", "supervisor", "audit_manager"]


class User(TypedDict):
    id: int
    last_login: datetime
    is_superuser: bool
    username: str
    email: str
    is_staff: bool
    is_active: bool
    date_joined: datetime
    first_name: str
    last_name: str
    signature: str
    role: ROLES


def is_user_type(user: User) -> bool:
    try:
        return (
            isinstance(user["id"], int)
            and is_valid_date(user["date_joined"])
            and (user.get("last_login") is None or is_valid_date(user["last_login"]))
            and isinstance(user["is_superuser"], bool)
            and isinstance(user["username"], str)
            and isinstance(user["email"], str)
            and isinstance(user["is_staff"], bool)
            and isinstance(user["is_active"], bool)
            and isinstance(user["first_name"], str)
            and isinstance(user["last_name"], str)
            and isinstance(user["signature"], str)
            and user.get("role").get("name")
            in ("auditor", "supervisor", "audit_manager")
        )
    except KeyError:
        return False
