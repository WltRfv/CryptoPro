import secrets
import hashlib
from cryptography.fernet import Fernet
import base64
import ssss  # Новая библиотека

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
        Разделяет секрет на части используя схему Шамира
        """
        if isinstance(secret, str):
            secret = secret.encode()

        # Преобразуем в hex для работы с secretsharing
        secret_hex = secret.hex()
        shares_list = SecretSharer.split_secret(secret_hex, threshold, shares)
        return shares_list

    @staticmethod
    def reconstruct_secret(shares):
        """
        Восстанавливает секрет из частей
        """
        try:
            secret_hex = SecretSharer.recover_secret(shares)
            secret = bytes.fromhex(secret_hex)
            return secret.decode()
        except Exception as e:
            raise ValueError(f"Не удалось восстановить секрет: {str(e)}")

    @staticmethod
    def generate_session_token():
        """Генерирует токен сессии для входа"""
        return secrets.token_urlsafe(32)


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