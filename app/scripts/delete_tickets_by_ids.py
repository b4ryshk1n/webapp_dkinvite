from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import Ticket
from dkinvite.services.qr_service import QrService

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", required=True)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        deleted = 0

        for ticket_id in args.ids:
            ticket = db.session.get(Ticket, ticket_id.strip())
            if not ticket:
                print(f"Не найден: {ticket_id}")
                continue

            QrService.delete_for_ticket(ticket.id)
            db.session.delete(ticket)
            deleted += 1
            print(f"Удален: {ticket.id} | {ticket.owner_name} | {ticket.seat}")

        db.session.commit()
        print(f"Всего удалено: {deleted}")

if __name__ == "__main__":
    main()
