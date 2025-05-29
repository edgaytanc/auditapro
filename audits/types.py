from typing import List, TypedDict
from datetime import datetime
from common.utils import is_valid_date
from users.types import User, is_user_type


class Audit(TypedDict):
    id: int
    title: str
    title: str
    description: str
    company: str
    created_at: datetime
    updated_at: datetime | None
    audit_manager: User
    assigned_users: List[User]


def is_audit_type(audit: Audit):
    try:
        return (
            isinstance(audit["id"], int)
            and isinstance(audit["title"], str)
            and isinstance(audit["company"], str)
            and is_valid_date(audit["created_at"])
            and is_valid_date(audit["updated_at"])
            and is_user_type(audit["audit_manager"])
            and isinstance(audit["assigned_users"], list)
            and all(
                is_user_type(assigned_user) for assigned_user in audit["assigned_users"]
            )
        )
    except KeyError:
        return False
