from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    
    events = db.relationship('Event', backref='author', lazy=True, cascade='all, delete-orphan')
    contracts = db.relationship('Contract', backref='manager', lazy=True, cascade='all, delete-orphan')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# таблиця договорів лізингу
class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), nullable=False)   
    client_name = db.Column(db.String(100), nullable=False) 
    client_email = db.Column(db.String(120), nullable=False) # <--- НОВЕ ПОЛЕ
    amount = db.Column(db.Float, nullable=False)       
    start_date = db.Column(db.Date, nullable=False)    
    duration_months = db.Column(db.Integer, nullable=False) 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    events = db.relationship('Event', backref='contract_ref', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Contract {self.number} - {self.client_name}>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # важливвість події: low, medium, high
    priority = db.Column(db.String(20), default='medium') 
    
    # типи подій: general, contract_deadline, payment_reminder
    event_type = db.Column(db.String(20), default='general')
    
    # лінк на договір, якщо подія пов'язана з договором
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=True)

    def __repr__(self):
        return f'<Event {self.title} on {self.date} (Pri: {self.priority})>'