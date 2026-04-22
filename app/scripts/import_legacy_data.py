from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import AuditLog, Event, Ticket, TicketStatus, User, UserRole

def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if not value or value == "-":
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def normalize_role(value: str | None) -> UserRole:
    if value == "admin":
        return UserRole.admin
    return UserRole.controller

def normalize_status(value: str | None) -> TicketStatus:
    allowed = {
        "active": TicketStatus.active,
        "used": TicketStatus.used,
        "cancelled": TicketStatus.cancelled,
        "blocked": TicketStatus.blocked,
    }
    return allowed.get((value or "").strip().lower(), TicketStatus.active)

def hash_if_needed(password: str | None) -> str:
    if password and password.startswith(("scrypt:", "pbkdf2:")):
        return password
    return generate_password_hash(password or "change-me-now")

def get_or_create_event(name: str, event_date: date | None) -> Event:
    session = db.session
    event = session.scalar(select(Event).where(Event.name == name))
    if event:
        if event.event_date is None and event_date is not None:
            event.event_date = event_date
            session.flush()
        return event

    event = Event(name=name, event_date=event_date)
    session.add(event)
    session.flush()
    return event

def main() -> None:
    app = create_app()

    with app.app_context():
        legacy_path = Path(app.config["LEGACY_DATABASE_PATH"]).resolve()
        if not legacy_path.exists():
            raise SystemExit(f"Не найден legacy-файл БД: {legacy_path}")

        conn = sqlite3.connect(legacy_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        imported_users = 0
        imported_events = 0
        imported_tickets = 0
        imported_logs = 0

        for row in cur.execute("SELECT username, password, role FROM users"):
            username = (row["username"] or "").strip().lower()
            if not username:
                continue

            exists = db.session.scalar(select(User).where(User.username == username))
            if exists:
                continue

            user = User(
                username=username,
                password_hash=hash_if_needed(row["password"]),
                role=normalize_role(row["role"]),
            )
            db.session.add(user)
            imported_users += 1

        db.session.commit()

        for row in cur.execute("SELECT name, event_date FROM events_list"):
            name = (row["name"] or "").strip()
            if not name:
                continue

            exists = db.session.scalar(select(Event).where(Event.name == name))
            if exists:
                continue

            event = Event(name=name, event_date=parse_date(row["event_date"]))
            db.session.add(event)
            imported_events += 1

        db.session.commit()

        for row in cur.execute("SELECT id, name, event, seat, status, date FROM tickets"):
            ticket_id = (row["id"] or "").strip()
            owner_name = (row["name"] or "").strip()
            event_name = (row["event"] or "").strip()
            seat = (row["seat"] or "").strip()

            if not ticket_id or not owner_name or not event_name or not seat:
                continue

            if db.session.get(Ticket, ticket_id):
                continue

            event = get_or_create_event(event_name, parse_date(row["date"]))

            duplicate_seat = db.session.scalar(
                select(Ticket).where(
                    Ticket.event_id == event.id,
                    Ticket.seat == seat,
                )
            )
            if duplicate_seat:
                print(f"Пропуск дубля места: {event_name} / {seat}")
                continue

            ticket = Ticket(
                id=ticket_id,
                event_id=event.id,
                owner_name=owner_name,
                seat=seat,
                status=normalize_status(row["status"]),
            )
            db.session.add(ticket)
            imported_tickets += 1

        db.session.commit()

        for row in cur.execute("SELECT timestamp, username, action, details FROM logs ORDER BY id"):
            username = (row["username"] or "").strip().lower() or None
            user = None
            if username:
                user = db.session.scalar(select(User).where(User.username == username))

            audit = AuditLog(
                user_id=user.id if user else None,
                username_snapshot=username,
                action=(row["action"] or "legacy_log")[:128],
                details=row["details"],
                created_at=parse_datetime(row["timestamp"]) or datetime.now(timezone.utc),
            )
            db.session.add(audit)
            imported_logs += 1

        db.session.commit()
        conn.close()

        print("Импорт завершен.")
        print(f"Users:   {imported_users}")
        print(f"Events:  {imported_events}")
        print(f"Tickets: {imported_tickets}")
        print(f"Logs:    {imported_logs}")

if __name__ == "__main__":
    main()
