from datetime import date
from io import BytesIO
from types import SimpleNamespace

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from dkinvite.extensions import db
from dkinvite.models import AuditLog, Event, Ticket, UserRole
from dkinvite.repositories.event_repository import EventRepository
from dkinvite.services.audit_service import AuditService
from dkinvite.services.auth_service import AuthService
from dkinvite.services.event_service import EventService
from dkinvite.services.qr_service import QrService
from dkinvite.services.ticket_service import TicketService
from dkinvite.web.deps import require_web_auth, require_web_roles
from dkinvite.utils.validators import parse_seat_list

bp = Blueprint("web", __name__)

def _role_value(user):
    return user.role.value if hasattr(user.role, "value") else str(user.role)

def _ticket_status_value(ticket):
    return ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)

def _ticket_status_label(ticket):
    status = _ticket_status_value(ticket)
    mapping = {
        "active": "Активен",
        "used": "Погашен",
        "cancelled": "Отменен",
        "blocked": "Заблокирован",
    }
    return mapping.get(status, status)

def _date_to_str(value):
    if not value:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def _normalize_search(value):
    return " ".join((value or "").split()).casefold()

def _ticket_vm(ticket):
    return SimpleNamespace(
        id=ticket.id,
        name=ticket.owner_name,
        owner_name=ticket.owner_name,
        event=ticket.event.name if ticket.event else "",
        seat=ticket.seat,
        status=_ticket_status_value(ticket),
        status_label=_ticket_status_label(ticket),
        used_at=ticket.used_at.isoformat() if ticket.used_at else "",
        date=_date_to_str(ticket.event.event_date if ticket.event else None),
        qr_path=ticket.qr_path,
    )

def _event_vm(event):
    return SimpleNamespace(
        id=event.id,
        name=event.name,
        event_date=_date_to_str(event.event_date),
    )

def _log_vm(log):
    return SimpleNamespace(
        timestamp=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        username=log.username_snapshot or "system",
        action=log.action,
        details=log.details or "",
    )

def _parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value)

def _extract_ticket_id(raw_value: str) -> str:
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return ""

    if "/ticket/" in raw_value:
        return raw_value.rstrip("/").split("/ticket/")[-1].split("?")[0].strip()

    return raw_value

@bp.get("/")
def index():
    if session.get("logged_in"):
        if session.get("role") == "admin":
            return redirect(url_for("web.admin"))
        return redirect(url_for("web.scan"))
    return redirect(url_for("web.login"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        result = AuthService.authenticate(username, password)
        if not result:
            flash("Неверный логин или пароль")
            return render_template("login.html"), 401

        user, _token = result

        session.clear()
        session.permanent = True
        session["logged_in"] = True
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = _role_value(user)

        AuditService.log(
            user=user,
            action="Вход в систему",
            details=f"Авторизован ({session['role']})",
        )

        if session["role"] == "admin":
            return redirect(url_for("web.admin"))
        return redirect(url_for("web.scan"))

    return render_template("login.html")

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))

@bp.route("/admin", methods=["GET", "POST"])
@require_web_roles(UserRole.admin)
def admin():
    current_event = (request.args.get("event_filter") or "").strip()
    events = list(db.session.scalars(select(Event).order_by(Event.id.desc())).all())

    if request.method == "POST":
        name = " ".join((request.form.get("name") or "").strip().split())
        event_name = (request.form.get("event") or "").strip()
        date_raw = (request.form.get("date") or "").strip()
        seats_raw = (request.form.get("seat") or "").strip()

        if not name or not event_name or not seats_raw:
            flash("Ошибка: Все поля обязательны к заполнению.")
            return redirect(url_for("web.admin", event_filter=event_name))

        event = EventRepository.get_by_name(event_name)
        if not event:
            flash("Ошибка: мероприятие не найдено.")
            return redirect(url_for("web.admin", event_filter=event_name))

        if date_raw and not event.event_date:
            event.event_date = _parse_date(date_raw)
            db.session.commit()

        try:
            seats = parse_seat_list(seats_raw)
        except Exception as exc:
            flash(str(exc))
            return redirect(url_for("web.admin", event_filter=event_name))

        created_count = 0
        errors = []

        for seat in seats:
            try:
                TicketService.create_ticket(
                    event_id=event.id,
                    owner_name=name,
                    seat=seat,
                    actor=g.current_user,
                )
                created_count += 1
            except Exception as exc:
                errors.append(f"{seat}: {exc}")

        if created_count:
            AuditService.log(
                user=g.current_user,
                action="Выдача билетов",
                details=f"Выдано {created_count} шт. на имя {name}",
            )
            flash(f"Билеты успешно выданы ({created_count} шт.)")

        if errors:
            flash(" ; ".join(errors))

        return redirect(url_for("web.admin", event_filter=event_name))

    occupied = []
    if current_event:
        event = EventRepository.get_by_name(current_event)
        if event:
            occupied = [
                seat
                for seat in db.session.scalars(
                    select(Ticket.seat).where(Ticket.event_id == event.id)
                ).all()
            ]

    return render_template(
        "admin.html",
        occupied_seats=occupied,
        events_list=[_event_vm(ev) for ev in events],
        current_event=current_event,
    )

@bp.route("/admin/events", methods=["GET", "POST"])
@require_web_roles(UserRole.admin)
def manage_events():
    if request.method == "POST":
        if "delete" in request.form:
            event_id = int(request.form["delete"])
            event = db.session.get(Event, event_id)

            if not event:
                flash("Мероприятие не найдено.")
            else:
                tickets = list(
                    db.session.scalars(
                        select(Ticket).where(Ticket.event_id == event.id)
                    ).all()
                )

                for ticket in tickets:
                    QrService.delete_for_ticket(ticket.id)
                    db.session.delete(ticket)

                AuditService.log(
                    user=g.current_user,
                    action="Удаление события",
                    details=f"ID: {event.id}; Название: {event.name}; Билетов удалено: {len(tickets)}",
                )

                db.session.delete(event)
                db.session.commit()
                flash("Мероприятие удалено вместе с билетами.")
        else:
            try:
                event = EventService.create_event(
                    name=request.form.get("name"),
                    event_date=request.form.get("date"),
                    actor=g.current_user,
                )
                flash(f"Мероприятие создано: {event.name}")
            except Exception as exc:
                flash(str(exc))

        return redirect(url_for("web.manage_events"))

    events = list(db.session.scalars(select(Event).order_by(Event.id.desc())).all())
    return render_template("events.html", events=[_event_vm(ev) for ev in events])

@bp.get("/admin/logs")
@require_web_roles(UserRole.admin)
def view_logs():
    logs = list(
        db.session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
        ).all()
    )
    return render_template("logs.html", logs=[_log_vm(log) for log in logs])

@bp.get("/admin/tickets")
@require_web_roles(UserRole.admin)
def tickets_list():
    q = (request.args.get("q") or "").strip()
    current_event = (request.args.get("event") or "").strip()

    query = (
        select(Ticket)
        .options(joinedload(Ticket.event))
        .join(Event, Ticket.event_id == Event.id)
    )

    if current_event:
        query = query.where(Event.name == current_event)

    query = query.order_by(Ticket.created_at.desc())

    tickets = list(db.session.scalars(query).unique().all())

    if q:
        q_norm = _normalize_search(q)
        tickets = [
            t for t in tickets
            if q_norm in _normalize_search(t.owner_name)
            or q_norm in _normalize_search(t.event.name if t.event else "")
        ]

    events = list(db.session.scalars(select(Event).order_by(Event.name.asc())).all())

    return render_template(
        "tickets_list.html",
        tickets=[_ticket_vm(t) for t in tickets],
        events=[SimpleNamespace(name=e.name) for e in events],
        current_event=current_event,
        search_q=q,
    )

@bp.get("/admin/export")
@require_web_roles(UserRole.admin)
def export_tickets():
    q = (request.args.get("q") or "").strip()
    current_event = (request.args.get("event") or "").strip()

    query = (
        select(Ticket)
        .options(joinedload(Ticket.event))
        .join(Event, Ticket.event_id == Event.id)
    )

    if current_event:
        query = query.where(Event.name == current_event)

    query = query.order_by(Event.name.asc(), Ticket.seat.asc())
    tickets = list(db.session.scalars(query).unique().all())

    if q:
        q_norm = _normalize_search(q)
        tickets = [
            t for t in tickets
            if q_norm in _normalize_search(t.owner_name)
            or q_norm in _normalize_search(t.event.name if t.event else "")
        ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Билеты ДК"
    ws.append(["ФИО Гостя", "Мероприятие", "Место", "Статус", "Дата генерации"])

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 20

    for t in tickets:
        status_rus = "АКТИВЕН" if _ticket_status_value(t) == "active" else "ПОГАШЕН"
        ws.append([
            t.owner_name,
            t.event.name if t.event else "",
            t.seat,
            status_rus,
            _date_to_str(t.event.event_date if t.event else None),
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    AuditService.log(
        user=g.current_user,
        action="Экспорт данных",
        details=f"Выгружен Excel (Мероприятие: {current_event or 'Все'})",
    )

    return send_file(
        output,
        download_name="DK_Tickets.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@bp.get("/admin/delete_ticket/<tid>")
@require_web_roles(UserRole.admin)
def delete_ticket(tid):
    try:
        ticket = TicketService.get_ticket(tid)
        details = f"Билет: {ticket.owner_name}, Место: {ticket.seat}"
        TicketService.delete_ticket(ticket_id=tid, actor=g.current_user)
        AuditService.log(
            user=g.current_user,
            action="Удаление билета",
            details=details,
        )
    except Exception as exc:
        flash(str(exc))

    return redirect(request.referrer or url_for("web.tickets_list"))

@bp.get("/admin/ticket/<tid>/<action>")
@require_web_auth
def ticket_action(tid, action):
    try:
        ticket = TicketService.get_ticket(tid)

        if action == "use":
            if session.get("role") not in {"admin", "controller"}:
                flash("Недостаточно прав")
                return redirect(url_for("web.login"))

            TicketService.mark_used(ticket_id=tid, actor=g.current_user)
            AuditService.log(
                user=g.current_user,
                action="Билет погашен",
                details=f"Гость: {ticket.owner_name}",
            )

        elif action == "reset":
            if session.get("role") != "admin":
                flash("Недостаточно прав")
                return redirect(url_for("web.scan"))

            TicketService.reset_ticket(ticket_id=tid, actor=g.current_user)
            AuditService.log(
                user=g.current_user,
                action="Сброс статуса",
                details=f"Гость: {ticket.owner_name}",
            )
    except Exception as exc:
        flash(str(exc))

    return redirect(request.referrer or url_for("web.ticket", ticket_id=tid))

@bp.get("/ticket/<ticket_id>")
def ticket(ticket_id):
    try:
        ticket_obj = TicketService.get_ticket(ticket_id)
    except LookupError:
        return "404", 404

    return render_template("ticket.html", ticket=_ticket_vm(ticket_obj))

@bp.get("/ticket/<ticket_id>/status")
def ticket_status(ticket_id):
    try:
        ticket_obj = TicketService.get_ticket(ticket_id)
    except LookupError:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify({
        "ok": True,
        "ticket": {
            "id": ticket_obj.id,
            "owner_name": ticket_obj.owner_name,
            "event": ticket_obj.event.name if ticket_obj.event else "",
            "seat": ticket_obj.seat,
            "status": _ticket_status_value(ticket_obj),
            "status_label": _ticket_status_label(ticket_obj),
            "used_at": ticket_obj.used_at.isoformat() if ticket_obj.used_at else "",
        }
    }), 200

@bp.route("/scan", methods=["GET", "POST"])
@require_web_roles(UserRole.admin, UserRole.controller)
def scan():
    result_ticket = None

    if request.method == "POST":
        ticket_id = _extract_ticket_id(request.form.get("ticket_id"))
        if not ticket_id:
            flash("Введите ID билета")
            return render_template("scan.html", ticket=None)

        try:
            ticket_obj = TicketService.mark_used(ticket_id=ticket_id, actor=g.current_user)
            AuditService.log(
                user=g.current_user,
                action="Билет погашен через сканер",
                details=f"Гость: {ticket_obj.owner_name}",
            )
            result_ticket = _ticket_vm(ticket_obj)
            flash("Билет успешно погашен")
        except Exception as exc:
            flash(str(exc))

    return render_template("scan.html", ticket=result_ticket)

@bp.post("/scan/consume")
@require_web_roles(UserRole.admin, UserRole.controller)
def scan_consume():
    data = request.get_json(silent=True) or {}
    ticket_id = _extract_ticket_id(data.get("ticket_id"))

    if not ticket_id:
        return jsonify({"ok": False, "error": "ticket_id_required", "message": "Не передан ID билета"}), 400

    try:
        ticket_obj = TicketService.mark_used(ticket_id=ticket_id, actor=g.current_user)
        AuditService.log(
            user=g.current_user,
            action="Билет погашен через камеру",
            details=f"Гость: {ticket_obj.owner_name}",
        )

        return jsonify({
            "ok": True,
            "ticket": {
                "id": ticket_obj.id,
                "owner_name": ticket_obj.owner_name,
                "event": ticket_obj.event.name if ticket_obj.event else "",
                "seat": ticket_obj.seat,
                "status": _ticket_status_value(ticket_obj),
                "status_label": _ticket_status_label(ticket_obj),
                "used_at": ticket_obj.used_at.isoformat() if ticket_obj.used_at else "",
            }
        }), 200

    except LookupError:
        return jsonify({"ok": False, "error": "not_found", "message": "Билет не найден"}), 404
    except ValueError as exc:
        msg = str(exc)
        code = "invalid_state"
        if "уже был погашен" in msg.lower():
            code = "already_used"
        return jsonify({"ok": False, "error": code, "message": msg}), 400
    except Exception:
        return jsonify({"ok": False, "error": "server_error", "message": "Внутренняя ошибка"}), 500
