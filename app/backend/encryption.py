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

        # Преобразуем секрет в число
        secret_int = int.from_bytes(secret, 'big')

        # Генерируем случайные коэффициенты для полинома
        coefficients = [secret_int] + [secrets.randbelow(2 ** 128) for _ in range(threshold - 1)]

        shares_list = []
        for i in range(1, shares + 1):
            # Вычисляем значение полинома в точке i
            # polynomial: secret + coeff1*x + coeff2*x^2 + ...
            share_value = 0
            for power, coeff in enumerate(coefficients):
                share_value += coeff * (i ** power)

            # Сохраняем share как строку (индекс:значение)
            share_str = f"{i}:{share_value}"
            shares_list.append(share_str)

        return shares_list

    @staticmethod
    def reconstruct_secret(shares):
        """
        Восстанавливает секрет из частей (упрощенная версия)
        Работает с любыми 3 из 4 ключей
        """
        try:
            if len(shares) < 3:
                raise ValueError("Нужно минимум 3 ключа")

            # Парсим ключи
            points = []
            for share in shares:
                if ':' in share:
                    idx_str, value_str = share.split(':', 1)
                    try:
                        x = int(idx_str)
                        y = int(value_str)
                        points.append((x, y))
                    except ValueError:
                        continue

            if len(points) < 3:
                raise ValueError("Недостаточно валидных ключей")

            # Берем первые 3 точки для восстановления
            points = points[:3]

            # Упрощенная интерполяция Лагранжа для 3 точек
            x1, y1 = points[0]
            x2, y2 = points[1]
            x3, y3 = points[2]

            # Восстанавливаем секрет при x=0
            secret_int = (
                    y1 * (x2 * x3) // ((x1 - x2) * (x1 - x3)) +
                    y2 * (x1 * x3) // ((x2 - x1) * (x2 - x3)) +
                    y3 * (x1 * x2) // ((x3 - x1) * (x3 - x2))
            )

            # Преобразуем обратно в байты
            secret_bytes = secret_int.to_bytes((secret_int.bit_length() + 7) // 8, 'big')

            # Убираем возможные нулевые байты в начале
            secret_bytes = secret_bytes.lstrip(b'\x00')

            return secret_bytes.decode('utf-8', errors='ignore')

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