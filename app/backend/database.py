from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import secrets

db = SQLAlchemy()


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    total_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    members = db.relationship('User', backref='team', lazy=True)
    transactions = db.relationship('Transaction', backref='team', lazy=True)
    purchased_questions = db.relationship('QuestionPurchase', backref='team', lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    personal_password = db.Column(db.String(200), nullable=False)  # Для личных операций
    points = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # Связи
    transfers_sent = db.relationship('Transfer', foreign_keys='Transfer.from_user_id', backref='sender', lazy=True)
    transfers_received = db.relationship('Transfer', foreign_keys='Transfer.to_user_id', backref='receiver', lazy=True)


class LoginSession(db.Model):
    __tablename__ = 'login_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    required_shares = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    # Связи
    key_shares = db.relationship('KeyShare', backref='login_session', lazy=True)


class KeyShare(db.Model):
    __tablename__ = 'key_shares'
    id = db.Column(db.Integer, primary_key=True)
    share = db.Column(db.Text, nullable=False)  # Часть ключа
    email = db.Column(db.String(100), nullable=False)
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
    is_approved = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    purchases = db.relationship('QuestionPurchase', backref='question', lazy=True)


class QuestionPurchase(db.Model):
    __tablename__ = 'question_purchases'
    id = db.Column(db.Integer, primary_key=True)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    purchased_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'purchase', 'transfer', 'reward'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Внешние ключи
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()