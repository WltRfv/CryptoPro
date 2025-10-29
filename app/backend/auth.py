"""from flask import current_app
from datetime import datetime, timedelta
import secrets
from .database import db, LoginSession, KeyShare, Team, Member
from .encryption_simple import shamir_manager, password_hasher
from .email_service import email_service
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config  # ИМПОРТИРУЕМ КЛАСС Config

class AuthManager:
    TEAM_EMAILS = Config.TEAM_EMAILS  # ИСПОЛЬЗУЕМ Config.
    TEAM_MEMBERS = Config.TEAM_MEMBERS  # ИСПОЛЬЗУЕМ Config.

    @staticmethod
    def initiate_team_login():

        #Инициирует процесс входа для команды - отправляет ключи на все email

        try:
            print("🔄 Инициируем вход команды...")
            print(f"📧 Порядок email в конфиге: {AuthManager.TEAM_EMAILS}")

            # Создаем токен сессии
            session_token = shamir_manager.generate_session_token()

            # Создаем мастер-ключ для этой сессии
            master_key = secrets.token_urlsafe(32)

            # Разделяем ключ на 4 части (порядок важен!)
            shares = shamir_manager.split_secret(master_key, shares=4, threshold=3)

            # ОТЛАДКА: покажем какой ключ кому отправляется
            print("🔑 РАСПРЕДЕЛЕНИЕ КЛЮЧЕЙ:")
            for i, email in enumerate(AuthManager.TEAM_EMAILS):
                print(f"  {email} → Ключ {i + 1}: {shares[i][:20]}...")

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
                print(f"📨 Отправка ключа {i + 1} на {email}: {shares[i]}")
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
                    print(f"✅ Ключ {i + 1} отправлен на {email}")
                else:
                    print(f"❌ Ошибка отправки ключа {i + 1} на {email}")

            db.session.commit()

            # Сохраняем ключи в файл для тестирования
            AuthManager._save_test_keys(shares, session_token)

            if email_count > 0:
                return session_token, f"Ключи отправлены на {email_count} email адресов! Также сохранены в файл test_keys.txt"
            else:
                return session_token, "Ключи сохранены в файл test_keys.txt (проверьте настройки email)"

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в initiate_team_login: {e}")
            # Возвращаем значения по умолчанию чтобы не ломать интерфейс
            return "ERROR", f"Ошибка при отправке ключей: {str(e)}"

    @staticmethod
    def _save_test_keys(shares, session_token):
        #Сохраняет ключи в файл для тестирования
        try:
            with open('test_keys.txt', 'w', encoding='utf-8') as f:
                f.write("🔐 ТЕСТОВЫЕ КЛЮЧИ ДЛЯ ВХОДА В КРИПТО-КОШЕЛЕК\n")
                f.write("=" * 60 + "\n")
                f.write(f"Токен сессии: {session_token}\n")
                f.write(f"Время генерации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
                f.write("Ключи (введите ЛЮБЫЕ 3 из 4 через пробел):\n")

                # Записываем ключи с указанием email и номера
                emails = ["samonov.135@gmail.com", "galkinasnezana788@gmail.com",
                         "lesa85130@gmail.com", "pravolavika@gmail.com"]
                for i, share in enumerate(shares, 1):
                    f.write(f"Ключ {i} ({emails[i - 1]}): {share}\n")

                f.write("\n💡 ДОПУСТИМЫЕ КОМБИНАЦИИ:\n")
                f.write("1-2-3, 1-2-4, 1-3-4, 2-3-4\n\n")
                f.write("📋 ТЕСТОВЫЕ КОМБИНАЦИИ (скопируйте и вставьте):\n")
                f.write(f"1-2-3: {shares[0]} {shares[1]} {shares[2]}\n")
                f.write(f"1-2-4: {shares[0]} {shares[1]} {shares[3]}\n")
                f.write(f"1-3-4: {shares[0]} {shares[2]} {shares[3]}\n")
                f.write(f"2-3-4: {shares[1]} {shares[2]} {shares[3]}\n")
                f.write("=" * 60 + "\n")

            print("✅ Ключи сохранены в файл test_keys.txt")
            print("📁 Откройте файл test_keys.txt чтобы увидеть ключи для тестирования")
        except Exception as e:
            print(f"❌ Ошибка сохранения ключей в файл: {e}")

    @staticmethod
    def verify_combined_key(entered_keys, session_token):

        #Проверяет комбинацию из 3 или 4 ключей СТРОГО по допустимым комбинациям

        print(f"🔍 Проверяем ключи для сессии: {session_token}")
        print(f"Введенные ключи: {entered_keys}")

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

        # Получаем все ключи этой сессии из БД
        all_shares = KeyShare.query.filter_by(
            session_id=session.id,
            is_used=False
        ).order_by(KeyShare.share_order).all()

        if len(all_shares) != 4:
            return False, "Не все ключи доступны"

        # Создаем словарь эталонных ключей из БД
        db_shares_dict = {share.share_order: share.share for share in all_shares}
        print(f"Ключи в БД: {db_shares_dict}")

        # Проверяем введенные ключи
        try:
            # Пытаемся восстановить секрет с введенными ключами
            reconstructed = shamir_manager.reconstruct_secret(entered_keys)

            # Если восстановление успешно - проверяем что ключи совпадают с БД
            if reconstructed == "SUCCESS_SECRET_RECONSTRUCTED":
                # Помечаем ключи как использованные
                for share in all_shares:
                    share.is_used = True
                    share.used_at = datetime.utcnow()

                # Деактивируем сессию
                session.is_active = False
                db.session.commit()

                print("✅ Успешная аутентификация команды!")
                return True, "Успешный вход в кошелек!"
            else:
                return False, "Неверная комбинация ключей"

        except ValueError as e:
            print(f"❌ Ошибка проверки ключей: {e}")
            return False, str(e)
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False, "Ошибка проверки ключей"

    @staticmethod
    def verify_personal_login(member_name, personal_password):

        #Проверяет личный логин участника (для операций внутри кошелька)

        member = Member.query.filter_by(name=member_name).first()
        if member and password_hasher.verify_password(personal_password, member.personal_password):
            return member, True
        return None, False

# Создаем глобальный экземпляр
auth_manager = AuthManager()"""


from flask import current_app
from datetime import datetime, timedelta
import secrets
from .database import db, LoginSession
from .signature_auth import signature_auth


class AuthManager:
    """Временный класс-заглушка для совместимости"""

    @staticmethod
    def initiate_team_login():
        """Инициирует процесс входа через цифровые подписи"""
        return signature_auth.initiate_team_login()


# Создаем экземпляр для совместимости
auth_manager = AuthManager()