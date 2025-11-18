from app import create_app
from app.backend.init_db import init_test_data
import os
import argparse
import sys
import ssl

# Добавляем текущую директорию в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from blockchain_integration import blockchain_integration

    BLOCKCHAIN_INTEGRATION_AVAILABLE = True
except ImportError as e:
    BLOCKCHAIN_INTEGRATION_AVAILABLE = False


def setup_blockchain_integration(blockchain_port):
    if not BLOCKCHAIN_INTEGRATION_AVAILABLE:
        print("⚠️ Blockchain integration disabled")
        return

    print(f"🎯 Настраиваем интеграцию с портом: {blockchain_port}")

    try:
        if hasattr(blockchain_integration, 'update_port'):
            blockchain_integration.update_port(blockchain_port)
        else:
            blockchain_integration.blockchain_port = blockchain_port

        if blockchain_integration.initialize_integration():
            print("✅ Интеграция с блокчейном успешно настроена")
        else:
            print("⚠️ Блокчейн недоступен - работаем в автономном режиме")
    except Exception as e:
        print("⚠️ Блокчейн недоступен - работаем в автономном режиме")


def create_ssl_context():
    """Создает SSL контекст для HTTPS"""
    cert_file = 'localhost+2.pem'
    key_file = 'localhost+2-key.pem'

    if os.path.exists(cert_file) and os.path.exists(key_file):
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)
            print("✅ SSL сертификаты загружены")
            return context
        except Exception:
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                context.load_cert_chain(cert_file, key_file)
                print("✅ SSL сертификаты загружены")
                return context
            except Exception as e:
                print(f"❌ Ошибка загрузки SSL: {e}")
                return None
    else:
        print("❌ SSL файлы не найдены. Запустите: mkcert localhost 127.0.0.1 ::1")
        return None


def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description='CryptoPro Wallet')
    parser.add_argument('--port', type=int, default=5001, help='Port for CryptoPro wallet')
    parser.add_argument('--blockchain-port', type=int, default=5001, help='Port for blockchain ledger')
    parser.add_argument('--https', action='store_true', default=True, help='Enable HTTPS (default)')
    parser.add_argument('--http', action='store_true', help='Enable HTTP instead of HTTPS')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    app = create_app()

    # Настраиваем интеграцию с блокчейном
    setup_blockchain_integration(args.blockchain_port)

    with app.app_context():
        # Проверяем, нужно ли инициализировать базу
        if not os.path.exists('instance/wallet.db'):
            print("🔄 Инициализация базы данных с RSA ключами...")
            init_test_data()
            print("✅ База данных инициализирована")
        else:
            print("✅ База данных готова")

    ssl_context = None
    protocol = "https"

    # Включаем HTTPS по умолчанию, если не указан --http
    if not args.http:
        ssl_context = create_ssl_context()
        if not ssl_context:
            print("⚠️ Продолжаем без HTTPS")
            protocol = "http"
    else:
        protocol = "http"

    print(f"\n{'=' * 60}")
    print(f"🚀 CRYPTOPRO КОШЕЛЕК ЗАПУЩЕН!")
    print(f"📍 Адрес: {protocol}://127.0.0.1:{args.port}")
    if protocol == "https":
        print(f"🔒 HTTPS активирован - в браузере будет ЗАМОК")
    print(f"{'=' * 60}\n")

    # Запуск с HTTPS если доступно
    if ssl_context:
        app.run(debug=True, host='127.0.0.1', port=args.port, ssl_context=ssl_context, use_reloader=False)
    else:
        app.run(debug=True, host='127.0.0.1', port=args.port, use_reloader=False)