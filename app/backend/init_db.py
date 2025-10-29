# app/backend/init_db.py - ЗАМЕНИ весь код на:
from .database import db, Team, Member, Question, PublicKey
from .encryption_simple import password_hasher
from .rsa_manager import rsa_manager

# Импортируем из корневого config.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

from datetime import datetime


def init_test_data():
    """Инициализирует базу данных с RSA ключами"""
    db.drop_all()
    db.create_all()

    # Создаем ОДНУ команду
    team = Team(
        name="Наша команда",
        total_points=1000
    )
    db.session.add(team)
    db.session.flush()

    # Создаем 4 участника команды
    for member_data in Config.TEAM_MEMBERS:
        member = Member(
            name=member_data['name'],
            email=member_data['email'],
            personal_password=password_hasher.hash_password(member_data['personal_password']),
            points=member_data['points'],
            team_id=team.id,
            is_teacher=False
        )
        db.session.add(member)
        db.session.flush()  # Получаем ID участника

        # Генерируем RSA ключи для участника
        private_key, public_key = rsa_manager.generate_key_pair()

        # Сохраняем публичный ключ в базу
        public_key_record = PublicKey(
            member_id=member.id,
            public_key=public_key
        )
        db.session.add(public_key_record)

        # Сохраняем приватный ключ в файл для тестирования
        keys_dir = "user_keys"
        os.makedirs(keys_dir, exist_ok=True)
        with open(f"{keys_dir}/{member_data['name']}_private.pem", "w") as f:
            f.write(private_key)
        print(f"✅ Сгенерирован ключ для {member_data['name']}")

    # Создаем преподавателя
    teacher = Member(
        name="Преподаватель",
        email="teacher@university.ru",
        personal_password=password_hasher.hash_password(Config.TEACHER_PASSWORD),
        points=Config.TEACHER_POINTS,
        team_id=team.id,
        is_teacher=True
    )
    db.session.add(teacher)

    # Создаем тестовые вопросы
    questions_data = [
        {'content': 'Что такое блокчейн и как он обеспечивает безопасность?', 'price': 100},
        {'content': 'Объясните принцип работы Proof-of-Work vs Proof-of-Stake', 'price': 150},
        {'content': 'Как работает механизм хеширования в криптографии?', 'price': 120},
        {'content': 'Что такое смарт-контракты и их применение?', 'price': 200},
    ]

    for question_data in questions_data:
        question = Question(
            content=question_data['content'],
            price=question_data['price'],
            is_approved=True
        )
        db.session.add(question)

    try:
        db.session.commit()
        print("✅ База данных инициализирована с RSA ключами!")
        print("📁 Приватные ключи сохранены в папку user_keys/")
        print("🔐 Каждый участник имеет свою пару RSA ключей")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка: {str(e)}")
        raise