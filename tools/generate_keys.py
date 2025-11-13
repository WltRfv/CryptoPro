# tools/generate_keys.py
import os
import sys
import getpass

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.backend.database import db, Member, PublicKey
from app.backend.rsa_manager import rsa_manager, KeyStorageManager


def generate_encrypted_keys():
    """Генерирует ключи с шифрованием"""
    app = create_app()

    with app.app_context():
        print("🔐 Генерация ЗАШИФРОВАННЫХ RSA ключей для всех участников...")

        # Получаем всех участников
        members = Member.query.filter_by(is_teacher=False).all()

        if not members:
            print("❌ Участники не найдены в базе!")
            return

        print("👥 Найдены участники:")
        for member in members:
            print(f" - {member.name}")

        for member in members:
            print(f"\n🔑 Генерируем ключи для {member.name}...")

            # Запрашиваем пароль для шифрования
            while True:
                password = getpass.getpass(f"Введите пароль для шифрования ключа {member.name}: ")
                password_confirm = getpass.getpass("Повторите пароль: ")

                if password == password_confirm:
                    break
                else:
                    print("❌ Пароли не совпадают! Попробуйте снова.")

            # Удаляем старый ключ если есть
            old_key = PublicKey.query.filter_by(member_id=member.id).first()
            if old_key:
                db.session.delete(old_key)
                db.session.commit()

            # Генерируем новую пару ключей
            private_key, public_key = rsa_manager.generate_key_pair()

            # Сохраняем публичный ключ в базу
            new_key = PublicKey(
                member_id=member.id,
                public_key=public_key
            )
            db.session.add(new_key)

            # Сохраняем ЗАШИФРОВАННЫЙ приватный ключ
            KeyStorageManager.save_encrypted_private_key(member.name, private_key, password)

            print(f"✅ Ключи для {member.name} созданы и зашифрованы!")

        db.session.commit()
        print("\n🎯 ВСЕ КЛЮЧИ СОЗДАНЫ И ЗАШИФРОВАНЫ!")


if __name__ == "__main__":
    generate_encrypted_keys()