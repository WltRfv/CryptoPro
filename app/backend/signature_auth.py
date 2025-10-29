# app/backend/signature_auth.py - СОЗДАЙ новый файл
from flask import current_app
from datetime import datetime, timedelta
import secrets
from .database import db, LoginSession, Member, PublicKey, SignatureVerification
from .rsa_manager import rsa_manager


class SignatureAuthManager:
    @staticmethod
    def initiate_team_login():
        """Инициирует процесс входа через цифровые подписи"""
        try:
            # Генерируем session token и challenge
            session_token = secrets.token_urlsafe(32)
            challenge_message = rsa_manager.generate_challenge()

            # Сохраняем сессию
            login_session = LoginSession(
                session_token=session_token,
                challenge_message=challenge_message,
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            db.session.add(login_session)
            db.session.commit()

            return session_token, challenge_message

        except Exception as e:
            print(f"❌ Ошибка в initiate_team_login: {e}")
            db.session.rollback()
            return None, f"Ошибка: {str(e)}"

    @staticmethod
    def verify_member_signature(session_token, member_name, signature):
        """Проверяет цифровую подпись участника"""
        try:
            # Находим активную сессию
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

            # Находим участника
            member = Member.query.filter_by(name=member_name).first()
            if not member:
                return False, "Участник не найден"

            # Находим публичный ключ участника
            public_key = PublicKey.query.filter_by(member_id=member.id).first()
            if not public_key:
                return False, "Публичный ключ участника не найден"

            # Проверяем подпись
            if rsa_manager.verify_signature(
                    public_key.public_key,
                    session.challenge_message,
                    signature
            ):
                # Сохраняем факт верификации
                verification = SignatureVerification(
                    session_id=session.id,
                    member_id=member.id,
                    signature=signature,
                    is_valid=True
                )
                db.session.add(verification)
                db.session.commit()

                return True, "Подпись успешно проверена"
            else:
                # Сохраняем неудачную попытку
                verification = SignatureVerification(
                    session_id=session.id,
                    member_id=member.id,
                    signature=signature,
                    is_valid=False
                )
                db.session.add(verification)
                db.session.commit()
                return False, "Неверная подпись"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка проверки: {str(e)}"

    @staticmethod
    def get_verified_members_count(session_token):
        """Возвращает количество участников, подтвердивших вход"""
        session = LoginSession.query.filter_by(session_token=session_token).first()
        if not session:
            return 0

        return SignatureVerification.query.filter_by(
            session_id=session.id,
            is_valid=True
        ).count()


# Глобальный экземпляр
signature_auth = SignatureAuthManager()