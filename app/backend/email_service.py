import smtplib
from email.mime.text import MIMEText  # ← ИСПРАВЛЕНО: MimeText на MIMEText
from email.mime.multipart import MIMEMultipart  # ← ИСПРАВЛЕНО: MimeMultipart на MIMEMultipart
import os
from datetime import datetime, timedelta


class EmailService:
    def __init__(self, app=None):
        self.app = app
        self.smtp_server = None
        self.port = None
        self.username = None
        self.password = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Инициализирует email сервис с конфигурацией приложения"""
        self.smtp_server = app.config['MAIL_SERVER']
        self.port = app.config['MAIL_PORT']
        self.username = app.config['MAIL_USERNAME']
        self.password = app.config['MAIL_PASSWORD']

    def send_key_share(self, email, key_share, session_token):
        """
        Отправляет часть ключа на email
        """
        subject = "🔐 Ваша часть ключа для доступа к крипто-кошельку"

        # Создаем красивый email
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333; text-align: center;">Крипто-Кошелек команды</h2>
                <p style="color: #666; font-size: 16px;">Здравствуйте!</p>
                <p style="color: #666; font-size: 16px;">Для входа в кошелек вашей команды используйте следующую часть ключа:</p>

                <div style="background-color: #f8f9fa; border: 2px dashed #dee2e6; padding: 20px; margin: 20px 0; text-align: center; border-radius: 5px;">
                    <code style="font-size: 18px; font-weight: bold; color: #e83e8c; letter-spacing: 1px;">{key_share}</code>
                </div>

                <p style="color: #666; font-size: 14px;">
                    <strong>Важно:</strong><br>
                    • Этот ключ действителен только для текущей сессии<br>
                    • Объедините этот ключ с ключами других участников<br>
                    • Порядок ключей не имеет значения<br>
                    • Ключ будет автоматически недействителен через 15 минут
                </p>

                <div style="text-align: center; margin-top: 30px; padding: 15px; background-color: #e9ecef; border-radius: 5px;">
                    <p style="margin: 0; color: #495057; font-size: 12px;">
                        Токен сессии: {session_token}<br>
                        Отправлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            self.send_email(email, subject, body)
            return True
        except Exception as e:
            print(f"Ошибка отправки email: {str(e)}")
            return False

    def send_email(self, to_email, subject, body):
        """Отправляет email"""
        msg = MIMEMultipart()  # ← ИСПРАВЛЕНО: MimeMultipart на MIMEMultipart
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject

        # Добавляем HTML тело
        msg.attach(MIMEText(body, 'html'))  # ← ИСПРАВЛЕНО: MimeText на MIMEText

        # Подключаемся к серверу и отправляем
        server = smtplib.SMTP(self.smtp_server, self.port)
        server.starttls()
        server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()


# Создаем глобальный экземпляр
email_service = EmailService()