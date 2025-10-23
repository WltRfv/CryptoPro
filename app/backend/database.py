from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets

db = SQLAlchemy()


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Наша команда")  # Только одна команда
    total_points = db.Column(db.Integer, default=1000)  # Общие баллы команды
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    personal_password = db.Column(db.String(200), nullable=False)  # Для личных операций
    points = db.Column(db.Integer, default=0)  # Личные баллы
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)


class LoginSession(db.Model):
    __tablename__ = 'login_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


class KeyShare(db.Model):
    __tablename__ = 'key_shares'
    id = db.Column(db.Integer, primary_key=True)
    share = db.Column(db.Text, nullable=False)  # Часть ключа
    email = db.Column(db.String(100), nullable=False)
    share_order = db.Column(db.Integer, nullable=False)  # Порядок ключа (1,2,3,4)
    is_used = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

    # Внешние ключи
    session_id = db.Column(db.Integer, db.ForeignKey('login_sessions.id'), nullable=False)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuestionPurchase(db.Model):
    __tablename__ = 'question_purchases'
    id = db.Column(db.Integer, primary_key=True)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    purchased_by = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)


class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    from_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    to_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()