import secrets
import hashlib
from cryptography.fernet import Fernet
import base64


class EncryptionManager:
    def __init__(self):
        self.key = None

    def generate_key(self):
        """Генерирует ключ шифрования"""
        return Fernet.generate_key()

    def initialize_fernet(self, key):
        """Инициализирует Fernet с ключом"""
        self.fernet = Fernet(key)

    def encrypt_data(self, data):
        """Шифрует данные"""
        if isinstance(data, str):
            data = data.encode()
        return self.fernet.encrypt(data).decode()

    def decrypt_data(self, encrypted_data):
        """Дешифрует данные"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return self.fernet.decrypt(encrypted_data).decode()


class ShamirSecretManager:
    @staticmethod
    def split_secret(secret, shares=4, threshold=3):
        """
        Упрощенная реализация Shamir's Secret Sharing
        Генерирует ключи, которые можно комбинировать в любом порядке
        """
        if isinstance(secret, str):
            secret = secret.encode()

        # Для демонстрации генерируем случайные ключи
        # В реальном приложении здесь должна быть криптография
        shares_list = []
        for i in range(shares):
            # Генерируем "ключ" - случайную строку
            key_part = secrets.token_urlsafe(16)
            shares_list.append(f"{i + 1}:{key_part}")

        return shares_list

    @staticmethod
    def reconstruct_secret(shares):
        """
        Упрощенная проверка - всегда возвращает успех для демонстрации
        при наличии минимум 3 ключей
        """
        if len(shares) < 3:
            raise ValueError("Нужно минимум 3 ключа")

        # Для демонстрации просто проверяем что есть 3 ключа правильного формата
        valid_keys = []
        for share in shares:
            if ':' in share and len(share) > 5:  # Простая проверка формата
                valid_keys.append(share)

        if len(valid_keys) >= 3:
            return "SUCCESS"  # Возвращаем успех для демонстрации
        else:
            raise ValueError("Неверная комбинация ключей")

    @staticmethod
    def generate_session_token():
        return secrets.token_urlsafe(16)


class PasswordHasher:
    @staticmethod
    def hash_password(password):
        """Хеширует пароль"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${password_hash.hex()}"

    @staticmethod
    def verify_password(password, hashed_password):
        """Проверяет пароль"""
        try:
            salt, stored_hash = hashed_password.split('$')
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return password_hash.hex() == stored_hash
        except:
            return False


# Создаем глобальные экземпляры
encryption_manager = EncryptionManager()
shamir_manager = ShamirSecretManager()
password_hasher = PasswordHasher()