import unittest
import os
import sys
from datetime import date, datetime

# Додаємо шлях до папки проекту, щоб Python бачив main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, db
from models import User, Event, Contract
# для гітхаб екшенс
try:
    from config import Config
except ImportError:
    # Заглушка для GitHub Actions
    class Config:
        SECRET_KEY = 'test-secret'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        WTF_CSRF_ENABLED = False
        MAIL_SUPPRESS_SEND = True
# для гітхаб екшенс

# === КОНФІГУРАЦІЯ ДЛЯ ТЕСТІВ ===
class TestConfig(Config):
    TESTING = True
    # Використовуємо базу даних в оперативній пам'яті (швидко і чисто)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    # ВАЖЛИВО: Блокуємо реальну відправку листів, щоб не потрібен був пароль
    MAIL_SUPPRESS_SEND = True 

class CalendarTestCase(unittest.TestCase):
    
    def setUp(self):
        """Запускається перед КОЖНИМ тестом"""
        self.app = app
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Створюємо тестового користувача
        self.test_user = User(username='testuser', email='test@example.com')
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()

        # Логінимось відразу, щоб не повторювати це в кожному тесті
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
    
    def tearDown(self):
        """Запускається після КОЖНОГО тесту"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # === ТЕСТИ АВТОРИЗАЦІЇ ===
    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # Перевіряємо, чи є на сторінці привітання (значить ми залогінені)
        self.assertIn(b'testuser', response.data)

    # === ТЕСТИ ПОДІЙ (З ПРІОРИТЕТАМИ) ===
    def test_add_event_with_priority(self):
        """Тестуємо створення події з високим пріоритетом"""
        response = self.client.post('/add', data={
            'title': 'Red Event',
            'description': 'Important meeting',
            'date': '2026-05-20',
            'priority': 'high'  # <--- Перевіряємо нову фічу
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Перевіряємо в базі
        event = Event.query.filter_by(title='Red Event').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.priority, 'high')
        self.assertEqual(str(event.date), '2026-05-20')

    # === ТЕСТИ ДОГОВОРІВ (З EMAIL) ===
    def test_add_contract_logic(self):
        """Тестуємо створення договору та генерацію платежів"""
        # Емулюємо відправку форми
        response = self.client.post('/add_contract', data={
            'number': 'CON-001',
            'client': 'Google Inc',
            'client_email': 'client@google.com', # <--- Нове обов'язкове поле
            'amount': '12000',
            'start_date': '2026-01-01',
            'duration': '12'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # 1. Перевіряємо, чи створився договір
        contract = Contract.query.filter_by(number='CON-001').first()
        self.assertIsNotNone(contract)
        self.assertEqual(contract.client_email, 'client@google.com')
        
        # 2. Перевіряємо, чи створилися автоматичні платежі (має бути 12 штук)
        events = Event.query.filter_by(contract_id=contract.id).all()
        self.assertEqual(len(events), 12)
        self.assertEqual(events[0].priority, 'high') # Платежі мають бути червоними

    def test_cancel_contract(self):
        """Тестуємо анулювання договору"""
        # Спочатку створюємо договір вручну в базі
        contract = Contract(
            number='DEL-001',
            client_name='To Delete',
            client_email='delete@test.com',
            amount=5000,
            start_date=date(2026, 1, 1),
            duration_months=6,
            user_id=self.test_user.id
        )
        db.session.add(contract)
        db.session.commit()

        # Тепер видаляємо його через форму
        response = self.client.post('/cancel_contract', data={
            'query': 'DEL-001'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Перевіряємо, що він зник з бази
        deleted_contract = Contract.query.filter_by(number='DEL-001').first()
        self.assertIsNone(deleted_contract)

if __name__ == '__main__':
    print("Running updated tests...")
    unittest.main()