# tools/generate_keys.py
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.backend.database import db, Member, PublicKey
from app.backend.rsa_manager import rsa_manager


# tools/generate_keys.py - ИСПРАВЛЯЕМ ОШИБКУ
def generate_all_keys():
    """Генерирует ключи для всех участников"""
    app = create_app()

    with app.app_context():
        print("🔐 Генерация RSA ключей для всех участников...")

        # Получаем всех участников (без преподавателя)
        members = Member.query.filter_by(is_teacher=False).all()

        if not members:
            print("❌ Участники не найдены в базе!")
            return

        print("👥 Найдены участники:")
        for member in members:
            print(f" - {member.name}")

        # Создаем папку для ключей
        keys_dir = "user_keys"
        os.makedirs(keys_dir, exist_ok=True)

        for member in members:
            print(f"🔑 Генерируем ключи для {member.name}...")

            # Удаляем старый ключ если есть (исправляем ошибку)
            old_key = PublicKey.query.filter_by(member_id=member.id).first()
            if old_key:
                db.session.delete(old_key)
                db.session.commit()  # 🔴 КОММИТИМ УДАЛЕНИЕ

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

            print(f"✅ Создан ключ: {key_filename}")

        db.session.commit()
        print("🎯 ВСЕ КЛЮЧИ СОЗДАНЫ!")


if __name__ == "__main__":
    generate_all_keys()