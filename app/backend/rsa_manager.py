# app/backend/rsa_manager.py - СОЗДАЙ новый файл
import base64
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import os
import secrets


class RSAManager:
    @staticmethod
    def generate_key_pair():
        """Генерация пары RSA ключей"""
        private_key = crypto_rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend = default_backend()
        )

        public_key = private_key.public_key()

        # Сериализация ключей
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

    @staticmethod
    def sign_message(private_key_pem, message):
        """Подписание сообщения приватным ключом"""
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend = default_backend()
            )

            signature = private_key.sign(
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"❌ Ошибка подписи: {e}")
            return None

    @staticmethod
    def verify_signature(public_key_pem, message, signature):
        """Проверка подписи публичным ключом"""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend = default_backend()
            )

            signature_bytes = base64.b64decode(signature)

            public_key.verify(
                signature_bytes,
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"❌ Ошибка проверки подписи: {e}")
            return False

    @staticmethod
    def generate_challenge():
        """Генерация challenge сообщения для подписи"""
        return f"CRYPTOPRO_AUTH_{secrets.token_urlsafe(32)}"


# Глобальный экземпляр
rsa_manager = RSAManager()