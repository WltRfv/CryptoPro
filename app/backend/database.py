# app/backend/database.py - ЗАМЕНИ весь файл на:
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
from flask_login import UserMixin

db = SQLAlchemy()


# СНАЧАЛА определяем db, ПОТОМ модели

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Наша команда")
    total_points = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Member(db.Model, UserMixin):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    personal_password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # ДОБАВЛЕНО: флаг преподавателя
    is_teacher = db.Column(db.Boolean, default=False)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


class LoginSession(db.Model):
    __tablename__ = 'login_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    challenge_message = db.Column(db.String(500), nullable=False)  # ДОБАВЛЕНО
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    # Связи
    signatures = db.relationship('SignatureVerification', backref='login_session', lazy=True)


class PublicKey(db.Model):
    __tablename__ = 'public_keys'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    public_key = db.Column(db.Text, nullable=False)  # PEM формат
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с участником
    member = db.relationship('Member', backref=db.backref('public_keys', lazy=True))


class SignatureVerification(db.Model):
    __tablename__ = 'signature_verifications'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('login_sessions.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    signature = db.Column(db.Text, nullable=False)  # Подпись участника
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_valid = db.Column(db.Boolean, default=False)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # ДОБАВЛЕНО: кто предложил вопрос
    proposed_by = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    # ДОБАВЛЕНО: какая команда предложила вопрос
    proposed_by_team = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)


class QuestionPurchase(db.Model):
    __tablename__ = 'question_purchases'
    id = db.Column(db.Integer, primary_key=True)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    purchased_by = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)


class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    from_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    to_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    transfer_type = db.Column(db.String(20), default='regular')  # 'regular' или 'teacher_reward'