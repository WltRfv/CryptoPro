from flask import current_app
from datetime import datetime, timedelta
import secrets
from .database import db, LoginSession, KeyShare, User, Team
from .encryption import shamir_manager, password_hasher
from .email_service import email_service


class AuthManager:
    @staticmethod
    def initiate_team_login(team_name):
        """
        Инициирует процесс входа для команды
        Отправляет части ключей всем участникам команды
        """
        # Находим команду
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            return None, "Команда не найдена"

        # Генерируем токен сессии
        session_token = shamir_manager.generate_session_token()

        # Создаем секрет для этой сессии
        secret = secrets.token_urlsafe(32)

        # Разделяем секрет на части
        shares = shamir_manager.split_secret(
            secret,
            shares=len(team.members),
            threshold=current_app.config['MIN_SHARES']
        )

        # Создаем запись сессии
        login_session = LoginSession(
            session_token=session_token,
            required_shares=current_app.config['MIN_SHARES'],
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db.session.add(login_session)
        db.session.flush()  # Получаем ID для связи

        # Отправляем части ключей участникам
        for i, member in enumerate(team.members):
            key_share = KeyShare(
                share=shares[i],
                email=member.email,
                session_id=login_session.id
            )
            db.session.add(key_share)

            # Отправляем email
            email_service.send_key_share(member.email, shares[i], session_token)

        db.session.commit()
        return session_token, "Ключи отправлены на почту участникам"

    @staticmethod
    def verify_combined_key(shares, session_token):
        """
        Проверяет комбинацию ключей
        """
        # Находим сессию
        session = LoginSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()

        if not session:
            return False, "Сессия не найдена или неактивна"

        if datetime.utcnow() > session.expires_at:
            session.is_active = False
            db.session.commit()
            return False, "Время сессии истекло"

        # Проверяем все возможные комбинации
        valid_combinations = AuthManager._generate_combinations(shares, session.required_shares)

        for combination in valid_combinations:
            try:
                reconstructed_secret = shamir_manager.reconstruct_secret(combination)
                # Если удалось восстановить - успех
                session.is_active = False

                # Помечаем использованные ключи
                for share_text in combination:
                    key_share = KeyShare.query.filter_by(
                        share=share_text,
                        session_id=session.id,
                        is_used=False
                    ).first()
                    if key_share:
                        key_share.is_used = True
                        key_share.used_at = datetime.utcnow()

                db.session.commit()
                return True, "Успешная аутентификация"

            except ValueError:
                continue

        return False, "Неверная комбинация ключей"

    @staticmethod
    def _generate_combinations(shares, k):
        """Генерирует все возможные комбинации из k ключей"""
        from itertools import combinations
        return list(combinations(shares, k))

    @staticmethod
    def verify_personal_login(username, personal_password):
        """
        Проверяет личный логин пользователя
        """
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and password_hasher.verify_password(personal_password, user.personal_password):
            return user, True
        return None, False


# Создаем глобальный экземпляр
auth_manager = AuthManager()