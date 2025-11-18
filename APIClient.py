"""
API клиент для взаимодействия с блокчейн сетью
"""

import requests
import json
from typing import Dict, List, Optional, Any
import time


class BlockchainAPIClient:
    """
    Клиент для взаимодействия с блокчейн сетью через REST API
    """

    def __init__(self, base_url: str = None, port: int = 5001):
        if base_url is None:
            base_url = f"http://localhost:{port}"
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10

    def _make_request(self, endpoint: str, method: str = "GET",
                      data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Базовый метод для выполнения HTTP запросов
        """
        url = f"{self.base_url}/api/{endpoint}"
        print(f"🔗 Запрос к: {url}")  # Добавим отладку

        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                return {"error": f"Unsupported method: {method}"}

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text}"}

            return response.json()

        except requests.exceptions.ConnectionError:
            return {"error": f"Не удалось подключиться к {url}"}
        except requests.exceptions.Timeout:
            return {"error": "Таймаут подключения"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Ошибка сети: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Неверный JSON в ответе"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка: {str(e)}"}

    def ping(self) -> Dict[str, Any]:
        return self._make_request("ping")

    def get_wallets(self) -> Dict[str, Any]:
        return self._make_request("wallets")

    def get_blockchain(self) -> Dict[str, Any]:
        return self._make_request("blockchain")

    def create_transaction(self, transaction_type: str, receiver: str, amount: float = 0) -> Dict[str, Any]:
        data = {"type": transaction_type, "receiver": receiver, "amount": amount}
        return self._make_request("transaction", "POST", data)


class BlockchainClientFactory:
    @staticmethod
    def create_client(port: int = 5001):
        return BlockchainAPIClient(port=port)