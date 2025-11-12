# test_connection.py
import requests
import time


def test_blockchain():
    print("🧪 Тестируем блокчейн...")
    try:
        response = requests.get("http://localhost:5001/api/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Блокчейн работает! Порт: {data.get('port', 'unknown')}")
            return True
        else:
            print(f"❌ Блокчейн недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к блокчейну: {e}")
        return False


def test_wallet():
    print("🧪 Тестируем кошелек...")
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        if response.status_code == 200:
            print("✅ Кошелек работает!")
            return True
        else:
            print(f"❌ Кошелек недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к кошельку: {e}")
        return False


def test_api_methods():
    print("🧪 Тестируем API методы...")

    # Тестируем основные endpoints
    endpoints = [
        "/api/wallets",
        "/api/blockchain",
        "/api/pending_transactions"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:5001{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - работает")
            else:
                print(f"⚠️  {endpoint} - код: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - ошибка: {e}")


if __name__ == "__main__":
    print("🚀 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ")
    print("=" * 50)

    # Даем время на запуск систем
    print("⏳ Ожидаем запуск систем...")
    time.sleep(2)

    blockchain_ok = test_blockchain()
    wallet_ok = test_wallet()

    if blockchain_ok and wallet_ok:
        print("\n🎉 ОБЕ СИСТЕМЫ РАБОТАЮТ!")
        test_api_methods()
    else:
        print("\n⚠️  Есть проблемы с подключением")

    print("=" * 50)