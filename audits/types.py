from typing import List, TypedDict

from common.utils import is_valid_date
from users.types import User, is_user_type


class Audit(TypedDict):
    id: int
    title: str
    identidad: str
    fechaInit: str
    fechaEnd: str
    tipoAuditoria: str
    created_at: str
    updated_at: str | None
    audit_manager: User
    assigned_users: List[User]


def is_audit_type(audit: Audit) -> bool:
    """
    Valida la estructura serializada que se guarda en
    request.session["selected_audit"].
    """
    try:
        updated_at = audit.get("updated_at")

        return (
            isinstance(audit["id"], int)
            and isinstance(audit["title"], str)
            and isinstance(audit["identidad"], str)
            and isinstance(audit["tipoAuditoria"], str)
            and audit["tipoAuditoria"] in ("F", "R", "I")
            and is_valid_date(audit["fechaInit"])
            and is_valid_date(audit["fechaEnd"])
            and is_valid_date(audit["created_at"])
            and (
                updated_at is None
                or is_valid_date(updated_at)
            )
            and is_user_type(audit["audit_manager"])
            and isinstance(audit["assigned_users"], list)
            and all(
                is_user_type(assigned_user)
                for assigned_user in audit["assigned_users"]
            )
        )

    except (KeyError, TypeError, AttributeError):
        return False