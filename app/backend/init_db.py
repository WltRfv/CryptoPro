from .database import db, Team, User, Question
from .encryption import password_hasher
from datetime import datetime


def init_test_data():
    """Инициализирует базу данных тестовыми данными"""

    # Очищаем существующие данные (для разработки)
    db.drop_all()
    db.create_all()

    # Создаем тестовые команды
    teams_data = [
        {'name': 'Команда_Альфа', 'total_points': 1000},
        {'name': 'Команда_Бета', 'total_points': 800},
        {'name': 'Команда_Гамма', 'total_points': 1200},
    ]

    teams = []
    for team_data in teams_data:
        team = Team(
            name=team_data['name'],
            total_points=team_data['total_points']
        )
        db.session.add(team)
        teams.append(team)

    db.session.flush()

    # Создаем тестовых пользователей (УБИРАЕМ password_hash)
    users_data = [
        # Команда Альфа (4 человека)
        {'username': 'alex_alpha', 'email': 'alex.alpha@university.com', 'personal_password': 'pass123', 'points': 250,
         'team_id': teams[0].id},
        {'username': 'maria_alpha', 'email': 'maria.alpha@university.com', 'personal_password': 'pass123',
         'points': 250, 'team_id': teams[0].id},
        {'username': 'ivan_alpha', 'email': 'ivan.alpha@university.com', 'personal_password': 'pass123', 'points': 250,
         'team_id': teams[0].id},
        {'username': 'olga_alpha', 'email': 'olga.alpha@university.com', 'personal_password': 'pass123', 'points': 250,
         'team_id': teams[0].id},

        # Команда Бета (3 человека)
        {'username': 'dmitry_beta', 'email': 'dmitry.beta@university.com', 'personal_password': 'pass123',
         'points': 300, 'team_id': teams[1].id},
        {'username': 'anna_beta', 'email': 'anna.beta@university.com', 'personal_password': 'pass123', 'points': 250,
         'team_id': teams[1].id},
        {'username': 'sergey_beta', 'email': 'sergey.beta@university.com', 'personal_password': 'pass123',
         'points': 250, 'team_id': teams[1].id},

        # Команда Гамма (4 человека)
        {'username': 'ekaterina_gamma', 'email': 'ekaterina.gamma@university.com', 'personal_password': 'pass123',
         'points': 300, 'team_id': teams[2].id},
        {'username': 'pavel_gamma', 'email': 'pavel.gamma@university.com', 'personal_password': 'pass123',
         'points': 300, 'team_id': teams[2].id},
        {'username': 'natalia_gamma', 'email': 'natalia.gamma@university.com', 'personal_password': 'pass123',
         'points': 300, 'team_id': teams[2].id},
        {'username': 'mikhail_gamma', 'email': 'mikhail.gamma@university.com', 'personal_password': 'pass123',
         'points': 300, 'team_id': teams[2].id},
    ]

    for user_data in users_data:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            personal_password=password_hasher.hash_password(user_data['personal_password']),
            points=user_data['points'],
            team_id=user_data['team_id']
        )
        db.session.add(user)

    # Создаем тестовые вопросы
    questions_data = [
        {'content': 'Что такое блокчейн и как он обеспечивает безопасность?', 'price': 100, 'is_approved': True},
        {'content': 'Объясните принцип работы Proof-of-Work vs Proof-of-Stake', 'price': 150, 'is_approved': True},
        {'content': 'Как работает механизм хеширования в криптографии?', 'price': 120, 'is_approved': True},
        {'content': 'Что такое смарт-контракты и их применение?', 'price': 200, 'is_approved': True},
        {'content': 'Объясните разницу между публичными и приватными ключами', 'price': 80, 'is_approved': True},
        {'content': 'Как работает алгоритм консенсуса в распределенных системах?', 'price': 180, 'is_approved': False},
        {'content': 'Что такое децентрализованные финансы (DeFi)?', 'price': 220, 'is_approved': True},
        {'content': 'Объясните механизм масштабирования Lightning Network', 'price': 250, 'is_approved': True},
    ]

    for i, question_data in enumerate(questions_data):
        question = Question(
            content=question_data['content'],
            price=question_data['price'],
            is_approved=question_data['is_approved'],
            created_by=1 if i % 3 == 0 else 2
        )
        db.session.add(question)

    try:
        db.session.commit()
        print("✅ Тестовые данные успешно созданы!")
        print("📊 Создано:")
        print(f"   - Команд: {len(teams)}")
        print(f"   - Пользователей: {len(users_data)}")
        print(f"   - Вопросов: {len(questions_data)}")

        print("\n🔑 Тестовые логины для личного входа:")
        print("   Команда 'Команда_Альфа':")
        for user in users_data[:4]:
            print(f"   - {user['username']} / {user['personal_password']}")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при создании тестовых данных: {str(e)}")
        raise