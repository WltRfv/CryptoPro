# final_test.py
import requests
import time
import json


def test_complete_flow():
    print("🎯 ПОЛНЫЙ ТЕСТ ИНТЕГРАЦИИ")
    print("=" * 60)

    # 1. Тест доступности
    print("1. 📡 Проверка доступности сервисов...")
    try:
        wallet_response = requests.get("http://localhost:5000/")
        blockchain_response = requests.get("http://localhost:5001/api/ping")
        print("   ✅ Оба сервиса доступны")
    except:
        print("   ❌ Сервисы недоступны")
        return

    # 2. Тест API блокчейна
    print("2. 🔗 Тест API блокчейна...")
    endpoints = [
        "/api/wallets",
        "/api/blockchain",
        "/api/pending_transactions"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:5001{endpoint}")
            if response.status_code == 200:
                print(f"   ✅ {endpoint} - работает")
            else:
                print(f"   ❌ {endpoint} - ошибка: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint} - исключение: {e}")

    # 3. Тест создания транзакции
    print("3. 💸 Тест создания транзакции...")
    try:
        transaction_data = {
            "type": "transfer",
            "receiver": "test_wallet",
            "amount": 10
        }
        response = requests.post("http://localhost:5001/api/transaction",
                                 json=transaction_data)
        if response.status_code == 200:
            print("   ✅ Транзакция создана успешно")
            tx_data = response.json()
            print(f"   📦 ID транзакции: {tx_data.get('transaction', {}).get('transaction_id', 'unknown')}")
        else:
            print(f"   ❌ Ошибка создания транзакции: {response.text}")
    except Exception as e:
        print(f"   ❌ Исключение при создании транзакции: {e}")

    # 4. Проверка pending транзакций
    print("4. 📋 Проверка pending транзакций...")
    try:
        response = requests.get("http://localhost:5001/api/pending_transactions")
        if response.status_code == 200:
            pending_tx = response.json()
            if isinstance(pending_tx, list) and len(pending_tx) > 0:
                print(f"   ✅ Найдено {len(pending_tx)} pending транзакций")
                for tx in pending_tx[:2]:  # Покажем первые 2
                    print(
                        f"      • {tx.get('sender', 'unknown')} → {tx.get('receiver', 'unknown')}: {tx.get('amount', 0)}")
            else:
                print("   ℹ️  Нет pending транзакций")
        else:
            print(f"   ❌ Ошибка получения транзакций: {response.text}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")

    print("=" * 60)
    print("🎉 ТЕСТ ЗАВЕРШЕН! Проверь ручные тесты в браузере.")


if __name__ == "__main__":
    test_complete_flow()