from .errors import (
    InvalidNoteNotificationError,
    InvalidNotifiedsNotificationError,
    NotifiedsNotificatonDoNotExitsError,
    AuditNotificationDoNotExitsError,
    InvalidAuditNotificationError,
    InvalidNotifierError,
    NotifierDoNotExits,
    NotificationDoNotExits,
    SupervisorInvalidNotifierError,
    AuditorInvalidNotifierError,
    AuditNotAssignantToUser,
)

from audits.errors import AuditDoNotExits, AuditsNullError
from users.errors import UserDoNotExits, UserUnauthorized
from common.constants import ERROR_INSTANCES

CREATE_NOTIFICATION_ERRORS_INSTANCES = (
    InvalidNoteNotificationError,
    InvalidNotifiedsNotificationError,
    NotifiedsNotificatonDoNotExitsError,
    InvalidAuditNotificationError,
    AuditNotificationDoNotExitsError,
    NotificationDoNotExits,
    AuditsNullError,
    InvalidNotifierError,
    AuditDoNotExits,
    NotifierDoNotExits,
    SupervisorInvalidNotifierError,
    AuditorInvalidNotifierError,
    AuditNotAssignantToUser,
    UserUnauthorized,
    UserDoNotExits,
) + ERROR_INSTANCES
