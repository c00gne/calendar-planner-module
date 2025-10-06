import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-for-calendar-app-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///calendar.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False