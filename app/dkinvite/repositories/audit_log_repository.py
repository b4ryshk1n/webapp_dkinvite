from dkinvite.extensions import db
from dkinvite.models import AuditLog, User

class AuditLogRepository:
    @staticmethod
    def create(
        *,
        user: User | None,
        action: str,
        details: str | None = None,
        ticket_id: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user.id if user else None,
            username_snapshot=user.username if user else None,
            ticket_id=ticket_id,
            action=action[:128],
            details=details,
        )
        db.session.add(log)
        return log
