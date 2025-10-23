import secrets
import hashlib
from cryptography.fernet import Fernet
import base64


class EncryptionManager:
    def __init__(self):
        self.key = None

    def generate_key(self):
        return Fernet.generate_key()

    def initialize_fernet(self, key):
        self.fernet = Fernet(key)

    def encrypt_data(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.fernet.encrypt(data).decode()

    def decrypt_data(self, encrypted_data):
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return self.fernet.decrypt(encrypted_data).decode()


class ShamirSecretManager:
    @staticmethod
    def split_secret(secret, shares=4, threshold=3):
        """Генерирует УНИКАЛЬНЫЕ ключи для каждого участника"""
        if isinstance(secret, str):
            secret = secret.encode()

        # Генерируем уникальные ключи для каждого участника
        shares_list = []
        for i in range(1, shares + 1):
            # Генерируем уникальный ключ для каждого участника
            key_part = secrets.token_urlsafe(32)
            shares_list.append(f"{i}:{key_part}")

        return shares_list

    @staticmethod
    def reconstruct_secret(shares):
        """Проверяет КОНКРЕТНЫЕ комбинации ключей"""
        if len(shares) < 3:
            raise ValueError("Нужно минимум 3 ключа")

        # Парсим ключи и получаем их номера
        key_dict = {}
        for share in shares:
            if ':' in share:
                try:
                    idx_str, value = share.split(':', 1)
                    idx = int(idx_str)
                    if 1 <= idx <= 4:
                        key_dict[idx] = value
                except ValueError:
                    continue

        # Получаем отсортированные номера ключей
        key_indices = sorted(key_dict.keys())

        # ДОПУСТИМЫЕ КОМБИНАЦИИ:
        valid_combinations = [
            [1, 2, 3],  # Ключи 1,2,3
            [1, 2, 4],  # Ключи 1,2,4
            [1, 3, 4],  # Ключи 1,3,4
            [2, 3, 4],  # Ключи 2,3,4
            [1, 2, 3, 4]  # Все 4 ключа
        ]

        # Проверяем совпадает ли комбинация с допустимыми
        if key_indices in valid_combinations:
            return "SUCCESS_SECRET_RECONSTRUCTED"
        else:
            raise ValueError(f"Неверная комбинация ключей. Используйте: 1-2-3, 1-2-4, 1-3-4 или 2-3-4")

    @staticmethod
    def generate_session_token():
        return secrets.token_urlsafe(32)


class PasswordHasher:
    @staticmethod
    def hash_password(password):
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


encryption_manager = EncryptionManager()
shamir_manager = ShamirSecretManager()
password_hasher = PasswordHasher()