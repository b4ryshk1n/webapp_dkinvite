from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import Ticket, Event

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=None)
    parser.add_argument("--owner", default=None)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        query = (
            select(Ticket)
            .options(joinedload(Ticket.event))
            .join(Event, Ticket.event_id == Event.id)
            .order_by(Event.name.asc(), Ticket.owner_name.asc(), Ticket.created_at.asc())
        )

        if args.event:
            query = query.where(Event.name == args.event)

        if args.owner:
            query = query.where(Ticket.owner_name.ilike(f"%{args.owner}%"))

        tickets = list(db.session.scalars(query).unique().all())

        if not tickets:
            print("Билеты не найдены.")
            return

        for t in tickets:
            status = t.status.value if hasattr(t.status, "value") else str(t.status)
            print("-" * 100)
            print(f"ID:        {t.id}")
            print(f"Event:     {t.event.name if t.event else '-'}")
            print(f"Owner:     {t.owner_name}")
            print(f"Seat:      {t.seat}")
            print(f"Status:    {status}")
            print(f"Created:   {t.created_at}")
            print(f"QR:        {t.qr_path}")

if __name__ == "__main__":
    main()
