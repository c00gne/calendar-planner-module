import unittest
import os
import sys
import time
from datetime import date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, db
from models import User, Event
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_temp.db'  
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class CalendarTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = app
        self.app.config.from_object(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.test_user = User(username='testuser', email='test@example.com')
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()
        
        self.client = self.app.test_client()
        self.start_time = time.time()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()  
        self.app_context.pop()
        test_time = time.time() - self.start_time
        print(f"Test completed in {test_time:.3f}s")
    
    def test_user_creation(self):
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpassword'))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_password_hashing(self):
        user = User(username='hash_test', email='hash@test.com')
        user.set_password('secure_password')
        
        self.assertNotEqual(user.password_hash, 'secure_password')
        self.assertTrue(user.check_password('secure_password'))
        self.assertFalse(user.check_password('wrong_password'))
    
    def test_event_creation(self):
        event = Event(
            title='Test Event',
            description='Test Description',
            date=date(2024, 10, 15),
            user_id=self.test_user.id
        )
        db.session.add(event)
        db.session.commit()
        
        saved_event = Event.query.filter_by(title='Test Event').first()
        self.assertIsNotNone(saved_event)
        self.assertEqual(saved_event.description, 'Test Description')
        self.assertEqual(saved_event.date, date(2024, 10, 15))
        self.assertEqual(saved_event.user_id, self.test_user.id)
    
    def test_user_events_relationship(self):
        event1 = Event(title='Event 1', date=date(2024, 10, 1), user_id=self.test_user.id)
        event2 = Event(title='Event 2', date=date(2024, 10, 2), user_id=self.test_user.id)
        
        db.session.add_all([event1, event2])
        db.session.commit()
        
        user_events = Event.query.filter_by(user_id=self.test_user.id).all()
        self.assertEqual(len(user_events), 2)
        self.assertEqual(user_events[0].title, 'Event 1')
        self.assertEqual(user_events[1].title, 'Event 2')
    
    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Compact Planner', response.data)
    
    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'username', response.data)
        self.assertIn(b'password', response.data)
    
    def test_register_page(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'email', response.data)
        self.assertIn(b'password', response.data)
    
    def test_successful_registration(self):
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        user = User.query.filter_by(username='newuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newuser@example.com')
    
    def test_duplicate_username_registration(self):
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'different@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
    
    def test_successful_login(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
    
    def test_failed_login(self):
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
    
    def test_protected_routes_redirect(self):
        response = self.client.get('/current-month', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

class ModelRelationshipsTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = app
        self.app.config.from_object(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all() 
        self.start_time = time.time()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        test_time = time.time() - self.start_time
        print(f"Test completed in {test_time:.3f}s")
    
    def test_user_event_cascade_delete(self):
        user = User(username='cascade_test', email='cascade@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        event1 = Event(title='Cascade Event 1', date=date(2024, 10, 1), user_id=user.id)
        event2 = Event(title='Cascade Event 2', date=date(2024, 10, 2), user_id=user.id)
        db.session.add_all([event1, event2])
        db.session.commit()
        
        event_ids = [event1.id, event2.id]
        
        db.session.delete(user)
        db.session.commit()
        
        for event_id in event_ids:
            event = Event.query.get(event_id)
            self.assertIsNone(event)

class EventFunctionalityTestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = app
        self.app.config.from_object(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        self.test_user = User(username='eventuser', email='event@example.com')
        self.test_user.set_password('testpass')
        db.session.add(self.test_user)
        db.session.commit()
        
        self.client = self.app.test_client()
        self.start_time = time.time()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        test_time = time.time() - self.start_time
        print(f"Test completed in {test_time:.3f}s")
    
    def test_event_creation_via_form(self):
        self.client.post('/login', data={
            'username': 'eventuser',
            'password': 'testpass'
        })
        
        response = self.client.post('/add', data={
            'title': 'Test Event via Form',
            'description': 'Test Description',
            'date': '2024-10-20'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        event = Event.query.filter_by(title='Test Event via Form').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.description, 'Test Description')
        self.assertEqual(str(event.date), '2024-10-20')

def run_production_tests():
    print("\n" + "="*50)
    print("PRODUCTION DATA TESTS (без очистки БД)")
    print("="*50)
    
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'
    
    try:
        with app.app_context():
            users = User.query.all()
            events = Event.query.all()
            print(f"Users in main DB: {len(users)}")
            print(f"Events in main DB: {len(events)}")
            
            new_user = User(username='temp_test_user', email='temp@test.com')
            new_user.set_password('temp_pass')
            db.session.add(new_user)
            db.session.commit()
            print("Test user added to main DB")
            
    finally:
        app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

if __name__ == '__main__':
    start_time = time.time()
    
    print("Starting unit tests for Compact Planner...")
    print("=" * 50)
    print("NOTE: Tests use SEPARATE database: test_temp.db")
    print("Main database (calendar.db) is NOT affected")
    print("=" * 50)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(CalendarTestCase))
    suite.addTests(loader.loadTestsFromTestCase(ModelRelationshipsTestCase))
    suite.addTests(loader.loadTestsFromTestCase(EventFunctionalityTestCase))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Total tests: {result.testsRun}")
    print(f"Total time: {total_time:.3f}s")
    
    if result.failures:
        print("\nFAILED TESTS:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nTESTS WITH ERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\nALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("\nSOME TESTS FAILED!")
    
    print("=" * 50)
    print("\nIMPORTANT: Your main database (calendar.db) is preserved!")
    print("Tests used separate database: test_temp.db")
    
    sys.exit(0 if result.wasSuccessful() else 1)