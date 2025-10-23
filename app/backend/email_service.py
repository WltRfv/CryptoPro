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
        Отправляет ключ на email участника с указанием номера ключа
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

            # Определяем номер ключа по email
            team_emails = [
                "samonov.135@gmail.com",  # Ключ 1
                "galkinasnezana788@gmail.com",  # Ключ 2
                "lesa85130@gmail.com",  # Ключ 3
                "pravolavika@gmail.com"  # Ключ 4
            ]

            key_number = team_emails.index(to_email) + 1 if to_email in team_emails else "?"
            print(f"📧 Отправляем ключ {key_number} на {to_email}")

            # Создаем сообщение - ИСПРАВЛЕННОЕ ФОРМАТИРОВАНИЕ
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = f"🔑 Ключ {key_number} для доступа к CryptoPro Кошельку"

            # ИСПРАВЛЕННОЕ ТЕЛО ПИСЬМА - без лишних отступов
            body = f"""🚀 Крипто-Кошелек CryptoPro

Вы получили ключ для доступа к командному кошельку.

📋 Токен сессии: {session_token}
🔐 Ваш ключ ({key_number}): {key_share}

💡 ИНСТРУКЦИЯ:
1. Перейдите на страницу входа: http://localhost:5001
2. Введите ЛЮБЫЕ 3 ключа из 4 (включая этот)
3. Ключи вводите через пробел или запятую

⚠️  Для входа нужно минимум 3 ключа от разных участников!
⏱️  Ключ действителен 15 минут

Команда CryptoPro 🤝"""

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Отправляем email
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()

            print(f"✅ Ключ {key_number} отправлен на {to_email}")
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