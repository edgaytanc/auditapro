from .errors import (
    AssignedAuditsNullError,
    AuditDoNotExits,
    AuditManagerDoNotExits,
    AuditManagerUnauthorized,
    AuditsNullError,
    InvalidAuditAuditorsError,
    InvalidAuditCompanyError,
    InvalidAuditSupervisoresError,
    InvalidAuditTitleError,
    UserAlredyHaveAssignamentAuditError,
)
from users.errors import UserDoNotExits
from common.constants import ERROR_INSTANCES

AUDIT_ERROR_INSTANCES = (
    AuditDoNotExits,
    AuditManagerUnauthorized,
    AuditManagerDoNotExits,
    UserDoNotExits,
    AssignedAuditsNullError,
    InvalidAuditCompanyError,
    InvalidAuditTitleError,
    AuditsNullError,
    InvalidAuditAuditorsError,
    UserAlredyHaveAssignamentAuditError,
    InvalidAuditSupervisoresError,
) + ERROR_INSTANCES
