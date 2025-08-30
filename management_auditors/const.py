from users.errors import UserDoNotExits
from audits.errors import (
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

from common.constants import ERROR_INSTANCES


MANAGEMENT_AUDITORS_ERROR_INSTANCES = (
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
    UserDoNotExits,
) + ERROR_INSTANCES
