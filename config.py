import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///wallet.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Shamir's Secret Sharing
    MIN_SHARES = 3
    TOTAL_SHARES = 4


# Конфигурация команды и email
TEAM_EMAILS = [
    "samonov.135@mail.ru",
    "galkinasnezana788@gmail.com",
    "lesa85130@gmail.com",
    "pravolavika@gmail.com"
]

TEAM_MEMBERS = [
    {'name': 'Самонов', 'email': 'samonov.135@mail.ru', 'personal_password': 'pass123', 'points': 250},
    {'name': 'Галкина', 'email': 'galkinasnezana788@gmail.com', 'personal_password': 'pass123', 'points': 250},
    {'name': 'Лесня', 'email': 'lesa85130@gmail.com', 'personal_password': 'pass123', 'points': 250},
    {'name': 'Лавика', 'email': 'pravolavika@gmail.com', 'personal_password': 'pass123', 'points': 250},
]