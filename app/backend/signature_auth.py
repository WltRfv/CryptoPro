import hashlib
import secrets
from datetime import datetime, timedelta

from .database import db, Member, PublicKey
from .rsa_manager import rsa_manager


class SignatureAuthManager:
    def __init__(self):
        self.used_signatures = {}  # Кэш использованных подписей

    def generate_secure_challenge(self, member_name):
        """Генерирует уникальный challenge с таймстампом"""
        member = Member.query.filter_by(name=member_name).first()
        if not member:
            return None

        timestamp = int(datetime.utcnow().timestamp())
        random_part = secrets.token_urlsafe(16)
        challenge = f"CRYPTO_AUTH_{member.id}_{timestamp}_{random_part}"

        # Сохраняем challenge для проверки свежести
        self.used_signatures[f"challenge_{challenge}"] = datetime.utcnow()
        return challenge

    def verify_challenge_freshness(self, challenge):
        """Проверяет что challenge свежий (не старше 2 минут)"""
        if not challenge.startswith("CRYPTO_AUTH_"):
            return False

        try:
            parts = challenge.split('_')
            timestamp = int(parts[3])
            current_time = datetime.utcnow().timestamp()
            return (current_time - timestamp) < 120  # 2 минуты
        except:
            return False

    def prevent_replay_attack(self, signature):
        """Защита от повторного использования подписи"""
        signature_hash = hashlib.sha256(signature.encode()).hexdigest()
        if signature_hash in self.used_signatures:
            return False
        # Храним подпись 5 минут
        self.used_signatures[signature_hash] = datetime.utcnow()
        return True

    def cleanup_old_signatures(self):
        """Очистка старых подписей из кэша"""
        now = datetime.utcnow()
        expired = []
        for sig_hash, timestamp in self.used_signatures.items():
            if (now - timestamp) > timedelta(minutes=5):
                expired.append(sig_hash)
        for sig_hash in expired:
            del self.used_signatures[sig_hash]

    def verify_single_signature(self, member_name, signature, challenge_message):
        """Проверяет цифровую подпись с защитой от атак"""
        try:
            print(f"🔍 Проверяем вход для: '{member_name}'")

            # Очистка старых подписей
            self.cleanup_old_signatures()

            # Проверяем свежесть challenge
            if not self.verify_challenge_freshness(challenge_message):
                return False, "Устаревший или неверный challenge"

            # Защита от replay-атак
            if not self.prevent_replay_attack(signature):
                return False, "Подпись уже использовалась"

            # Находим участника
            member = Member.query.filter_by(name=member_name).first()
            if not member:
                return False, "Участник не найден"

            # Находим публичный ключ
            public_key = PublicKey.query.filter_by(member_id=member.id).first()
            if not public_key:
                return False, "Публичный ключ не зарегистрирован"

            # Проверяем подпись
            if rsa_manager.verify_signature(
                    public_key.public_key,
                    challenge_message,
                    signature
            ):
                print(f"✅ Успешный безопасный вход: {member.name}")
                return True, member
            else:
                return False, "Неверная подпись"

        except Exception as e:
            print(f"❌ Ошибка при проверке подписи: {e}")
            return False, f"Ошибка: {str(e)}"


# Глобальный экземпляр
signature_auth = SignatureAuthManager()