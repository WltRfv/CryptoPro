# app/backend/rsa_manager.py
import os
import struct
import hashlib
import secrets
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.fernet import Fernet


class RSAManager:
    def __init__(self):
        self.block_size = 190
        self.iv_size = 16
        self.salt_size = 16

    def generate_key_pair(self):
        """Генерация пары RSA-2048 ключей"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem.decode('utf-8'), public_pem.decode('utf-8')

    def sign_message(self, private_key_pem, message):
        """Подпись сообщения"""
        if isinstance(message, str):
            message = message.encode('utf-8')

        # Добавляем соль для защиты
        salt = secrets.token_bytes(16)
        message_to_sign = salt + message

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )

        signature = private_key.sign(
            message_to_sign,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return base64.b64encode(salt + signature).decode('utf-8')

    def verify_signature(self, public_key_pem, message, signature):
        """Проверка подписи"""
        if isinstance(message, str):
            message = message.encode('utf-8')

        try:
            signature_data = base64.b64decode(signature)
            salt = signature_data[:16]
            actual_signature = signature_data[16:]

            message_with_salt = salt + message

            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            public_key.verify(
                actual_signature,
                message_with_salt,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True

        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False

    def _pad_message(self, message):
        """PKCS#7 padding для выравнивания блоков"""
        pad_length = self.block_size - (len(message) % self.block_size)
        padding = bytes([pad_length] * pad_length)
        return message + padding

    def _unpad_message(self, padded_message):
        """Удаление PKCS#7 padding"""
        pad_length = padded_message[-1]
        return padded_message[:-pad_length]

    def _generate_session_key(self):
        """Генерация сессионного ключа для симметричного шифрования"""
        return secrets.token_bytes(32)  # AES-256

    def _encrypt_aes(self, data, key):
        """Шифрование данных AES-256-CBC"""
        iv = secrets.token_bytes(self.iv_size)
        salt = secrets.token_bytes(self.salt_size)

        # Деривация ключа из пароля и соли
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = kdf.derive(key)

        # Шифрование AES
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
        encryptor = cipher.encryptor()

        padded_data = self._pad_message(data)
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        return salt + iv + encrypted_data

    def _decrypt_aes(self, encrypted_package, key):
        """Расшифровка данных AES-256-CBC"""
        salt = encrypted_package[:self.salt_size]
        iv = encrypted_package[self.salt_size:self.salt_size + self.iv_size]
        encrypted_data = encrypted_package[self.salt_size + self.iv_size:]

        # Деривация ключа
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = kdf.derive(key)

        # Расшифровка AES
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
        decryptor = cipher.decryptor()

        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
        return self._unpad_message(decrypted_padded)

    def hybrid_encrypt(self, public_key_pem, message):
        """
        Гибридное шифрование: AES для данных + RSA для ключа
        """
        if isinstance(message, str):
            message = message.encode('utf-8')

        # Генерируем сессионный ключ
        session_key = self._generate_session_key()

        # Шифруем сообщение AES
        encrypted_message = self._encrypt_aes(message, session_key)

        # Шифруем сессионный ключ RSA
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

        encrypted_session_key = public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Добавляем HMAC для проверки целостности
        hmac = hashlib.sha256(encrypted_message + encrypted_session_key).digest()

        # Формируем итоговый пакет
        package = struct.pack('!H', len(encrypted_session_key)) + \
                  encrypted_session_key + \
                  encrypted_message + \
                  hmac

        return base64.b64encode(package).decode('utf-8')

    def hybrid_decrypt(self, private_key_pem, encrypted_package):
        """
        Гибридная расшифровка
        """
        try:
            # Декодируем пакет
            package = base64.b64decode(encrypted_package)

            # Извлекаем компоненты
            session_key_len = struct.unpack('!H', package[:2])[0]
            encrypted_session_key = package[2:2 + session_key_len]
            encrypted_message = package[2 + session_key_len:-32]
            received_hmac = package[-32:]

            # Проверяем HMAC
            expected_hmac = hashlib.sha256(encrypted_message + encrypted_session_key).digest()
            if received_hmac != expected_hmac:
                raise ValueError("HMAC verification failed - data corrupted")

            # Расшифровываем сессионный ключ
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )

            session_key = private_key.decrypt(
                encrypted_session_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Расшифровываем сообщение
            decrypted_message = self._decrypt_aes(encrypted_message, session_key)

            return decrypted_message.decode('utf-8')

        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


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
            f.write(salt + encrypted_key)

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


# ВАЖНО: СОЗДАЕМ ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ
rsa_manager = RSAManager()
key_storage = KeyStorageManager()