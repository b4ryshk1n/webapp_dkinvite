import os
import sqlite3
import uuid
import qrcode
import click
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dk-kirova-super-secret')
DATABASE = 'instance/database.sqlite'
QR_FOLDER = 'static/qrs'

os.makedirs('instance', exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

DOMAIN = 'https://dkinvite.ru'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, name TEXT, event TEXT, seat TEXT, status TEXT DEFAULT "active", date TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS events_list (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, event_date TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT DEFAULT "admin")')
        db.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, username TEXT, action TEXT, details TEXT)')
        db.commit()

init_db()

def log_action(action, details=""):
    try:
        db = get_db()
        username = session.get('username', 'system')
        db.execute('INSERT INTO logs (username, action, details) VALUES (?, ?, ?)', (username, action, details))
        db.commit()
    except Exception as e:
        print(f"Ошибка логирования: {e}")

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username'].lower().strip()
        p = request.form['password']
        
        user = get_db().execute('SELECT * FROM users WHERE LOWER(username) = ?', (u,)).fetchone()
        
        if user and check_password_hash(user['password'], p):
            session['logged_in'] = True
            session['username'] = u
            session['role'] = user['role']
            log_action('Вход в систему', f'Авторизован ({session["role"]})')
            
            if session['role'] == 'admin': return redirect(url_for('admin'))
            else: return redirect(url_for('scan'))
            
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('scan'))
    
    db = get_db()
    current_event = request.args.get('event_filter', '')
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        event = request.form.get('event', '')
        date = request.form.get('date', '')
        seats_raw = request.form.get('seat', '')
        
        if not name or not event or not seats_raw:
            flash('Ошибка: Все поля обязательны к заполнению.')
            return redirect(url_for('admin', event_filter=event))
        
        seats = [s.strip() for s in seats_raw.split('|') if s.strip()]
        for seat in seats:
            tid = str(uuid.uuid4())
            qr = qrcode.make(f"{DOMAIN}/ticket/{tid}")
            qr.save(os.path.join(QR_FOLDER, f"{tid}.png"))
            db.execute('INSERT INTO tickets (id, name, event, date, seat) VALUES (?,?,?,?,?)', (tid, name, event, date, seat))
        db.commit()
        
        log_action('Выдача билетов', f'Выдано {len(seats)} шт. на имя {name}')
        flash(f'Билеты успешно выданы ({len(seats)} шт.)')
        return redirect(url_for('admin', event_filter=event))
    
    events = db.execute('SELECT * FROM events_list ORDER BY id DESC').fetchall()
    occupied = [r['seat'] for r in db.execute('SELECT seat FROM tickets WHERE event = ?', (current_event,)).fetchall()] if current_event else []
    return render_template('admin.html', occupied_seats=occupied, events_list=events, current_event=current_event)

@app.route('/admin/logs')
def view_logs():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('scan'))
    logs = get_db().execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100').fetchall()
    return render_template('logs.html', logs=logs)

@app.route('/admin/events', methods=['GET', 'POST'])
def manage_events():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('scan'))
    db = get_db()
    if request.method == 'POST':
        if 'delete' in request.form:
            event_id = request.form['delete']
            db.execute('DELETE FROM events_list WHERE id = ?', (event_id,))
            log_action('Удаление события', f'ID: {event_id}')
        else:
            e_name = request.form['name']
            db.execute('INSERT OR IGNORE INTO events_list (name, event_date) VALUES (?,?)', (e_name, request.form['date']))
            log_action('Создание события', f'Название: {e_name}')
        db.commit()
        return redirect(url_for('manage_events'))
    events = db.execute('SELECT * FROM events_list ORDER BY id DESC').fetchall()
    return render_template('events.html', events=events)

@app.route('/admin/tickets')
def tickets_list():
    if not session.get('logged_in'): return redirect(url_for('login'))
    db = get_db()
    q = request.args.get('q', '').strip()
    e = request.args.get('event', '')
    events = db.execute('SELECT name FROM events_list ORDER BY name').fetchall()
    
    sql = 'SELECT * FROM tickets WHERE 1=1'
    params = []
    if q:
        sql += ' AND (name LIKE ? OR event LIKE ?)'
        params.extend(['%'+q+'%', '%'+q+'%'])
    if e:
        sql += ' AND event = ?'
        params.append(e)
    sql += ' ORDER BY rowid DESC'
    
    tickets = db.execute(sql, params).fetchall()
    return render_template('tickets_list.html', tickets=tickets, events=events, current_event=e, search_q=q)

# === НАСТОЯЩИЙ EXCEL ЭКСПОРТ ===
@app.route('/admin/export')
def export_tickets():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('tickets_list'))
    
    # Защита от падения, если пакет не установился
    try:
        import openpyxl
        from openpyxl.utils import get_column_letter
    except ImportError:
        flash("Библиотека openpyxl не установлена. Подождите окончания сборки контейнера.")
        return redirect(url_for('tickets_list'))
        
    db = get_db()
    q = request.args.get('q', '').strip()
    e = request.args.get('event', '')
    
    sql = 'SELECT name, event, seat, status, date FROM tickets WHERE 1=1'
    params = []
    if q:
        sql += ' AND (name LIKE ? OR event LIKE ?)'
        params.extend(['%'+q+'%', '%'+q+'%'])
    if e:
        sql += ' AND event = ?'
        params.append(e)
    sql += ' ORDER BY event, seat'
    
    tickets = db.execute(sql, params).fetchall()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Билеты ДК"
    
    # Заголовки
    ws.append(['ФИО Гостя', 'Мероприятие', 'Место', 'Статус', 'Дата генерации'])
    
    # ЖЕСТКАЯ ШИРИНА КОЛОНОК (С ЗАПАСОМ)
    ws.column_dimensions['A'].width = 45 # ФИО Гостя
    ws.column_dimensions['B'].width = 35 # Мероприятие
    ws.column_dimensions['C'].width = 15 # Место
    ws.column_dimensions['D'].width = 15 # Статус
    ws.column_dimensions['E'].width = 20 # Дата генерации
    
    # Данные
    for t in tickets:
        status_rus = 'АКТИВЕН' if t['status'] == 'active' else 'ПОГАШЕН'
        ws.append([t['name'], t['event'], t['seat'], status_rus, t['date']])
        
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    log_action('Экспорт данных', f'Выгружен Excel (Мероприятие: {e or "Все"})')
    return send_file(output, download_name="DK_Tickets.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/admin/delete_ticket/<tid>')
def delete_ticket(tid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('tickets_list'))
    db = get_db()
    ticket = db.execute('SELECT name, seat FROM tickets WHERE id = ?', (tid,)).fetchone()
    if ticket:
        log_action('Удаление билета', f'Билет: {ticket["name"]}, Место: {ticket["seat"]}')
        db.execute('DELETE FROM tickets WHERE id = ?', (tid,))
        db.commit()
    return redirect(request.referrer or url_for('tickets_list'))

@app.route('/admin/ticket/<tid>/<action>')
def ticket_action(tid, action):
    if not session.get('logged_in'): return redirect(url_for('login'))
    db = get_db()
    ticket = db.execute('SELECT name, seat FROM tickets WHERE id = ?', (tid,)).fetchone()
    if action == 'use': 
        db.execute('UPDATE tickets SET status = "used" WHERE id = ?', (tid,))
        if ticket: log_action('Билет погашен', f'Гость: {ticket["name"]}')
    elif action == 'reset': 
        db.execute('UPDATE tickets SET status = "active" WHERE id = ?', (tid,))
        if ticket: log_action('Сброс статуса', f'Гость: {ticket["name"]}')
    db.commit()
    return redirect(request.referrer or url_for('ticket', ticket_id=tid))

@app.route('/ticket/<ticket_id>')
def ticket(ticket_id):
    t = get_db().execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not t: return "404", 404
    return render_template('ticket.html', ticket=t, is_admin=session.get('logged_in'))

@app.route('/scan')
def scan():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('scan.html')

@app.cli.command("create-user")
@click.argument("username")
@click.argument("password")
@click.option("--role", default="controller", help="Роль: admin или controller")
def create_user(username, password, role):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                   (username, generate_password_hash(password), role))
        db.commit()
        print(f"Пользователь {username} ({role}) создан.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
