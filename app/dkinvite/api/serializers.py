def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

def serialize_event(event):
    return {
        "id": event.id,
        "name": event.name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }

def serialize_ticket(ticket):
    return {
        "id": ticket.id,
        "event_id": ticket.event_id,
        "event_name": ticket.event.name if ticket.event else None,
        "owner_name": ticket.owner_name,
        "seat": ticket.seat,
        "status": ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        "qr_path": ticket.qr_path,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "used_at": ticket.used_at.isoformat() if ticket.used_at else None,
    }
