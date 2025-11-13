# Добавляем в конец app/backend/rsa_manager.py
import os
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class KeyStorageManager:
    @staticmethod
    def get_keys_directory():
        """Возвращает безопасную папку для ключей"""
        keys_dir = os.path.join(os.path.expanduser("~"), "cryptopro_keys")
        os.makedirs(keys_dir, exist_ok=True)
        return keys_dir

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """Деривация ключа из пароля"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @staticmethod
    def save_encrypted_private_key(member_name: str, private_key_pem: str, password: str):
        """Сохраняет зашифрованный приватный ключ"""
        keys_dir = KeyStorageManager.get_keys_directory()

        # Генерируем случайную соль
        salt = os.urandom(16)

        # Деривируем ключ из пароля
        key = KeyStorageManager.derive_key_from_password(password, salt)
        fernet = Fernet(key)

        # Шифруем приватный ключ
        encrypted_key = fernet.encrypt(private_key_pem.encode())

        # Сохраняем зашифрованный ключ и соль
        key_filename = f"{member_name}_encrypted.key"
        key_path = os.path.join(keys_dir, key_filename)

        with open(key_path, 'wb') as f:
            f.write(salt + encrypted_key)  # Соль + зашифрованные данные

        print(f"✅ Зашифрованный ключ сохранен: {key_path}")

    @staticmethod
    def load_private_key(member_name: str, password: str) -> str:
        """Загружает и расшифровывает приватный ключ"""
        keys_dir = KeyStorageManager.get_keys_directory()
        key_filename = f"{member_name}_encrypted.key"
        key_path = os.path.join(keys_dir, key_filename)

        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Ключ для {member_name} не найден")

        with open(key_path, 'rb') as f:
            data = f.read()

        # Извлекаем соль и зашифрованные данные
        salt = data[:16]
        encrypted_key = data[16:]

        # Деривируем ключ из пароля
        key = KeyStorageManager.derive_key_from_password(password, salt)
        fernet = Fernet(key)

        # Расшифровываем ключ
        try:
            decrypted_key = fernet.decrypt(encrypted_key)
            return decrypted_key.decode('utf-8')
        except Exception:
            raise ValueError("Неверный пароль для расшифровки ключа")

    @staticmethod
    def key_exists(member_name: str) -> bool:
        """Проверяет существует ли зашифрованный ключ"""
        keys_dir = KeyStorageManager.get_keys_directory()
        key_filename = f"{member_name}_encrypted.key"
        key_path = os.path.join(keys_dir, key_filename)
        return os.path.exists(key_path)


# Создаем глобальный экземпляр
key_storage = KeyStorageManager()