from dkinvite.extensions import db
from dkinvite.models import User
from dkinvite.repositories.audit_log_repository import AuditLogRepository

class AuditService:
    @staticmethod
    def log(
        *,
        user: User | None,
        action: str,
        details: str | None = None,
        ticket_id: str | None = None,
        commit: bool = True,
    ) -> None:
        AuditLogRepository.create(
            user=user,
            action=action,
            details=details,
            ticket_id=ticket_id,
        )
        if commit:
            db.session.commit()
