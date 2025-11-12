import os
from dotenv import load_dotenv

load_dotenv()


class BlockchainConfig:
    # Настройки блокчейн реестра
    DEFAULT_PORT = 5000
    PORTS_RANGE = range(5000, 5011)  # Порты 5000-5010

    @classmethod
    def get_api_url(cls, port=None):
        port = port or cls.DEFAULT_PORT
        return f"http://localhost:{port}"