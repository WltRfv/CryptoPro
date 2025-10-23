import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


class EmailService:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def send_key_share(self, to_email, key_share, session_token):
        """
        Отправляет ключ на email участника
        """
        try:
            # Получаем настройки из конфигурации Flask
            smtp_server = current_app.config.get('MAIL_SERVER')
            port = current_app.config.get('MAIL_PORT')
            username = current_app.config.get('MAIL_USERNAME')
            password = current_app.config.get('MAIL_PASSWORD')

            if not all([smtp_server, username, password]):
                print(f"❌ Не все настройки email заполнены для отправки на {to_email}")
                return False

            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = "🔑 Ключ для доступа к CryptoPro Кошельку"

            body = f"""
            🚀 Крипто-Кошелек CryptoPro

            Вы получили ключ для доступа к командному кошельку.

            📋 Токен сессии: {session_token}
            🔐 Ваш ключ: {key_share}

            💡 ИНСТРУКЦИЯ:
            1. Перейдите на страницу входа: http://localhost:5001
            2. Введите ЛЮБЫЕ 3 ключа из 4 (включая этот)
            3. Ключи вводите через пробел или запятую

            ⚠️  Для входа нужно минимум 3 ключа от разных участников!
            ⏱️  Ключ действителен 15 минут

            Команда CryptoPro 🤝
            """

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Отправляем email
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Ключ отправлен на {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"❌ Ошибка аутентификации при отправке на {to_email}")
            print("   Проверьте MAIL_USERNAME и MAIL_PASSWORD в .env")
            return False
        except Exception as e:
            print(f"❌ Ошибка отправки на {to_email}: {e}")
            return False


# Создаем глобальный экземпляр
email_service = EmailService()