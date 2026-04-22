from flask import Blueprint, g, request

from dkinvite.api.deps import require_roles
from dkinvite.api.responses import error_response, success_response
from dkinvite.api.serializers import serialize_ticket
from dkinvite.models import UserRole
from dkinvite.services.ticket_service import TicketService

bp = Blueprint("scan_api", __name__)

@bp.get("/lookup/<ticket_id>")
@require_roles(UserRole.admin, UserRole.controller)
def lookup_ticket(ticket_id):
    try:
        ticket = TicketService.get_ticket(ticket_id)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)})

@bp.post("/consume")
@require_roles(UserRole.admin, UserRole.controller)
def consume_ticket():
    data = request.get_json(silent=True) or {}
    ticket_id = (data.get("ticket_id") or "").strip()

    if not ticket_id:
        return error_response("validation_error", "ticket_id обязателен", 400)

    try:
        ticket = TicketService.mark_used(ticket_id=ticket_id, actor=g.current_user)
    except ValueError as exc:
        message = str(exc)
        error_code = "invalid_state"
        if "уже был погашен" in message.lower():
            error_code = "already_used"
        return error_response(error_code, message, 400)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)})
