# tools/verify_keys.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.backend.database import db, Member, PublicKey
from app.backend.rsa_manager import rsa_manager


def verify_all_keys():
    """Проверяет что все ключи правильно сгенерированы и работают"""
    app = create_app()

    with app.app_context():
        print("🔍 ПРОВЕРКА RSA КЛЮЧЕЙ")
        print("=" * 50)

        members = Member.query.filter_by(is_teacher=False).all()

        if not members:
            print("❌ Участники не найдены!")
            return

        keys_dir = "rsa_keys"

        for member in members:
            print(f"\n🎯 Проверка ключей: {member.name}")

            # Проверяем публичный ключ в БД
            pub_key = PublicKey.query.filter_by(member_id=member.id).first()
            if not pub_key:
                print("   ❌ Публичный ключ не найден в БД")
                continue

            print("   ✅ Публичный ключ найден в БД")

            # Проверяем приватный ключ в файле
            key_path = os.path.join(keys_dir, f"{member.name}_private.pem")
            if not os.path.exists(key_path):
                print("   ❌ Приватный ключ не найден в файле")
                continue

            with open(key_path, 'r', encoding='utf-8') as f:
                private_key = f.read()

            print("   ✅ Приватный ключ найден в файле")

            # Тестируем подпись и проверку
            test_message = f"Test message for {member.name}"

            try:
                # Подписываем сообщение
                signature = rsa_manager.sign_message(private_key, test_message)

                # Проверяем подпись
                is_valid = rsa_manager.verify_signature(pub_key.public_key, test_message, signature)

                if is_valid:
                    print("   ✅ Подпись и проверка работают корректно")
                else:
                    print("   ❌ Ошибка проверки подписи")

            except Exception as e:
                print(f"   ❌ Ошибка при работе с ключами: {e}")

        print("\n" + "=" * 50)
        print("🎯 ПРОВЕРКА ЗАВЕРШЕНА!")


if __name__ == "__main__":
    verify_all_keys()