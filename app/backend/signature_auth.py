# app/backend/signature_auth.py - РАБОЧАЯ ВЕРСИЯ
from datetime import datetime, timedelta
import secrets
import hashlib
from .database import db, Member, PublicKey
from .rsa_manager import rsa_manager


class SignatureAuthManager:
    @staticmethod
    def verify_single_signature(member_name, signature, challenge_message):
        """Проверяет цифровую подпись ОДНОГО участника"""
        try:
            print(f"🔍 Ищем участника: '{member_name}'")

            # ПОКАЖИ ВСЕХ УЧАСТНИКОВ В БАЗЕ
            all_members = Member.query.all()
            print("👥 ВСЕ УЧАСТНИКИ В БАЗЕ:")
            for m in all_members:
                print(f"   - '{m.name}'")

            # Находим участника
            member = Member.query.filter_by(name=member_name).first()
            if not member:
                print(f"❌ Участник '{member_name}' не найден в базе!")
                return False, "Участник не найден"

            print(f"✅ Участник найден: {member.name} (ID: {member.id})")

            # Находим публичный ключ
            public_key = PublicKey.query.filter_by(member_id=member.id).first()
            if not public_key:
                return False, "Публичный ключ не найден"

            print(f"🔑 Публичный ключ найден для {member.name}")

            # Проверяем подпись
            if rsa_manager.verify_signature(
                    public_key.public_key,
                    challenge_message,
                    signature
            ):
                print(f"✅ Успешный вход: {member.name}")
                return True, member
            else:
                print(f"❌ Неверная подпись для {member.name}")
                return False, "Неверная подпись"

        except Exception as e:
            print(f"❌ Ошибка при проверке подписи: {e}")
            return False, f"Ошибка: {str(e)}"


# Глобальный экземпляр
signature_auth = SignatureAuthManager()