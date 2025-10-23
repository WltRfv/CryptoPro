import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()


def test_mail_ru_connection():
    print("🧪 Тестируем подключение к Mail.ru...")
    print("=" * 50)

    try:
        # Получаем настройки из .env
        smtp_server = os.getenv('MAIL_SERVER')
        port = int(os.getenv('MAIL_PORT'))
        username = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')

        print(f"🔧 Настройки из .env:")
        print(f"   Сервер: {smtp_server}")
        print(f"   Порт: {port}")
        print(f"   Пользователь: {username}")
        print(f"   Пароль: {'*' * len(password) if password else 'НЕТ'}")

        if not all([smtp_server, username, password]):
            print("❌ Не все настройки email заполнены в .env файле")
            print("   Проверьте что в .env есть:")
            print("   MAIL_SERVER=smtp.mail.ru")
            print("   MAIL_PORT=587")
            print("   MAIL_USERNAME=your_email@mail.ru")
            print("   MAIL_PASSWORD=your_password")
            return False

        # Подключаемся к серверу
        print("\n🔄 Подключаемся к серверу Mail.ru...")
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()

        # Логинимся
        print("🔄 Аутентифицируемся...")
        server.login(username, password)

        # Отправляем тестовое сообщение
        print("🔄 Отправляем тестовое сообщение...")
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = username  # Отправляем самому себе
        msg['Subject'] = "✅ Тест Crypto Wallet - Успех!"

        body = """
        Поздравляем! 

        Настройки Mail.ru работают корректно.
        Теперь ваш крипто-кошелек может отправлять ключи на email.

        🎉 Все готово к работе!
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server.send_message(msg)
        server.quit()

        print("=" * 50)
        print("✅ Тест пройден! Email отправлен успешно!")
        print("📧 Проверьте вашу почту Mail.ru - должно прийти тестовое письмо")
        print("🚀 Теперь можно запускать основное приложение: python run.py")
        return True

    except smtplib.SMTPAuthenticationError:
        print("=" * 50)
        print("❌ Ошибка аутентификации. Проверьте:")
        print("   - Правильность email в MAIL_USERNAME")
        print("   - Правильность пароля в MAIL_PASSWORD")
        print("   - Пароль должен быть ОТ ПОЧТЫ, не App Password")
        print("\n💡 Для Mail.ru используйте ОБЫЧНЫЙ пароль от почты")
        return False
    except Exception as e:
        print("=" * 50)
        print(f"❌ Ошибка: {e}")
        print("\n🔧 Возможные решения:")
        print("1. Проверьте интернет-подключение")
        print("2. Убедитесь что почта Mail.ru активна")
        print("3. Попробуйте другой пароль")
        return False


if __name__ == "__main__":
    test_mail_ru_connection()