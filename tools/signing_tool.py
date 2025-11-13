# tools/signing_tool.py
import os
import sys
import getpass

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.backend.rsa_manager import rsa_manager, KeyStorageManager


def sign_message_secure():
    """Безопасная утилита для подписи сообщений"""
    print("🛠️ Безопасная утилита для подписи RSA ключами")
    print("=" * 50)

    keys_dir = KeyStorageManager.get_keys_directory()
    key_files = [f for f in os.listdir(keys_dir) if f.endswith('_encrypted.key')]

    if not key_files:
        print("❌ Зашифрованные ключи не найдены!")
        print("💡 Сначала запустите tools/generate_keys.py")
        return

    print("📁 Доступные зашифрованные ключи:")
    for i, key_file in enumerate(key_files, 1):
        member_name = key_file.replace('_encrypted.key', '')
        print(f" {i}. {member_name}")

    try:
        choice = int(input("\n🎯 Выберите номер вашего ключа: ")) - 1
        if choice < 0 or choice >= len(key_files):
            print("❌ Неверный выбор!")
            return

        selected_key = key_files[choice]
        member_name = selected_key.replace('_encrypted.key', '')

        # Запрашиваем пароль для расшифровки
        password = getpass.getpass(f"Введите пароль для ключа {member_name}: ")

        # Загружаем и расшифровываем ключ
        private_key = KeyStorageManager.load_private_key(member_name, password)

        print(f"✅ Ключ {member_name} успешно загружен!")

        print("📋 Введите challenge-сообщение с сайта:")
        message = input("Challenge: ").strip()

        if not message:
            print("❌ Сообщение не может быть пустым!")
            return

        # Подписываем сообщение
        print("🔐 Подписываем сообщение...")
        signature = rsa_manager.sign_message(private_key, message)

        if signature:
            print("\n" + "=" * 50)
            print("✅ СООБЩЕНИЕ УСПЕШНО ПОДПИСАНО!")
            print("=" * 50)
            print(f"🔐 Цифровая подпись:")
            print(signature)
            print("\n💡 Скопируйте ЭТУ подпись и вставьте в форму на сайте")
            print("=" * 50)
        else:
            print("❌ Ошибка при подписи сообщения!")

    except ValueError as e:
        print(f"❌ Ошибка: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    sign_message_secure()