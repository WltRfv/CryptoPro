# api_server.py
from flask import Flask, jsonify
import threading
import time

app = Flask(__name__)


# Имитируем API блокчейна
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'alive', 'port': 5001})


@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    return jsonify({
        'cryptopro_team': {
            'balance': 2500,
            'public_key': 'test_key',
            'is_authority_node': True
        }
    })


@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify({
        'chain': [{'index': 0, 'transactions': []}],
        'pending_transactions': [],
        'blockchain_height': 1
    })


@app.route('/api/transaction', methods=['POST'])
def create_transaction():
    return jsonify({
        'status': 'transaction_created',
        'transaction': {'id': 'test_tx_001'}
    })


def run_blockchain_console():
    """Запускает консольный интерфейс в отдельном потоке"""
    print("🔧 Консольный интерфейс блокчейна доступен")
    # Здесь можно добавить логику для взаимодействия с консолью


if __name__ == '__main__':
    print("🚀 БЛОКЧЕЙН API СЕРВЕР")
    print("📍 API: http://localhost:5001/api")
    print("🔧 Консоль: запущена в фоне")

    # Запускаем консоль в отдельном потоке
    console_thread = threading.Thread(target=run_blockchain_console, daemon=True)
    console_thread.start()

    # Запускаем API сервер
    app.run(host='0.0.0.0', port=5001, debug=False)


'''
pending_transactions = []


@app.route('/api/pending_transactions', methods=['GET'])
def get_pending_transactions():
    """Получить неподтвержденные транзакции"""
    return jsonify(pending_transactions)


@app.route('/api/transactions/<wallet_id>', methods=['GET'])
def get_wallet_transactions(wallet_id):
    """Получить транзакции кошелька"""
    # Фильтруем транзакции по кошельку
    wallet_tx = [tx for tx in pending_transactions
                 if tx.get('sender') == wallet_id or tx.get('receiver') == wallet_id]
    return jsonify(wallet_tx)


@app.route('/api/transaction', methods=['POST'])
def create_transaction():
    """Создать новую транзакцию"""
    data = request.get_json()

    # Создаем транзакцию
    transaction = {
        'transaction_id': f"tx_{len(pending_transactions) + 1}",
        'sender': data.get('sender', 'unknown'),
        'receiver': data.get('receiver'),
        'amount': data.get('amount', 0),
        'type': data.get('type', 'transfer'),
        'timestamp': str(datetime.datetime.now()),
        'signature': 'test_signature'
    }

    # Добавляем в pending
    pending_transactions.append(transaction)

    return jsonify({
        'status': 'transaction_created',
        'transaction': transaction,
        'should_mine': len(pending_transactions) >= 3
    })


@app.route('/api/create_block', methods=['POST'])
def create_block():
    """Создать новый блок из pending транзакций"""
    global pending_transactions

    if len(pending_transactions) == 0:
        return jsonify({
            'status': 'no_transactions',
            'message': 'Нет транзакций для создания блока'
        })

    # Создаем новый блок
    new_block = {
        'index': len(blockchain.chain),
        'timestamp': str(datetime.datetime.now()),
        'transactions': pending_transactions.copy(),  # Копируем текущие транзакции
        'previous_hash': blockchain.chain[-1]['hash'] if blockchain.chain else '0',
        'miner': 'api_server'
    }
    new_block['hash'] = blockchain.hash_block(new_block)

    # Добавляем блок в цепочку
    blockchain.chain.append(new_block)

    # Очищаем pending транзакции
    processed_count = len(pending_transactions)
    pending_transactions = []

    return jsonify({
        'status': 'block_created',
        'block': new_block,
        'processed_transactions': processed_count
    })

'''