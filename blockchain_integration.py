"""
Сервис для интеграции CryptoPro кошелька с блокчейн реестром
"""

import sys
import os
from typing import Dict, List, Optional, Any

# Добавляем текущую директорию в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from APIClient import BlockchainAPIClient, BlockchainClientFactory
    BLOCKCHAIN_AVAILABLE = True
    print("✅ APIClient загружен успешно")
except ImportError as e:
    print(f"⚠️  APIClient не доступен: {e}")
    BLOCKCHAIN_AVAILABLE = False


class CryptoProBlockchainIntegration:
    """
    Сервис для синхронизации данных между CryptoPro кошельком и блокчейн реестром
    """

    def __init__(self, blockchain_port: int = 5001):  # ← ПОРТ ПО УМОЛЧАНИЮ 5001!
        if not BLOCKCHAIN_AVAILABLE:
            self.client = None
            self.is_active = False
            print("⚠️  Блокчейн интеграция отключена - APIClient не найден")
            return

        print(f"🔧 Инициализация клиента для порта: {blockchain_port}")
        self.client = BlockchainClientFactory.create_client(blockchain_port)
        self.is_active = False

    def update_port(self, new_port: int):
        """Обновляет порт блокчейна"""
        print(f"🔄 Обновление порта на: {new_port}")
        self.blockchain_port = new_port
        self.client = BlockchainClientFactory.create_client(new_port)
        self.is_active = False  # Сбрасываем статус, нужно переинициализировать

    def initialize_integration(self) -> bool:
        """
        Инициализирует интеграцию с блокчейном
        """
        if self.client is None:
            print("❌ Блокчейн клиент не инициализирован")
            return False

        try:
            # Проверяем доступность блокчейна
            print("🔗 Проверяем подключение к блокчейну...")
            ping_result = self.client.ping()

            if "error" in ping_result:
                print(f"❌ Блокчейн недоступен: {ping_result['error']}")
                return False
            else:
                print(f"✅ Блокчейн реестр доступен: {ping_result}")
                self.is_active = True
                return True

        except Exception as e:
            print(f"❌ Ошибка инициализации блокчейн интеграции: {e}")
            return False

    def get_blockchain_status(self) -> Dict[str, Any]:
        """
        Получает статус блокчейна
        """
        if not self.is_active or self.client is None:
            return {"error": "Блокчейн интеграция не активна"}

        try:
            # Получаем базовую информацию о блокчейне
            blockchain_info = self.client.get_blockchain()
            wallets_info = self.client.get_wallets()

            if "error" in blockchain_info:
                return {"error": blockchain_info["error"]}

            return {
                "status": "active",
                "blockchain_height": len(blockchain_info.get('chain', [])),
                "total_wallets": len(wallets_info) if not isinstance(wallets_info, dict) or "error" not in wallets_info else 0,
                "is_active": True
            }

        except Exception as e:
            return {"error": str(e), "is_active": False}



# Глобальный экземпляр интеграции
blockchain_integration = CryptoProBlockchainIntegration()