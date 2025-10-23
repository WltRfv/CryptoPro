from flask import current_app
from datetime import datetime, timedelta
import secrets
from .database import db, LoginSession, KeyShare, Team, Member
from .encryption import shamir_manager, password_hasher
from .email_service import email_service
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import TEAM_EMAILS, TEAM_MEMBERS


class AuthManager:
    TEAM_EMAILS = TEAM_EMAILS
    TEAM_MEMBERS = TEAM_MEMBERS

    @staticmethod
    def initiate_team_login():
        """
        Инициирует процесс входа для команды - отправляет ключи на все email
        """
        print("🔄 Инициируем вход команды...")

        # Создаем токен сессии
        session_token = shamir_manager.generate_session_token()

        # Создаем мастер-ключ для этой сессии
        master_key = secrets.token_urlsafe(24)

        # Разделяем ключ на 4 части (порядок важен!)
        shares = shamir_manager.split_secret(master_key, shares=4, threshold=3)

        # Создаем запись сессии
        login_session = LoginSession(
            session_token=session_token,
            expires_at=datetime.utcnow() + timedelta(minutes=15)
        )
        db.session.add(login_session)
        db.session.flush()

        # Сохраняем ключи в базу и отправляем на email
        email_count = 0
        for i, email in enumerate(AuthManager.TEAM_EMAILS):
            key_share = KeyShare(
                share=shares[i],
                email=email,
                share_order=i + 1,  # Порядок 1,2,3,4
                session_id=login_session.id
            )
            db.session.add(key_share)

            # Отправляем email с ключом
            if email_service.send_key_share(email, shares[i], session_token):
                email_count += 1

        db.session.commit()

        # Сохраняем ключи в файл для тестирования
        AuthManager._save_test_keys(shares, session_token)

        if email_count > 0:
            return session_token, f"Ключи отправлены на {email_count} email адресов! Также сохранены в файл test_keys.txt"
        else:
            return session_token, "Ключи сохранены в файл test_keys.txt (проверьте настройки email)"

    @staticmethod
    def _save_test_keys(shares, session_token):
        """Сохраняет ключи в файл для тестирования"""
        try:
            with open('test_keys.txt', 'w', encoding='utf-8') as f:
                f.write("🔐 ТЕСТОВЫЕ КЛЮЧИ ДЛЯ ВХОДА В КРИПТО-КОШЕЛЕК\n")
                f.write("=" * 60 + "\n")
                f.write(f"Токен сессии: {session_token}\n")
                f.write(f"Время генерации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
                f.write("Ключи (введите ЛЮБЫЕ 3 из 4 через пробел):\n")
                for i, share in enumerate(shares, 1):
                    f.write(f"Ключ {i}: {share}\n")
                f.write("\n💡 ИНСТРУКЦИЯ:\n")
                f.write("1. Скопируйте ЛЮБЫЕ 3 ключа из 4\n")
                f.write("2. Вставьте на странице входа через пробел\n")
                f.write("3. Пример ввода: 1:значение 2:значение 3:значение\n")
                f.write("4. Или: 1:значение 2:значение 4:значение\n")
                f.write("=" * 60 + "\n")

            print("✅ Ключи сохранены в файл test_keys.txt")
            print("📁 Откройте файл test_keys.txt чтобы увидеть ключи для тестирования")

        except Exception as e:
            print(f"❌ Ошибка сохранения ключей в файл: {e}")

    @staticmethod
    def verify_combined_key(entered_keys, session_token):
        """
        Проверяет комбинацию из 3 или 4 ключей
        """
        print(f"🔍 Проверяем ключи для сессии: {session_token}")

        # Находим активную сессию
        session = LoginSession.query.filter_by(
            session_token=session_token,
            is_active=True
        ).first()

        if not session:
            return False, "Сессия не найдена или неактивна"

        if datetime.utcnow() > session.expires_at:
            session.is_active = False
            db.session.commit()
            return False, "Время сессии истекло"

        # Получаем все ключи этой сессии
        all_shares = KeyShare.query.filter_by(
            session_id=session.id,
            is_used=False
        ).all()

        if len(all_shares) != 4:
            return False, "Не все ключи доступны"

        # Создаем словарь ключей по порядку
        shares_dict = {share.share_order: share.share for share in all_shares}

        # Проверяем все возможные комбинации из 3 ключей
        valid_combinations = [
            [1, 2, 3], [1, 2, 4], [1, 3, 4], [2, 3, 4], [1, 2, 3, 4]
        ]

        for combination in valid_combinations:
            # Проверяем, есть ли у нас все ключи для этой комбинации
            if all(order in shares_dict for order in combination):
                # Собираем ключи для проверки
                test_shares = [shares_dict[order] for order in combination]

                try:
                    # Пытаемся восстановить мастер-ключ
                    reconstructed_key = shamir_manager.reconstruct_secret(test_shares)

                    # Если успешно - помечаем ключи как использованные
                    for order in combination:
                        key_share = KeyShare.query.filter_by(
                            session_id=session.id,
                            share_order=order,
                            is_used=False
                        ).first()
                        if key_share:
                            key_share.is_used = True
                            key_share.used_at = datetime.utcnow()

                    # Деактивируем сессию
                    session.is_active = False
                    db.session.commit()

                    print("✅ Успешная аутентификация команды!")
                    return True, "Успешный вход в кошелек!"

                except ValueError as e:
                    print(f"❌ Ошибка проверки комбинации {combination}: {e}")
                    continue

        return False, "Неверная комбинация ключей. Нужно минимум 3 правильных ключа."

    @staticmethod
    def verify_personal_login(member_name, personal_password):
        """
        Проверяет личный логин участника (для операций внутри кошелька)
        """
        member = Member.query.filter_by(name=member_name).first()
        if member and password_hasher.verify_password(personal_password, member.personal_password):
            return member, True
        return None, False


# Создаем глобальный экземпляр
auth_manager = AuthManager()