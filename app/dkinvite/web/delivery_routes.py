from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from dkinvite.extensions import db
from dkinvite.models import Ticket, UserRole
from dkinvite.services.audit_service import AuditService
from dkinvite.web.deps import require_web_roles

bp = Blueprint("delivery", __name__)


def _sent_at_str(value):
    if not value:
        return None
    return value.astimezone().strftime("%d.%m.%Y %H:%M")


@bp.post("/admin/tickets/mark-sent")
@require_web_roles(UserRole.admin)
def mark_tickets_sent():
    data = request.get_json(silent=True) or {}
    raw_ids = data.get("ticket_ids") or []

    if not isinstance(raw_ids, list):
        return jsonify({"ok": False, "message": "ticket_ids должен быть списком"}), 400

    ticket_ids = []
    for raw_id in raw_ids:
        ticket_id = str(raw_id).strip()
        if ticket_id and ticket_id not in ticket_ids:
            ticket_ids.append(ticket_id)

    if not ticket_ids:
        return jsonify({"ok": True, "items": []}), 200

    tickets = list(
        db.session.scalars(
            select(Ticket).where(Ticket.id.in_(ticket_ids))
        ).all()
    )

    now = datetime.now(timezone.utc)

    for ticket in tickets:
        ticket.sent_at = now

    for ticket in tickets:
        AuditService.log(
            user=g.current_user,
            action="ticket_sent_marked",
            ticket_id=ticket.id,
            details=f"event_id={ticket.event_id}; seat={ticket.seat}",
            commit=False,
        )

    db.session.commit()

    return jsonify({
        "ok": True,
        "items": [
            {
                "id": ticket.id,
                "sent_at": _sent_at_str(ticket.sent_at),
            }
            for ticket in tickets
        ]
    }), 200


@bp.get("/admin/tickets/sent-state")
@require_web_roles(UserRole.admin)
def tickets_sent_state():
    raw_ids = request.args.getlist("ids")
    ticket_ids = []

    for raw_id in raw_ids:
        ticket_id = str(raw_id).strip()
        if ticket_id and ticket_id not in ticket_ids:
            ticket_ids.append(ticket_id)

    if not ticket_ids:
        return jsonify({"ok": True, "items": []}), 200

    tickets = list(
        db.session.scalars(
            select(Ticket).where(Ticket.id.in_(ticket_ids))
        ).all()
    )

    return jsonify({
        "ok": True,
        "items": [
            {
                "id": ticket.id,
                "sent_at": _sent_at_str(ticket.sent_at),
            }
            for ticket in tickets
        ]
    }), 200
