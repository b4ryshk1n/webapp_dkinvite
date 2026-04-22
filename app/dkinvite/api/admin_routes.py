from flask import Blueprint, g, request

from dkinvite.api.deps import require_roles
from dkinvite.api.responses import error_response, success_response
from dkinvite.api.serializers import serialize_event, serialize_ticket
from dkinvite.models import UserRole
from dkinvite.services.event_service import EventService
from dkinvite.services.ticket_service import TicketService

bp = Blueprint("admin_api", __name__)

@bp.get("/events")
@require_roles(UserRole.admin, UserRole.controller)
def list_events():
    events = EventService.list_events()
    return success_response({"items": [serialize_event(event) for event in events]})

@bp.post("/events")
@require_roles(UserRole.admin)
def create_event():
    data = request.get_json(silent=True) or {}

    try:
        event = EventService.create_event(
            name=data.get("name"),
            event_date=data.get("event_date"),
            actor=g.current_user,
        )
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    return success_response({"item": serialize_event(event)}, status_code=201)

@bp.get("/tickets")
@require_roles(UserRole.admin)
def list_tickets():
    raw_event_id = request.args.get("event_id")
    status = request.args.get("status")

    try:
        event_id = int(raw_event_id) if raw_event_id else None
    except ValueError:
        return error_response("validation_error", "event_id должен быть числом", 400)

    try:
        tickets = TicketService.list_tickets(event_id=event_id, status=status)
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    return success_response({"items": [serialize_ticket(ticket) for ticket in tickets]})

@bp.get("/tickets/<ticket_id>")
@require_roles(UserRole.admin, UserRole.controller)
def get_ticket(ticket_id):
    try:
        ticket = TicketService.get_ticket(ticket_id)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)})

@bp.post("/tickets")
@require_roles(UserRole.admin)
def create_ticket():
    data = request.get_json(silent=True) or {}

    try:
        event_id = int(data.get("event_id"))
    except (TypeError, ValueError):
        return error_response("validation_error", "event_id должен быть числом", 400)

    try:
        ticket = TicketService.create_ticket(
            event_id=event_id,
            owner_name=data.get("owner_name"),
            seat=data.get("seat"),
            actor=g.current_user,
        )
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)}, status_code=201)

@bp.post("/tickets/<ticket_id>/use")
@require_roles(UserRole.admin, UserRole.controller)
def use_ticket(ticket_id):
    try:
        ticket = TicketService.mark_used(ticket_id=ticket_id, actor=g.current_user)
    except ValueError as exc:
        return error_response("invalid_state", str(exc), 400)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)})

@bp.post("/tickets/<ticket_id>/reset")
@require_roles(UserRole.admin)
def reset_ticket(ticket_id):
    try:
        ticket = TicketService.reset_ticket(ticket_id=ticket_id, actor=g.current_user)
    except ValueError as exc:
        return error_response("invalid_state", str(exc), 400)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"item": serialize_ticket(ticket)})

@bp.delete("/tickets/<ticket_id>")
@require_roles(UserRole.admin)
def delete_ticket(ticket_id):
    try:
        TicketService.delete_ticket(ticket_id=ticket_id, actor=g.current_user)
    except LookupError as exc:
        return error_response("not_found", str(exc), 404)

    return success_response({"deleted_ticket_id": ticket_id}, message="Билет удален")
