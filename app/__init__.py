from flask import Flask
from flask_login import LoginManager
from config import Config
from app.backend.database import db
from app.backend.email_service import email_service

login_manager = LoginManager()
login_manager.login_view = 'frontend.team_login'  # ВАЖНО: должно быть 'frontend.team_login'
login_manager.login_message = 'Пожалуйста, войдите в систему'


@login_manager.user_loader
def load_user(user_id):
    from app.backend.database import Member
    return Member.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    email_service.init_app(app)

    from app.frontend.routes import bp as frontend_bp
    app.register_blueprint(frontend_bp)

    return app