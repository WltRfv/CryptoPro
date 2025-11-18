# tools/signing_tool.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.backend.rsa_manager import rsa_manager


def sign_message_interactive():
    """Интерактивная утилита для подписи сообщений"""
    print("🛠️ Утилита для подписи RSA ключами")
    print("=" * 50)

    keys_dir = "user_keys"
    if not os.path.exists(keys_dir):
        print("❌ Папка с ключами не найдена!")
        print("💡 Сначала запустите tools/generate_keys.py")
        return

    key_files = [f for f in os.listdir(keys_dir) if f.endswith('_private.pem')]

    if not key_files:
        print("❌ Приватные ключи не найдены!")
        return

    print("📁 Доступные ключи:")
    for i, key_file in enumerate(key_files, 1):
        print(f"  {i}. {key_file}")

    try:
        choice = int(input("\n🎯 Выберите номер вашего ключа: ")) - 1
        if choice < 0 or choice >= len(key_files):
            print("❌ Неверный выбор!")
            return

        selected_key = key_files[choice]
        key_path = os.path.join(keys_dir, selected_key)

        # Читаем приватный ключ
        with open(key_path, 'r', encoding='utf-8') as f:
            private_key = f.read()

        print(f"\n🔑 Используем ключ: {selected_key}")
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

    except ValueError:
        print("❌ Введите корректный номер!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    sign_message_interactive()