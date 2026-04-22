import pytest
from app import get_db

def test_login_and_roles(client):
    """Проверка авторизации и ролевого доступа"""
    # Логинимся как контролер
    response = client.post('/login', data={'username': 'ctrl_test', 'password': 'pass123'}, follow_redirects=True)
    assert b'logout' in response.data  # Проверяем, что появилась кнопка выхода
    
    # Пытаемся зайти в админку под контролером (должно выкинуть на сканер)
    response = client.get('/admin', follow_redirects=True)
    assert b'scan' in response.data or b'\xd0\xa1\xd0\xba\xd0\xb0\xd0\xbd\xd0\xb5\xd1\x80' in response.data

def test_ticket_creation(client, app):
    """Проверка выдачи билетов администратором"""
    # 1. Авторизуемся как админ
    client.post('/login', data={'username': 'admin_test', 'password': 'pass123'})
    
    # 2. Создаем билет
    test_guest_name = "Lyashova Svetlana Aleksandrovna"
    response = client.post('/admin', data={
        'name': test_guest_name,
        'event': 'Тестовый Концерт',
        'date': '2026-05-01',
        'seat': 'Ряд 1 Место 1'
    }, follow_redirects=True)
    
    # 3. Проверяем, что билет появился в базе
    with app.app_context():
        db = get_db()
        ticket = db.execute("SELECT * FROM tickets WHERE name = ?", (test_guest_name,)).fetchone()
        assert ticket is not None
        assert ticket['event'] == 'Тестовый Концерт'
        assert ticket['status'] == 'active'

def test_ticket_redeem(client, app):
    """Проверка гашения билета"""
    # Авторизуемся как админ
    client.post('/login', data={'username': 'admin_test', 'password': 'pass123'})
    
    # Создаем билет напрямую в БД
    test_id = "test-uuid-1234"
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO tickets (id, name, event, seat) VALUES (?, ?, ?, ?)", 
                   (test_id, "Гость 1", "Событие 1", "Место 1"))
        db.commit()
    
    # Гасим билет через URL (как это делает контролер)
    client.get(f'/admin/ticket/{test_id}/use')
    
    # Проверяем, что статус изменился на used
    with app.app_context():
        ticket = get_db().execute("SELECT status FROM tickets WHERE id = ?", (test_id,)).fetchone()
        assert ticket['status'] == 'used'
