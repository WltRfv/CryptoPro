# tools/generate_rsa_keys.py
import os
import sys
import getpass

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.backend.database import db, Member, PublicKey
from app.backend.rsa_manager import rsa_manager


def generate_rsa_keys():
    """Генерация RSA ключей и регистрация в системе"""
    app = create_app()

    with app.app_context():
        print("🔐 ГЕНЕРАЦИЯ RSA КЛЮЧЕЙ")
        print("=" * 50)

        # Получаем всех участников
        members = Member.query.filter_by(is_teacher=False).all()

        if not members:
            print("❌ Участники не найдены в базе!")
            return

        print("👥 Найдены участники:")
        for member in members:
            print(f" - {member.name}")

        # Создаем папку для ключей
        keys_dir = "rsa_keys"
        os.makedirs(keys_dir, exist_ok=True)

        for member in members:
            print(f"\n🎯 Генерация ключей для: {member.name}")

            # Удаляем старый ключ если есть
            old_key = PublicKey.query.filter_by(member_id=member.id).first()
            if old_key:
                db.session.delete(old_key)
                db.session.commit()
                print("   ✅ Старый ключ удален")

            # Генерируем новую пару ключей
            private_key, public_key = rsa_manager.generate_key_pair()

            # Сохраняем публичный ключ в базу
            new_key = PublicKey(
                member_id=member.id,
                public_key=public_key
            )
            db.session.add(new_key)

            # Сохраняем приватный ключ в файл
            key_filename = f"{member.name}_private.pem"
            key_path = os.path.join(keys_dir, key_filename)

            with open(key_path, 'w', encoding='utf-8') as f:
                f.write(private_key)

            print(f"   ✅ Публичный ключ сохранен в БД")
            print(f"   ✅ Приватный ключ сохранен: {key_path}")
            print(f"   🔑 Приватный ключ (первые 100 символов):")
            print(f"      {private_key[:100]}...")

        db.session.commit()
        print("\n" + "=" * 50)
        print("🎯 ВСЕ RSA КЛЮЧИ УСПЕШНО СОЗДАНЫ!")
        print(f"📍 Приватные ключи: ./{keys_dir}/")
        print("📍 Публичные ключи: база данных")
        print("\n💡 Для входа в систему:")
        print("   1. Откройте https://localhost:5001")
        print("   2. Выберите участника")
        print("   3. Вставьте приватный ключ из соответствующего файла")


if __name__ == "__main__":
    generate_rsa_keys()