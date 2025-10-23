from .database import db, Team, Member, Question
from .encryption_simple import password_hasher

# Импортируем из корневого config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config  # ИМПОРТИРУЕМ КЛАСС Config

from datetime import datetime

def init_test_data():
    """Инициализирует базу данных для ОДНОЙ команды"""
    db.drop_all()
    db.create_all()

    # Создаем ОДНУ команду
    team = Team(
        name="Наша команда",
        total_points=1000
    )
    db.session.add(team)
    db.session.flush()

    # Создаем 4 участника команды с фиксированными email
    for member_data in Config.TEAM_MEMBERS:  # ИСПОЛЬЗУЕМ Config.
        member = Member(
            name=member_data['name'],
            email=member_data['email'],
            personal_password=password_hasher.hash_password(member_data['personal_password']),
            points=member_data['points'],
            team_id=team.id,
            is_teacher=False
        )
        db.session.add(member)

    # Создаем преподавателя
    teacher = Member(
        name="Преподаватель",
        email="teacher@university.ru",
        personal_password=password_hasher.hash_password(Config.TEACHER_PASSWORD),  # ИСПОЛЬЗУЕМ Config.
        points=Config.TEACHER_POINTS,  # ИСПОЛЬЗУЕМ Config.
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
        print("✅ База данных инициализирована для ОДНОЙ команды!")
        print("📧 Email участников:")
        for email in Config.TEAM_EMAILS:  # ИСПОЛЬЗУЕМ Config.
            print(f" - {email}")
        print(f"\n👨‍🏫 Преподаватель создан с паролем: {Config.TEACHER_PASSWORD}")  # ИСПОЛЬЗУЕМ Config.
        print("\n🔑 Личные логины:")
        for member in Config.TEAM_MEMBERS:  # ИСПОЛЬЗУЕМ Config.
            print(f" - {member['name']} / {member['personal_password']}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка: {str(e)}")
        raise