from app import create_app
from app.backend.init_db import init_test_data
import os
import argparse
import sys

# Добавляем текущую директорию в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from blockchain_integration import blockchain_integration

    BLOCKCHAIN_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Blockchain integration unavailable: {e}")
    BLOCKCHAIN_INTEGRATION_AVAILABLE = False


def setup_blockchain_integration(blockchain_port):
    if not BLOCKCHAIN_INTEGRATION_AVAILABLE:
        print("⚠️  Blockchain integration disabled")
        return

    print(f"🎯 Настраиваем интеграцию с портом: {blockchain_port}")

    # Используем метод update_port если он есть, иначе пересоздаем
    if hasattr(blockchain_integration, 'update_port'):
        blockchain_integration.update_port(blockchain_port)
    else:
        # Старый способ
        blockchain_integration.blockchain_port = blockchain_port

    if blockchain_integration.initialize_integration():
        print("✅ Интеграция с блокчейном успешно настроена")
        status = blockchain_integration.get_blockchain_status()
        print(f"📊 Статус блокчейна: {status}")
    else:
        print("⚠️  Интеграция с блокчейном отключена")


def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description='CryptoPro Wallet')
    parser.add_argument('--port', type=int, default=5001, help='Port for CryptoPro wallet')
    parser.add_argument('--blockchain-port', type=int, default=5001, help='Port for blockchain ledger')
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

            # Регистрируем участников в блокчейне (если интеграция активна)
            if (BLOCKCHAIN_INTEGRATION_AVAILABLE and
                    blockchain_integration.is_active):

                print("🔗 Регистрация участников в блокчейн реестре...")
                from config import Config

                for member in Config.TEAM_MEMBERS:
                    result = blockchain_integration.register_member(member)
                    if "error" in result:
                        print(f"❌ Ошибка регистрации {member['name']}: {result['error']}")
                    else:
                        print(f"✅ Зарегистрирован: {member['name']}")
        else:
            print("✅ База данных уже существует")

    print(f"🚀 Запуск крипто-кошелька...")
    print(f"📍 Кошелек доступен по адресу: http://localhost:{args.port}")

    if BLOCKCHAIN_INTEGRATION_AVAILABLE and blockchain_integration.is_active:
        print(f"🔗 Блокчейн реестр: http://localhost:{args.blockchain_port}")
    else:
        print("⚠️  Блокчейн интеграция отключена")

    app.run(debug=True, host='0.0.0.0', port=args.port)