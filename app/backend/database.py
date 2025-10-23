from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
from flask_login import UserMixin

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Наша команда")
    total_points = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Member(db.Model, UserMixin):  # ДОБАВЬТЕ UserMixin
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    personal_password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

    # ДОБАВЬТЕ ЭТИ МЕТОДЫ ДЛЯ FLASK-LOGIN
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
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

class KeyShare(db.Model):
    __tablename__ = 'key_shares'
    id = db.Column(db.Integer, primary_key=True)
    share = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    share_order = db.Column(db.Integer, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)
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
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    purchased_by = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)

class Transfer(db.Model):
    __tablename__ = 'transfers'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)
    from_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    to_member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()