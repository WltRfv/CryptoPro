# reset_database.py
import os
import shutil
from app import create_app
from app.backend.database import db
from app.backend.init_db import init_test_data


def reset_database():
    """Полностью пересоздает базу данных с ключами"""
    app = create_app()

    print("🔄 Полный сброс базы данных...")

    # Удаляем старую базу
    if os.path.exists('instance/wallet.db'):
        os.remove('instance/wallet.db')
        print("✅ Удалена старая база данных")

    # Удаляем старые ключи
    for folder in ['user_keys', 'distributed_keys']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"✅ Удалена папка {folder}")

    with app.app_context():
        # Создаем новую базу
        db.create_all()
        print("✅ Создана новая база данных")

        # Инициализируем тестовые данные
        init_test_data()
        print("✅ Тестовые данные добавлены")

        from tools.generate_keys import generate_all_keys
        generate_all_keys()
        print("✅ RSA ключи сгенерированы")

    print("🎯 База данных полностью пересоздана!")


if __name__ == "__main__":
    reset_database()