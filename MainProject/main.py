import os
import json
import uuid
import hashlib
import socket
import threading
import time
from datetime import datetime, timedelta
import base64
import hmac
import random
import secrets

# Сначала стандартные библиотеки, потом внешние зависимости
import requests
from flask import Flask, jsonify, request

# Наша замена netifaces в самом конце
import netifaces_fix as netifaces

P = 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
N = 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFA51868783BF2F966B7FCC0148F709A5D03BB5C9B8899C47AEBB6FB71E91386409
A = 0x01FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC
B = 0x0051953EB9618E1C9A1F929A21A0B68540EEA2DA725B99B315F3B8B489918EF109E156193951EC7E937B1652C0BD3BB1BF073573DF883D2C34F1EF451FD46B503
Gx = 0x00C6858E06B70404E9CD9E3ECB662395B4429C648139053FB521F828AF606B4D3DBAA14B5E77EFE75928FE1DC127A2FFA8DE3348B3C1856A429BF97E7E31C2E5BD66
Gy = 0x011839296A789A3BC0045C8A5FB42C7D1BD998F54449579B446817AFBD17273E662C97EE72995EF42640C550B9013FAD0761353C7086A272C24088BE94769FD16650
G = (Gx, Gy)


def _ext_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x1, y1 = _ext_gcd(b % a, a)
    return g, y1 - (b // a) * x1, x1


def _mod_inv(a, m):
    a %= m
    g, x, _ = _ext_gcd(a, m)
    if g != 1:
        raise Exception('no inverse')
    return x % m


def _point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if y1 == y2:
            return _point_double(p1)
        return None
    s = ((y2 - y1) * _mod_inv(x2 - x1, P)) % P
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_double(p1):
    if p1 is None:
        return None
    x1, y1 = p1
    if y1 == 0:
        return None
    s = ((3 * x1 * x1 + A) * _mod_inv(2 * y1, P)) % P
    x3 = (s * s - 2 * x1) % P
    y3 = (s * (x1 - x3) - y1) % P
    return (x3, y3)


def _scalar_mult(k, point):
    if k == 0:
        return None
    result = None
    add = point
    while k:
        if k & 1:
            result = _point_add(result, add)
        add = _point_double(add)
        k >>= 1
    return result


def generate_keypair():
    private_key = secrets.randbelow(N - 1) + 1
    public_key = _scalar_mult(private_key, G)
    return private_key, public_key


def _hash_message(message):
    if isinstance(message, str):
        message = message.encode('utf-8')
    return hashlib.sha512(message).digest()


def sign(private_key, message):
    z = int.from_bytes(_hash_message(message), 'big')
    while True:
        k = secrets.randbelow(N - 1) + 1
        x1, _ = _scalar_mult(k, G)
        r = x1 % N
        if r == 0:
            continue
        s = (_mod_inv(k, N) * (z + r * private_key)) % N
        if s == 0:
            continue
        return (r, s)


def verify_signature(public_key, message, signature):
    r, s = signature
    if r < 1 or r > N - 1 or s < 1 or s > N - 1:
        return False

    z = int.from_bytes(_hash_message(message), 'big')
    w = _mod_inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N

    point = _point_add(_scalar_mult(u1, G), _scalar_mult(u2, public_key))
    if point is None:
        return False

    return point[0] % N == r


def _int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    length = (value.bit_length() + 7) // 8
    result = value.to_bytes(length, byteorder="big")
    if result[0] & 0x80:
        result = b"\x00" + result
    return result


def _der_len(data_len: int) -> bytes:
    if data_len < 128:
        return bytes([data_len])
    out = []
    while data_len > 0:
        out.insert(0, data_len & 0xFF)
        data_len >>= 8
    return bytes([0x80 | len(out)] + out)


def _der_t(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _der_seq(content: bytes) -> bytes:
    return _der_t(0x30, content)


def _der_int(value: int) -> bytes:
    return _der_t(0x02, _int_to_bytes(value))


def signature_to_der(r: int, s: int) -> str:
    der_sig = _der_seq(_der_int(r) + _der_int(s))
    return base64.b64encode(der_sig).decode()


def signature_from_der(der_sig: str):
    try:
        sig_bytes = base64.b64decode(der_sig)
        if sig_bytes[0] != 0x30:
            return None, None

        pos = 2

        if sig_bytes[pos] != 0x02:
            return None, None
        r_len = sig_bytes[pos + 1]
        r_bytes = sig_bytes[pos + 2:pos + 2 + r_len]
        pos += 2 + r_len

        if sig_bytes[pos] != 0x02:
            return None, None
        s_len = sig_bytes[pos + 1]
        s_bytes = sig_bytes[pos + 2:pos + 2 + s_len]

        r = int.from_bytes(r_bytes, 'big')
        s = int.from_bytes(s_bytes, 'big')
        return r, s
    except:
        return None, None


def public_key_to_string(public_key):
    x, y = public_key
    return f"{x:x}:{y:x}"


def public_key_from_string(key_str):
    try:
        x_hex, y_hex = key_str.split(':')
        return (int(x_hex, 16), int(y_hex, 16))
    except:
        return None


def private_key_to_string(private_key):
    return f"{private_key:x}"


def private_key_from_string(key_str):
    try:
        return int(key_str, 16)
    except:
        return None


class Transaction:
    def __init__(self, sender, receiver, amount, transaction_type="transfer", signature=None, nonce=None,
                 metadata=None):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.timestamp = datetime.now().isoformat()
        self.transaction_type = transaction_type
        self.signature = signature
        self.nonce = nonce
        self.metadata = metadata or {}
        self.transaction_id = self.generate_id()
        self.locked = False

    def generate_id(self):
        transaction_data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "type": self.transaction_type,
            "metadata": self.metadata
        }
        transaction_string = json.dumps(transaction_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(transaction_string.encode()).hexdigest()[:16]

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'type': self.transaction_type,
            'signature': self.signature,
            'nonce': self.nonce,
            'metadata': self.metadata,
            'locked': self.locked
        }

    def get_data_to_sign(self):
        data_to_sign = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "type": self.transaction_type
        }

        if self.transaction_type in ["grant_authority", "attendance_mark"] and self.metadata:
            data_to_sign["metadata"] = self.metadata

        return json.dumps(data_to_sign, sort_keys=True, separators=(',', ':')).encode()

    def sign_transaction(self, private_key):
        if self.transaction_type == "transfer" and self.nonce is None:
            raise ValueError("Nonce must be set for transfer transactions")

        transaction_data = self.get_data_to_sign()
        r, s = sign(private_key, transaction_data)
        self.signature = signature_to_der(r, s)

    def verify_signature(self, public_key):
        if self.signature is None:
            return False

        try:
            transaction_data = self.get_data_to_sign()
            r, s = signature_from_der(self.signature)
            if r is None or s is None:
                return False
            return verify_signature(public_key, transaction_data, (r, s))
        except:
            return False

    @staticmethod
    def from_dict(data):
        transaction = Transaction(
            data['sender'],
            data['receiver'],
            data['amount'],
            data['type'],
            data.get('signature'),
            data.get('nonce'),
            data.get('metadata', {})
        )
        transaction.transaction_id = data['transaction_id']
        transaction.timestamp = data['timestamp']
        transaction.locked = data.get('locked', False)
        return transaction


class Block:
    def __init__(self, index, previous_hash, transactions, miner_wallet_id, signature=None, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp or datetime.now().isoformat()
        self.transactions = transactions
        self.miner_wallet_id = miner_wallet_id
        self.signature = signature
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_data = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "miner": self.miner_wallet_id
        }
        block_string = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(block_string.encode()).hexdigest()

    def get_data_to_sign(self):
        block_data = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "miner": self.miner_wallet_id
        }
        return json.dumps(block_data, sort_keys=True, separators=(',', ':')).encode()

    def sign_block(self, private_key):
        block_data = self.get_data_to_sign()
        r, s = sign(private_key, block_data)
        self.signature = signature_to_der(r, s)

    def verify_signature(self, public_key):
        if self.signature is None:
            return False

        try:
            block_data = self.get_data_to_sign()
            r, s = signature_from_der(self.signature)
            if r is None or s is None:
                return False
            return verify_signature(public_key, block_data, (r, s))
        except:
            return False

    def to_dict(self):
        return {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'miner': self.miner_wallet_id,
            'signature': self.signature,
            'hash': self.hash
        }

    @staticmethod
    def from_dict(data):
        transactions = [Transaction.from_dict(tx) for tx in data['transactions']]
        block = Block(
            data['index'],
            data['previous_hash'],
            transactions,
            data['miner'],
            data.get('signature'),
            data.get('timestamp')
        )
        block.hash = data['hash']
        return block


class AttendanceSystem:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.attendance_window_hours = 2
        self.reward_amount = 100

    def create_attendance_transaction(self, student_wallet, week_id):
        attendance_tx = Transaction(
            sender=student_wallet,
            receiver="attendance_system",
            amount=0,
            transaction_type="attendance_mark",
            metadata={
                "week_id": week_id,
                "timestamp": datetime.now().isoformat(),
                "type": "presence"
            }
        )
        return attendance_tx

    def validate_attendance_transaction(self, transaction, current_week_id):
        if transaction.transaction_type != "attendance_mark":
            return False

        metadata = transaction.metadata
        if metadata.get("week_id") != current_week_id:
            return False

        if self.has_student_attended(transaction.sender, current_week_id):
            return False

        return True

    def has_student_attended(self, student_wallet, week_id):
        for block in self.blockchain.chain:
            for tx in block.transactions:
                if (tx.transaction_type == "attendance_mark" and
                        tx.sender == student_wallet and
                        tx.metadata.get("week_id") == week_id):
                    return True

        for tx in self.blockchain.pending_transactions:
            if (tx.transaction_type == "attendance_mark" and
                    tx.sender == student_wallet and
                    tx.metadata.get("week_id") == week_id):
                return True
        return False

    def get_weekly_attendance(self, week_id):
        attendees = set()
        for block in self.blockchain.chain:
            for tx in block.transactions:
                if (tx.transaction_type == "attendance_mark" and
                        tx.metadata.get("week_id") == week_id):
                    attendees.add(tx.sender)

        for tx in self.blockchain.pending_transactions:
            if (tx.transaction_type == "attendance_mark" and
                    tx.metadata.get("week_id") == week_id):
                attendees.add(tx.sender)

        return list(attendees)


class ActivityTracker:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def get_last_activity_date(self, student_wallet):
        last_activity = None

        for block in self.blockchain.chain:
            for tx in block.transactions:
                if tx.transaction_type == "attendance_mark":
                    continue

                if tx.sender == student_wallet or tx.receiver == student_wallet:
                    try:
                        tx_time = datetime.fromisoformat(tx.timestamp.replace('Z', '+00:00'))
                        if last_activity is None or tx_time > last_activity:
                            last_activity = tx_time
                    except:
                        continue

        for tx in self.blockchain.pending_transactions:
            if tx.transaction_type == "attendance_mark":
                continue

            if tx.sender == student_wallet or tx.receiver == student_wallet:
                try:
                    tx_time = datetime.fromisoformat(tx.timestamp.replace('Z', '+00:00'))
                    if last_activity is None or tx_time > last_activity:
                        last_activity = tx_time
                except:
                    continue

        return last_activity

    def check_inactivity_penalty(self, student_wallet, check_date):
        last_activity = self.get_last_activity_date(student_wallet)

        if last_activity is None:
            return True

        time_diff = check_date - last_activity
        return time_diff.days >= 30


class RewardSystem:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.attendance_system = AttendanceSystem(blockchain)
        self.activity_tracker = ActivityTracker(blockchain)
        self.reward_amount = 100
        self.penalty_amount = 100

    def process_weekly_rewards(self, week_id, week_start, week_end):
        reward_transactions = []

        all_students = self.get_all_students()
        attendees = self.attendance_system.get_weekly_attendance(week_id)

        for student in all_students:
            if student in attendees:
                reward_tx = Transaction(
                    sender="bank",
                    receiver=student,
                    amount=self.reward_amount,
                    transaction_type="attendance_reward",
                    metadata={
                        "week_id": week_id,
                        "type": "attendance_bonus"
                    }
                )
                reward_transactions.append(reward_tx)
            else:
                penalty_tx = Transaction(
                    sender=student,
                    receiver="bank",
                    amount=self.penalty_amount,
                    transaction_type="absence_penalty",
                    metadata={
                        "week_id": week_id,
                        "type": "absence_fine"
                    }
                )
                reward_transactions.append(penalty_tx)

            if self.activity_tracker.check_inactivity_penalty(student, week_end):
                inactivity_tx = Transaction(
                    sender=student,
                    receiver="bank",
                    amount=self.penalty_amount,
                    transaction_type="inactivity_penalty",
                    metadata={
                        "week_id": week_id,
                        "type": "inactivity_fine"
                    }
                )
                reward_transactions.append(inactivity_tx)

                user_assets = self.blockchain.get_user_assets(student)
                if user_assets:
                    asset_id_to_remove = list(user_assets.keys())[0]
                    asset_removal_tx = Transaction(
                        sender="system",
                        receiver=student,
                        amount=0,
                        transaction_type="asset_removal",
                        metadata={
                            "week_id": week_id,
                            "asset_id": asset_id_to_remove,
                            "reason": "inactivity"
                        }
                    )
                    reward_transactions.append(asset_removal_tx)

        return reward_transactions

    def get_all_students(self):
        students = set()
        system_wallets = {"system", "bank", "genesis", "attendance_system"}

        for block in self.blockchain.chain:
            for tx in block.transactions:
                if tx.sender not in system_wallets and tx.sender:
                    students.add(tx.sender)
                if tx.receiver not in system_wallets and tx.receiver:
                    students.add(tx.receiver)

        return list(students)


class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.block_size = 20
        self.mining_in_progress = False
        self.wallet_nonces = {}
        self.locked_transactions = set()
        self.last_sync_time = 0
        self.mining_lock = threading.Lock()
        self.authority_nodes = set()
        self.authority_public_keys = {}
        self.genesis_owner = None

        self.assets = {}
        self.asset_transfers = {}
        self.votes_required_percentage = 51

        self.attendance_system = AttendanceSystem(self)
        self.activity_tracker = ActivityTracker(self)
        self.reward_system = RewardSystem(self)

        self.initialize_asset_system()

    def initialize_asset_system(self):
        self.assets = {}
        self.asset_transfers = {}

    def is_authority_node(self, wallet_id):
        return wallet_id in self.authority_nodes

    def add_authority_public_key(self, wallet_id, public_key_str):
        public_key = public_key_from_string(public_key_str)
        if public_key:
            self.authority_public_keys[wallet_id] = public_key

    def get_authority_public_key(self, wallet_id):
        return self.authority_public_keys.get(wallet_id)

    def create_genesis_block(self, authority_wallet_id, public_key_str=None):
        if len(self.chain) > 0:
            return None

        genesis_transaction = Transaction("system", "genesis", 0, "genesis")
        bank_transaction = Transaction("system", "bank", 60000, "create_bank")
        authority_transaction = Transaction("system", authority_wallet_id, 2500, "create")

        genesis_block = Block(0, "0", [
            genesis_transaction,
            bank_transaction,
            authority_transaction
        ], authority_wallet_id)

        genesis_block.timestamp = "2024-01-01T00:00:00"
        genesis_block.hash = genesis_block.calculate_hash()

        self.authority_nodes.add(authority_wallet_id)
        self.genesis_owner = authority_wallet_id

        if public_key_str:
            self.authority_public_keys[authority_wallet_id] = public_key_from_string(public_key_str)

        self.create_initial_assets(authority_wallet_id)

        return genesis_block

    def get_latest_block(self):
        if len(self.chain) == 0:
            return None
        return self.chain[-1]

    def validate_transaction(self, transaction):
        if transaction.transaction_id in self.locked_transactions:
            return False

        if transaction.transaction_type == "create":
            return (transaction.sender == "system" and
                    transaction.receiver not in ["system", "genesis", "bank"])

        elif transaction.transaction_type == "create_bank":
            return (transaction.sender == "system" and
                    transaction.receiver == "bank" and
                    transaction.amount == 60000)

        elif transaction.transaction_type == "grant_authority":
            return self.validate_grant_authority_transaction(transaction)

        elif transaction.transaction_type == "transfer":
            if transaction.metadata and transaction.metadata.get('is_asset_transfer'):
                return True

            return (self.is_wallet_created(transaction.receiver) and
                    self.get_available_balance(transaction.sender) >= transaction.amount)

        elif transaction.transaction_type == "asset_bonus":
            return (transaction.sender == "bank" and
                    self.is_wallet_created(transaction.receiver) and
                    self.get_balance("bank") >= transaction.amount)

        elif transaction.transaction_type == "attendance_mark":
            current_week_id = datetime.now().strftime("%Y-W%U")
            return self.attendance_system.validate_attendance_transaction(transaction, current_week_id)

        elif transaction.transaction_type == "asset_removal":
            return (transaction.sender == "system" and
                    self.is_wallet_created(transaction.receiver) and
                    'asset_id' in transaction.metadata and
                    transaction.metadata['asset_id'] in self.assets and
                    self.assets[transaction.metadata['asset_id']]['owner'] == transaction.receiver)

        elif transaction.transaction_type in ["attendance_reward", "absence_penalty", "inactivity_penalty"]:
            return True

        return False

    def validate_grant_authority_transaction(self, transaction):
        if transaction.sender != self.genesis_owner:
            return False

        if not self.is_wallet_created(transaction.receiver):
            return False

        if transaction.receiver in self.authority_nodes:
            return False

        public_key = self.get_authority_public_key(transaction.sender)
        if not public_key or not transaction.verify_signature(public_key):
            return False

        return True

    def process_grant_authority(self, transaction, public_key_str=None):
        if self.validate_grant_authority_transaction(transaction):
            self.authority_nodes.add(transaction.receiver)

            if public_key_str:
                public_key = public_key_from_string(public_key_str)
                if public_key:
                    self.authority_public_keys[transaction.receiver] = public_key

            return True
        return False

    def can_grant_authority(self, wallet_id):
        return wallet_id == self.genesis_owner

    def validate_block(self, block):
        calculated_hash = block.calculate_hash()
        if block.hash != calculated_hash:
            return False

        if block.index == 0:
            pass
        elif not self.is_authority_node(block.miner_wallet_id):
            return False

        if block.index > 0:
            public_key = self.get_authority_public_key(block.miner_wallet_id)
            if not public_key:
                return False

            try:
                if not block.verify_signature(public_key):
                    return False
            except Exception as e:
                return False

        for transaction in block.transactions:
            if not self.validate_transaction(transaction):
                return False

        return True

    def create_block(self, miner_wallet_id, private_key):
        with self.mining_lock:
            if self.mining_in_progress:
                return None

            if miner_wallet_id not in self.authority_nodes:
                return None

            self.mining_in_progress = True

        try:
            if len(self.pending_transactions) < self.block_size:
                return None

            transactions_to_mine = self.lock_transactions_for_mining()

            latest_block = self.get_latest_block()
            previous_hash = latest_block.hash if latest_block else "0"

            block = Block(
                len(self.chain),
                previous_hash,
                transactions_to_mine,
                miner_wallet_id
            )

            block.sign_block(private_key)

            self.chain.append(block)

            for tx in transactions_to_mine:
                if tx.transaction_type == "grant_authority":
                    self.process_grant_authority(tx)
                elif tx.transaction_type == "asset_removal":
                    asset_id = tx.metadata.get('asset_id')
                    if asset_id in self.assets:
                        del self.assets[asset_id]
                self.remove_transaction_from_pending(tx)

            return block

        except Exception as e:
            return None
        finally:
            self.mining_in_progress = False
            self.unlock_all_transactions()

    def generate_unique_asset_id(self):
        while True:
            asset_id = hashlib.sha256(
                f"{uuid.uuid4()}{datetime.now().timestamp()}{random.random()}".encode()).hexdigest()[:16]
            if asset_id not in self.assets:
                return asset_id

    def create_initial_assets(self, wallet_id):
        if wallet_id in ["system", "genesis", "bank"]:
            return

        user_assets = self.get_user_assets(wallet_id)
        if len(user_assets) > 0:
            return

        created_assets = []
        for i in range(5):
            asset_id = self.generate_unique_asset_id()
            self.assets[asset_id] = {
                'id': asset_id,
                'owner': wallet_id,
                'created_at': datetime.now().isoformat(),
                'transfer_history': []
            }
            created_assets.append(asset_id)

        return created_assets

    def create_assets_for_new_user(self, wallet_id):
        try:
            if (wallet_id not in ["system", "genesis", "bank"] and
                    wallet_id not in self.get_all_wallets_with_assets()):
                assets_created = self.create_initial_assets(wallet_id)
                return assets_created
        except Exception as e:
            pass
        return None

    def get_all_wallets_with_assets(self):
        wallets_with_assets = set()
        for asset_id, asset in self.assets.items():
            wallets_with_assets.add(asset['owner'])
        return wallets_with_assets

    def initiate_asset_transfer(self, asset_id, from_wallet, to_wallet, price=100):
        if asset_id not in self.assets:
            raise ValueError(f"Актив с ID {asset_id} не существует")

        if self.assets[asset_id]['owner'] != from_wallet:
            raise ValueError("Только владелец может инициировать передачу")

        if not self.is_wallet_created(to_wallet):
            raise ValueError(f"Получатель {to_wallet} не существует")

        if from_wallet == to_wallet:
            raise ValueError("Нельзя передавать актив самому себе")

        transfer_id = hashlib.sha256(
            f"{asset_id}_{from_wallet}_{to_wallet}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        self.asset_transfers[transfer_id] = {
            'asset_id': asset_id,
            'from_wallet': from_wallet,
            'to_wallet': to_wallet,
            'price': price,
            'votes': {},
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }

        return transfer_id

    def vote_on_asset_transfer(self, transfer_id, voter_wallet_id, approve):
        if transfer_id not in self.asset_transfers:
            raise ValueError("Передача не найдена")

        transfer = self.asset_transfers[transfer_id]

        if voter_wallet_id == transfer['to_wallet']:
            raise ValueError("Получатель актива не может участвовать в голосовании")

        if not self.is_wallet_created(voter_wallet_id):
            raise ValueError("Кошелек голосующего не существует")

        transfer['votes'][voter_wallet_id] = {
            'approve': approve,
            'timestamp': datetime.now().isoformat()
        }

        self._check_transfer_consensus(transfer_id)

    def _check_transfer_consensus(self, transfer_id):
        transfer = self.asset_transfers[transfer_id]

        all_wallets = set(self.get_all_wallets_from_blockchain().keys())
        voters_pool = all_wallets - {transfer['from_wallet'], transfer['to_wallet']}

        if not voters_pool:
            self._execute_asset_transfer(transfer_id)
            return

        approve_count = sum(1 for vote in transfer['votes'].values() if vote['approve'])
        total_votes = len(transfer['votes'])
        total_possible_voters = len(voters_pool)

        if total_votes >= total_possible_voters or (total_votes > 0 and total_possible_voters == 0):
            approval_rate = (approve_count / max(total_votes, 1)) * 100

            if approval_rate >= self.votes_required_percentage:
                self._execute_asset_transfer(transfer_id)
            else:
                self._reject_asset_transfer(transfer_id)

    def _execute_asset_transfer(self, transfer_id):
        transfer = self.asset_transfers[transfer_id]
        asset_id = transfer['asset_id']

        old_owner = self.assets[asset_id]['owner']
        self.assets[asset_id]['owner'] = transfer['to_wallet']
        self.assets[asset_id]['transfer_history'].append({
            'from': old_owner,
            'to': transfer['to_wallet'],
            'timestamp': datetime.now().isoformat(),
            'transfer_id': transfer_id,
            'price': transfer['price']
        })

        payment_tx = Transaction(
            transfer['to_wallet'],
            transfer['from_wallet'],
            transfer['price'],
            "transfer",
            nonce=self.get_expected_nonce(transfer['to_wallet']) + 1,
            metadata={'is_asset_transfer': True, 'asset_id': asset_id, 'transfer_id': transfer_id}
        )

        bonus_tx = Transaction(
            "bank",
            transfer['to_wallet'],
            150,
            "asset_bonus",
            metadata={'is_asset_bonus': True, 'asset_id': asset_id, 'transfer_id': transfer_id}
        )

        self.add_transaction(payment_tx)
        self.add_transaction(bonus_tx)

        transfer['status'] = 'approved'
        transfer['executed_at'] = datetime.now().isoformat()

    def _reject_asset_transfer(self, transfer_id):
        transfer = self.asset_transfers[transfer_id]

        penalty_tx = Transaction(
            transfer['to_wallet'],
            transfer['from_wallet'],
            transfer['price'],
            "transfer",
            nonce=self.get_expected_nonce(transfer['to_wallet']) + 1,
            metadata={'is_penalty': True, 'transfer_id': transfer_id, 'asset_id': transfer['asset_id']}
        )

        self.add_transaction(penalty_tx)
        transfer['status'] = 'rejected'
        transfer['executed_at'] = datetime.now().isoformat()

    def get_user_assets(self, wallet_id):
        return {asset_id: asset for asset_id, asset in self.assets.items()
                if asset['owner'] == wallet_id}

    def get_user_assets_count(self, wallet_id):
        return len(self.get_user_assets(wallet_id))

    def sync_asset_transfers(self, asset_transfers_data):
        added_count = 0

        for transfer_id, transfer_data in asset_transfers_data.items():
            if transfer_id not in self.asset_transfers:
                self.asset_transfers[transfer_id] = transfer_data
                added_count += 1

                if transfer_data.get('status') in ['approved', 'rejected']:
                    self._apply_completed_asset_transfer(transfer_id, transfer_data)
            else:
                existing_transfer = self.asset_transfers[transfer_id]
                for voter_id, vote_data in transfer_data.get('votes', {}).items():
                    if voter_id not in existing_transfer['votes']:
                        existing_transfer['votes'][voter_id] = vote_data
                        added_count += 1

                if transfer_data.get('status') != existing_transfer.get('status'):
                    existing_transfer['status'] = transfer_data.get('status')
                    existing_transfer['executed_at'] = transfer_data.get('executed_at')

                    if transfer_data.get('status') in ['approved', 'rejected']:
                        self._apply_completed_asset_transfer(transfer_id, existing_transfer)

        return added_count

    def _apply_completed_asset_transfer(self, transfer_id, transfer_data):
        if transfer_data['status'] == 'approved':
            asset_id = transfer_data['asset_id']
            if (asset_id in self.assets and
                    self.assets[asset_id]['owner'] != transfer_data['to_wallet']):
                self.assets[asset_id]['owner'] = transfer_data['to_wallet']
                self.assets[asset_id]['transfer_history'].append({
                    'from': transfer_data['from_wallet'],
                    'to': transfer_data['to_wallet'],
                    'timestamp': transfer_data.get('executed_at', datetime.now().isoformat()),
                    'transfer_id': transfer_id,
                    'price': transfer_data.get('price', 100)
                })

    def add_attendance_transaction(self, transaction, current_week_id, private_key=None):
        if not self.attendance_system.validate_attendance_transaction(transaction, current_week_id):
            raise ValueError("Невалидная транзакция посещения")

        if private_key:
            transaction.sign_transaction(private_key)

        return self.add_transaction(transaction)

    def process_weekly_settlement(self, week_id, week_start, week_end):
        reward_transactions = self.reward_system.process_weekly_rewards(week_id, week_start, week_end)

        for tx in reward_transactions:
            self.add_transaction(tx)

        return len(reward_transactions)

    def get_expected_nonce(self, wallet_id):
        if wallet_id in self.wallet_nonces:
            return self.wallet_nonces[wallet_id]

        nonce = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == wallet_id and tx.nonce is not None:
                    nonce = max(nonce, tx.nonce)

        for tx in self.pending_transactions:
            if tx.sender == wallet_id and tx.nonce is not None:
                nonce = max(nonce, tx.nonce)

        self.wallet_nonces[wallet_id] = nonce
        return nonce

    def get_available_balance(self, wallet_id):
        balance = self.get_balance(wallet_id)
        for tx in self.pending_transactions:
            if tx.sender == wallet_id and tx.transaction_type == "transfer":
                if not tx.metadata or not tx.metadata.get('is_asset_transfer'):
                    balance -= tx.amount
        return balance

    def lock_transactions_for_mining(self, count=None):
        if count is None:
            count = self.block_size

        self.unlock_all_transactions()
        transactions_to_lock = self.pending_transactions[:min(count, len(self.pending_transactions))]
        for tx in transactions_to_lock:
            self.locked_transactions.add(tx.transaction_id)
            tx.locked = True
        return transactions_to_lock

    def unlock_all_transactions(self):
        for tx in self.pending_transactions:
            tx.locked = False
        self.locked_transactions.clear()

    def add_transaction(self, transaction, private_key=None):
        if len(self.pending_transactions) >= self.block_size:
            raise ValueError(f"Достигнут лимит pending транзакций ({self.block_size})")

        if not self.validate_transaction(transaction):
            raise ValueError("Невалидная транзакция")

        for tx in self.pending_transactions:
            if tx.transaction_id == transaction.transaction_id:
                return False

        if transaction.transaction_type == "transfer":
            for tx in self.pending_transactions:
                if tx.sender == transaction.sender and tx.nonce == transaction.nonce:
                    return False

        if private_key and transaction.transaction_type in ["transfer", "attendance_mark", "grant_authority"]:
            transaction.sign_transaction(private_key)

        if transaction.transaction_type == "create":
            self.create_assets_for_new_user(transaction.receiver)

        self.pending_transactions.append(transaction)

        return len(self.pending_transactions) >= self.block_size

    def is_wallet_created(self, wallet_id):
        if wallet_id in ["system", "genesis"]:
            return False

        for block in self.chain:
            for transaction in block.transactions:
                if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                    return True

        for transaction in self.pending_transactions:
            if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                return True

        return False

    def add_authority_node(self, wallet_id, public_key_str=None):
        self.authority_nodes.add(wallet_id)
        if public_key_str:
            public_key = public_key_from_string(public_key_str)
            if public_key:
                self.authority_public_keys[wallet_id] = public_key

    def validate_chain(self):
        if len(self.chain) == 0:
            return True

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

            if i > 0 and not self.is_authority_node(current_block.miner_wallet_id):
                return False

        return True

    def add_block(self, block):
        if not self.validate_block(block):
            return False

        latest_block = self.get_latest_block()
        if latest_block and block.previous_hash != latest_block.hash:
            return False

        if block.index != len(self.chain):
            return False

        self.chain.append(block)

        for tx in block.transactions:
            if tx.transaction_type == "create":
                self.create_assets_for_new_user(tx.receiver)
            elif tx.transaction_type == "grant_authority":
                self.process_grant_authority(tx)
            elif tx.transaction_type == "asset_removal":
                asset_id = tx.metadata.get('asset_id')
                if asset_id in self.assets:
                    del self.assets[asset_id]

            self.remove_transaction_from_pending(tx)

        return True

    def remove_transaction_from_pending(self, transaction):
        new_pending = []
        removed_count = 0

        for tx in self.pending_transactions:
            if tx.transaction_id != transaction.transaction_id:
                new_pending.append(tx)
            else:
                removed_count += 1

        self.pending_transactions = new_pending
        return removed_count

    def get_balance(self, wallet_id, include_pending=True):
        balance = 0

        for block in self.chain:
            for transaction in block.transactions:
                if transaction.receiver == "genesis" or transaction.sender == "genesis":
                    continue

                if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "create_bank" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "transfer":
                    if transaction.sender == wallet_id:
                        balance -= transaction.amount
                    if transaction.receiver == wallet_id:
                        balance += transaction.amount
                elif transaction.transaction_type == "asset_bonus" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "attendance_reward" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type in ["absence_penalty",
                                                      "inactivity_penalty"] and transaction.sender == wallet_id:
                    balance -= transaction.amount

        if include_pending:
            for transaction in self.pending_transactions:
                if transaction.receiver == "genesis" or transaction.sender == "genesis":
                    continue

                if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "create_bank" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "transfer":
                    if transaction.sender == wallet_id:
                        balance -= transaction.amount
                    if transaction.receiver == wallet_id:
                        balance += transaction.amount
                elif transaction.transaction_type == "asset_bonus" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type == "attendance_reward" and transaction.receiver == wallet_id:
                    balance += transaction.amount
                elif transaction.transaction_type in ["absence_penalty",
                                                      "inactivity_penalty"] and transaction.sender == wallet_id:
                    balance -= transaction.amount

        return balance

    def get_all_wallets_from_blockchain(self):
        wallets = {}

        for block in self.chain:
            for transaction in block.transactions:
                if transaction.receiver == "genesis" or transaction.sender == "genesis":
                    continue

                if transaction.sender != "system" and transaction.sender not in wallets:
                    wallets[transaction.sender] = {
                        'balance': self.get_balance(transaction.sender),
                        'public_key': None,
                        'last_updated': block.timestamp,
                        'assets_count': self.get_user_assets_count(transaction.sender)
                    }

                if transaction.receiver != "system" and transaction.receiver not in wallets:
                    wallets[transaction.receiver] = {
                        'balance': self.get_balance(transaction.receiver),
                        'public_key': None,
                        'last_updated': block.timestamp,
                        'assets_count': self.get_user_assets_count(transaction.receiver)
                    }

        for transaction in self.pending_transactions:
            if transaction.receiver == "genesis" or transaction.sender == "genesis":
                continue

            if transaction.sender != "system" and transaction.sender not in wallets:
                wallets[transaction.sender] = {
                    'balance': self.get_balance(transaction.sender),
                    'public_key': None,
                    'last_updated': datetime.now().isoformat(),
                    'assets_count': self.get_user_assets_count(transaction.sender)
                }

            if transaction.receiver != "system" and transaction.receiver not in wallets:
                wallets[transaction.receiver] = {
                    'balance': self.get_balance(transaction.receiver),
                    'public_key': None,
                    'last_updated': datetime.now().isoformat(),
                    'assets_count': self.get_user_assets_count(transaction.receiver)
                }

        return wallets

    def has_user_creation_transaction(self, wallet_id):
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                    return True

        for transaction in self.pending_transactions:
            if transaction.transaction_type == "create" and transaction.receiver == wallet_id:
                return True

        return False

    def get_all_transactions_for_wallet(self, wallet_id):
        transactions = []

        for block in self.chain:
            for transaction in block.transactions:
                if transaction.receiver == "genesis" or transaction.sender == "genesis":
                    continue

                if transaction.sender == wallet_id or transaction.receiver == wallet_id:
                    transactions.append(transaction.to_dict())

        for transaction in self.pending_transactions:
            if transaction.receiver == "genesis" or transaction.sender == "genesis":
                continue

            if transaction.sender == wallet_id or transaction.receiver == wallet_id:
                transactions.append(transaction.to_dict())

        return transactions

    def is_transaction_in_blockchain(self, transaction_id):
        for block in self.chain:
            for tx in block.transactions:
                if tx.transaction_id == transaction_id:
                    return True
        return False

    def add_pending_transactions(self, transactions_data):
        added_count = 0
        should_mine = False

        for tx_data in transactions_data:
            try:
                if len(self.pending_transactions) >= self.block_size:
                    break

                transaction = Transaction.from_dict(tx_data)

                if transaction.locked:
                    continue

                if self.is_transaction_in_blockchain(transaction.transaction_id):
                    continue

                exists_in_pending = any(
                    existing_tx.transaction_id == transaction.transaction_id
                    for existing_tx in self.pending_transactions
                )

                if exists_in_pending:
                    continue

                if transaction.transaction_type == "transfer":
                    nonce_exists = any(
                        existing_tx.sender == transaction.sender and
                        existing_tx.nonce == transaction.nonce
                        for existing_tx in self.pending_transactions
                    )
                    if nonce_exists:
                        continue

                if not self.validate_transaction(transaction):
                    continue

                self.pending_transactions.append(transaction)
                added_count += 1

                if transaction.transaction_type == "create":
                    self.create_assets_for_new_user(transaction.receiver)

            except Exception as e:
                continue

        if len(self.pending_transactions) >= self.block_size:
            should_mine = True

        return added_count, should_mine

    def sync_transaction_pool(self, transactions_data):
        added_count = 0
        for tx_data in transactions_data:
            try:
                if len(self.pending_transactions) >= self.block_size:
                    break

                transaction = Transaction.from_dict(tx_data)

                if transaction.locked:
                    continue

                exists = False
                for existing_tx in self.pending_transactions:
                    if existing_tx.transaction_id == transaction.transaction_id:
                        exists = True
                        break

                if not exists and self.validate_transaction(transaction):
                    self.pending_transactions.append(transaction)
                    added_count += 1

                    if transaction.transaction_type == "create":
                        self.create_assets_for_new_user(transaction.receiver)

            except Exception as e:
                continue

        return added_count

    def find_longest_valid_chain(self, chains):
        longest_chain = None
        max_length = len(self.chain)

        for chain_data in chains:
            try:
                temp_blockchain = Blockchain()
                temp_blockchain.chain = []

                for block_data in chain_data['chain']:
                    block = Block.from_dict(block_data)
                    temp_blockchain.chain.append(block)

                if 'authority_nodes' in chain_data:
                    temp_blockchain.authority_nodes = set(chain_data['authority_nodes'])

                if temp_blockchain.validate_chain() and len(temp_blockchain.chain) > max_length:
                    longest_chain = chain_data
                    max_length = len(temp_blockchain.chain)
            except Exception as e:
                continue

        return longest_chain

    def to_dict(self):
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'block_size': self.block_size,
            'authority_nodes': list(self.authority_nodes),
            'authority_public_keys': {k: public_key_to_string(v) for k, v in self.authority_public_keys.items()},
            'genesis_owner': self.genesis_owner,
            'assets': self.assets,
            'asset_transfers': self.asset_transfers
        }

    def from_dict(self, data):
        self.chain = []
        for block_data in data['chain']:
            block = Block.from_dict(block_data)
            self.chain.append(block)

        self.pending_transactions = []
        for tx_data in data['pending_transactions']:
            tx = Transaction.from_dict(tx_data)
            self.pending_transactions.append(tx)

        self.block_size = data.get('block_size', 20)
        self.authority_nodes = set(data.get('authority_nodes', []))

        authority_public_keys = data.get('authority_public_keys', {})
        self.authority_public_keys = {}
        for wallet_id, key_str in authority_public_keys.items():
            public_key = public_key_from_string(key_str)
            if public_key:
                self.authority_public_keys[wallet_id] = public_key

        self.genesis_owner = data.get('genesis_owner')
        self.assets = data.get('assets', {})
        self.asset_transfers = data.get('asset_transfers', {})


class Wallet:
    def __init__(self, wallet_id=None):
        self.wallet_id = wallet_id or self.generate_wallet_id()
        self.private_key, self.public_key = self.generate_keys()
        self.known_wallets = {}
        self.file_path = f"wallets/{self.wallet_id}.json"
        self.mac_address = self.get_mac_address()
        self.transaction_nonce = 0
        self.file_integrity_hash = None
        self.is_first_node = False
        self.is_authority_node = False

        self.blockchain = Blockchain()
        self.load_transaction_nonce()

    def generate_wallet_id(self):
        mac = self.get_mac_address()
        random_component = str(uuid.uuid4())
        unique_string = f"{mac}_{random_component}_{datetime.now().timestamp()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def generate_keys(self):
        return generate_keypair()

    def get_mac_address(self):
        try:
            for interface in netifaces.interfaces():
                if interface == 'lo':
                    continue
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_LINK in addrs:
                    mac = addrs[netifaces.AF_LINK][0]['addr']
                    if mac and mac != '00:00:00:00:00:00':
                        return mac
            return "unknown_mac"
        except:
            return "unknown_mac"

    def get_next_nonce(self):
        self.transaction_nonce += 1
        self.save_transaction_nonce()
        return self.transaction_nonce

    def load_transaction_nonce(self):
        try:
            if os.path.exists("wallets/nonce_store.json"):
                with open("wallets/nonce_store.json", 'r') as f:
                    nonce_data = json.load(f)
                    if self.wallet_id in nonce_data:
                        self.transaction_nonce = nonce_data[self.wallet_id]
        except:
            self.transaction_nonce = 0

    def save_transaction_nonce(self):
        os.makedirs("wallets", exist_ok=True)
        try:
            if os.path.exists("wallets/nonce_store.json"):
                with open("wallets/nonce_store.json", 'r') as f:
                    nonce_data = json.load(f)
            else:
                nonce_data = {}

            nonce_data[self.wallet_id] = self.transaction_nonce

            with open("wallets/nonce_store.json", 'w') as f:
                json.dump(nonce_data, f, indent=2)
        except:
            pass

    def calculate_file_hash(self, data):
        secret = "blockchain_wallet_integrity_secret"
        data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hmac.new(secret.encode(), data_string.encode(), hashlib.sha256).hexdigest()

    def save_to_file(self):
        os.makedirs("wallets", exist_ok=True)

        data = {
            "wallet_id": self.wallet_id,
            "public_key": public_key_to_string(self.public_key),
            "private_key": private_key_to_string(self.private_key),
            "known_wallets": self.known_wallets,
            "blockchain": self.blockchain.to_dict(),
            "last_updated": datetime.now().isoformat(),
            "mac_address": self.mac_address,
            "transaction_nonce": self.transaction_nonce,
            "is_first_node": self.is_first_node,
            "is_authority_node": self.is_authority_node
        }

        integrity_data = data.copy()
        data['integrity_hash'] = self.calculate_file_hash(integrity_data)

        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving wallet: {e}")
            return False

    def load_from_file(self):
        try:
            if not os.path.exists(self.file_path):
                return False

            with open(self.file_path, 'r') as f:
                data = json.load(f)

            integrity_hash = data.get('integrity_hash')
            if not integrity_hash:
                return False

            check_data = data.copy()
            check_data.pop('integrity_hash', None)

            calculated_hash = self.calculate_file_hash(check_data)

            if integrity_hash != calculated_hash:
                return False

            self.wallet_id = data['wallet_id']
            self.public_key = public_key_from_string(data['public_key'])
            self.private_key = private_key_from_string(data['private_key'])
            self.known_wallets = data.get('known_wallets', {})

            if 'blockchain' in data:
                self.blockchain.from_dict(data['blockchain'])

            self.mac_address = data.get('mac_address', self.get_mac_address())
            self.transaction_nonce = data.get('transaction_nonce', 0)
            self.is_first_node = data.get('is_first_node', False)
            self.is_authority_node = data.get('is_authority_node', False)

            return True

        except FileNotFoundError:
            return False
        except json.JSONDecodeError as e:
            return False
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return False

    def get_balance(self, include_pending=True):
        return self.blockchain.get_balance(self.wallet_id, include_pending)

    def get_available_balance(self):
        return self.blockchain.get_available_balance(self.wallet_id)

    def get_assets_count(self):
        return self.blockchain.get_user_assets_count(self.wallet_id)

    def create_user_transaction(self, new_wallet_id):
        transaction = Transaction(
            "system",
            new_wallet_id,
            2500,
            "create"
        )
        return transaction

    def create_transfer_transaction(self, receiver_wallet_id, amount):
        if receiver_wallet_id == self.wallet_id:
            raise ValueError("Нельзя переводить самому себе")
        if receiver_wallet_id == "bank":
            raise ValueError("Нельзя переводить банку")

        if not self.is_wallet_valid_for_transfer(receiver_wallet_id):
            raise ValueError(f"Получатель {receiver_wallet_id} не существует или не валиден для перевода")

        available_balance = self.get_available_balance()
        if available_balance < amount:
            raise ValueError(f"Недостаточно средств. Доступно: {available_balance}, требуется: {amount}")

        nonce = self.get_next_nonce()

        transaction = Transaction(
            self.wallet_id,
            receiver_wallet_id,
            amount,
            "transfer",
            nonce=nonce
        )

        transaction.sign_transaction(self.private_key)
        return transaction

    def create_attendance_transaction(self, week_id):
        transaction = self.blockchain.attendance_system.create_attendance_transaction(
            self.wallet_id, week_id
        )
        transaction.sign_transaction(self.private_key)
        return transaction

    def create_grant_authority_transaction(self, target_wallet_id):
        transaction = Transaction(
            self.wallet_id,
            target_wallet_id,
            0,
            "grant_authority",
            nonce=self.get_next_nonce()
        )
        transaction.sign_transaction(self.private_key)
        return transaction

    def update_authority_status(self):
        was_authority = self.is_authority_node
        self.is_authority_node = self.wallet_id in self.blockchain.authority_nodes

        if self.is_authority_node and not was_authority:
            return True
        elif not self.is_authority_node and was_authority:
            return True

        return False

    def is_wallet_valid_for_transfer(self, wallet_id):
        if wallet_id in ["system", "genesis"]:
            return False

        if self.blockchain.is_wallet_created(wallet_id):
            return True

        if wallet_id in self.known_wallets:
            wallet_info = self.known_wallets[wallet_id]
            if wallet_info.get('public_key') is not None:
                return True

        return False

    def update_wallet_info(self, wallet_data):
        current_time = datetime.now().isoformat()

        for wallet_id, wallet_info in wallet_data.items():
            if wallet_id in ["system", "genesis"]:
                continue

            if wallet_id not in self.known_wallets:
                self.known_wallets[wallet_id] = wallet_info
            else:
                existing_time = self.known_wallets[wallet_id].get('last_updated', '')
                new_time = wallet_info.get('last_updated', '')

                if new_time > existing_time:
                    self.known_wallets[wallet_id] = wallet_info

            if wallet_info.get('is_authority_node') and wallet_info.get('public_key'):
                self.blockchain.add_authority_public_key(wallet_id, wallet_info['public_key'])

        self.known_wallets[self.wallet_id] = {
            'balance': self.get_balance(),
            'public_key': public_key_to_string(self.public_key),
            'last_updated': current_time,
            'is_authority_node': self.is_authority_node,
            'assets_count': self.get_assets_count()
        }

        self.update_authority_status()

        self.save_to_file()

    def get_all_wallets_info(self):
        blockchain_wallets = self.blockchain.get_all_wallets_from_blockchain()
        all_wallets = {}

        for wallet_id, wallet_info in blockchain_wallets.items():
            all_wallets[wallet_id] = wallet_info

        for wallet_id, wallet_info in self.known_wallets.items():
            if wallet_id in ["system", "genesis"]:
                continue

            if wallet_id in all_wallets:
                all_wallets[wallet_id]['public_key'] = wallet_info.get('public_key')
                all_wallets[wallet_id]['is_authority_node'] = wallet_info.get('is_authority_node', False)
                all_wallets[wallet_id]['assets_count'] = wallet_info.get('assets_count', 0)
                if 'last_updated' in wallet_info and ('last_updated' not in all_wallets[wallet_id] or
                                                      wallet_info['last_updated'] > all_wallets[wallet_id].get(
                            'last_updated', '')):
                    all_wallets[wallet_id]['last_updated'] = wallet_info['last_updated']
            else:
                all_wallets[wallet_id] = wallet_info

        return all_wallets

    def get_my_assets(self):
        return self.blockchain.get_user_assets(self.wallet_id)

    def get_attendance_stats(self, week_id):
        attendees = self.blockchain.attendance_system.get_weekly_attendance(week_id)
        has_attended = self.wallet_id in attendees
        return {
            "week_id": week_id,
            "has_attended": has_attended,
            "total_attendees": len(attendees)
        }


class NetworkDiscovery:
    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    @staticmethod
    def scan_local_network(base_ip=None, port_range=(5000, 5010)):
        if not base_ip:
            local_ip = NetworkDiscovery.get_local_ip()
            base_ip = '.'.join(local_ip.split('.')[:-1]) + '.'
        else:
            base_ip = '.'.join(base_ip.split('.')[:-1]) + '.'

        discovered_peers = []

        def check_host(ip, port):
            try:
                url = f"http://{ip}:{port}/api/ping"
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    discovered_peers.append(f"{ip}:{port}")
            except:
                pass

        threads = []
        for i in range(1, 255):
            for port in range(port_range[0], port_range[1] + 1):
                ip = f"{base_ip}{i}"
                thread = threading.Thread(target=check_host, args=(ip, port))
                thread.daemon = True
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join(timeout=0.1)

        return discovered_peers


class DistributedLedger:
    def __init__(self, host='0.0.0.0', port=5000, known_peers=None):
        self.wallet = None
        self.host = host
        self.port = port
        self.peers = known_peers or []
        self.app = Flask(__name__)
        self.sync_lock = threading.Lock()
        self.block_creation_lock = threading.Lock()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/api/wallets', methods=['GET'])
        def get_wallets():
            if self.wallet:
                return jsonify(self.wallet.get_all_wallets_info())
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/wallet', methods=['GET'])
        def get_current_wallet():
            if self.wallet:
                self.wallet.update_authority_status()
                return jsonify({
                    "wallet_id": self.wallet.wallet_id,
                    "balance": self.wallet.get_balance(),
                    "available_balance": self.wallet.get_available_balance(),
                    "public_key": public_key_to_string(self.wallet.public_key),
                    "is_first_node": self.wallet.is_first_node,
                    "is_authority_node": self.wallet.is_authority_node,
                    "assets_count": self.wallet.get_assets_count()
                })
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/transactions/<wallet_id>', methods=['GET'])
        def get_transactions_for_wallet(wallet_id):
            if self.wallet:
                transactions = self.wallet.blockchain.get_all_transactions_for_wallet(wallet_id)
                return jsonify(transactions)
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/update', methods=['POST'])
        def update_wallets():
            if self.wallet:
                wallet_data = request.get_json()
                self.wallet.update_wallet_info(wallet_data)

                for wallet_id, wallet_info in wallet_data.items():
                    if wallet_info.get('is_authority_node') and wallet_info.get('public_key'):
                        self.wallet.blockchain.add_authority_public_key(wallet_id, wallet_info['public_key'])

                self.wallet.update_authority_status()
                self.check_mining_after_authority_update()

                return jsonify({"status": "updated"})
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/register_peer', methods=['POST'])
        def register_peer():
            peer_data = request.get_json()
            peer_address = f"{peer_data['host']}:{peer_data['port']}"
            if peer_address not in self.peers and peer_address != f"{self.host}:{self.port}":
                self.peers.append(peer_address)

                threading.Thread(target=self.sync_with_new_peer, args=(peer_data['host'], peer_data['port']),
                                 daemon=True).start()

            return jsonify({"status": "registered", "peers": self.peers})

        @self.app.route('/api/ping', methods=['GET'])
        def ping():
            return jsonify({"status": "alive", "host": self.host, "port": self.port})

        @self.app.route('/api/peers', methods=['GET'])
        def get_peers():
            return jsonify({"peers": self.peers})

        @self.app.route('/api/discover', methods=['POST'])
        def discover_peers():
            discovered = NetworkDiscovery.scan_local_network()
            new_peers = []
            for peer in discovered:
                if peer not in self.peers and peer != f"{self.host}:{self.port}":
                    self.peers.append(peer)
                    new_peers.append(peer)

            if new_peers:
                threading.Thread(target=self.sync_with_network, daemon=True).start()

            return jsonify({"discovered": discovered, "current_peers": self.peers, "new_peers": new_peers})

        @self.app.route('/api/blockchain', methods=['GET'])
        def get_blockchain():
            if self.wallet:
                return jsonify(self.wallet.blockchain.to_dict())
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/pending_transactions', methods=['GET'])
        def get_pending_transactions():
            if self.wallet:
                return jsonify([tx.to_dict() for tx in self.wallet.blockchain.pending_transactions])
            return jsonify({"error": "Wallet not initialized"}), 400

        @self.app.route('/api/pending_transactions', methods=['POST'])
        def add_pending_transactions():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            transactions_data = request.get_json()
            try:
                added_count, should_mine = self.wallet.blockchain.add_pending_transactions(transactions_data)
                self.wallet.save_to_file()

                if added_count > 0:
                    self.broadcast_pending_transactions()

                if should_mine and self.wallet.is_authority_node:
                    threading.Thread(target=self.try_create_block, daemon=True).start()

                return jsonify({"status": "transactions_added", "added_count": added_count, "should_mine": should_mine})
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/block', methods=['POST'])
        def receive_block():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            block_data = request.get_json()
            try:
                block = Block.from_dict(block_data)

                if len(self.wallet.blockchain.chain) > block.index:
                    existing_block = self.wallet.blockchain.chain[block.index]
                    if existing_block.hash == block.hash:
                        return jsonify({"status": "block_already_exists"})

                if not self.wallet.blockchain.validate_block(block):
                    return jsonify({"error": "invalid_block"}), 400

                latest_block = self.wallet.blockchain.get_latest_block()
                if latest_block and block.previous_hash != latest_block.hash:
                    threading.Thread(target=self.sync_with_network, daemon=True).start()
                    return jsonify({"error": "chain_conflict"}), 400

                if self.wallet.blockchain.add_block(block):
                    self.wallet.save_to_file()

                    self.wallet.update_authority_status()
                    self.check_mining_after_authority_update()

                    self.broadcast_pending_transactions()
                    return jsonify({"status": "block_added"})
                else:
                    return jsonify({"error": "failed_to_add_block"}), 400

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/transaction', methods=['POST'])
        def create_transaction():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            data = request.get_json()
            try:
                if data['type'] == 'create':
                    receiver_wallet_id = data['receiver']

                    if self.wallet.blockchain.has_user_creation_transaction(receiver_wallet_id):
                        return jsonify({"error": "Пользователь уже создан"}), 400

                    if receiver_wallet_id in ["system", "genesis"]:
                        return jsonify({"error": "Нельзя создать системный кошелек"}), 400

                    transaction = self.wallet.create_user_transaction(receiver_wallet_id)
                    should_mine = self.wallet.blockchain.add_transaction(transaction)

                    self.wallet.save_to_file()
                    self.broadcast_pending_transactions()
                    self.broadcast_wallet_info()

                    if should_mine and self.wallet.is_authority_node:
                        threading.Thread(target=self.try_create_block, daemon=True).start()

                    return jsonify({
                        "status": "user_created",
                        "transaction": transaction.to_dict(),
                        "should_mine": should_mine
                    })

                elif data['type'] == 'transfer':
                    receiver = data['receiver']
                    amount = data['amount']

                    if receiver == self.wallet.wallet_id:
                        return jsonify({"error": "Нельзя переводить самому себе"}), 400
                    if receiver == "bank":
                        return jsonify({"error": "Нельзя переводить банку"}), 400

                    if not self.wallet.is_wallet_valid_for_transfer(receiver):
                        return jsonify({"error": f"Получатель {receiver} не существует"}), 400

                    transaction = self.wallet.create_transfer_transaction(receiver, amount)
                    should_mine = self.wallet.blockchain.add_transaction(transaction, self.wallet.private_key)

                    self.wallet.save_to_file()
                    self.broadcast_pending_transactions()
                    self.broadcast_wallet_info()

                    if should_mine and self.wallet.is_authority_node:
                        threading.Thread(target=self.try_create_block, daemon=True).start()

                    return jsonify({
                        "status": "transaction_created",
                        "transaction": transaction.to_dict(),
                        "should_mine": should_mine
                    })
                else:
                    return jsonify({"error": "Invalid transaction type"}), 400

            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка: {str(e)}"}), 500

        @self.app.route('/api/create_block', methods=['POST'])
        def create_block():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            try:
                self.wallet.update_authority_status()

                if not self.wallet.is_authority_node:
                    return jsonify({"error": "Узел не авторизован для создания блоков"}), 403

                block = self.wallet.blockchain.create_block(
                    self.wallet.wallet_id,
                    self.wallet.private_key
                )

                if block:
                    self.wallet.save_to_file()
                    self.broadcast_block(block)
                    self.broadcast_wallet_info()
                    self.broadcast_pending_transactions()

                    return jsonify({
                        "status": "block_created",
                        "block": block.to_dict()
                    })
                else:
                    pending = len(self.wallet.blockchain.pending_transactions)
                    return jsonify({"status": "not_enough_transactions", "required": self.wallet.blockchain.block_size,
                                    "current": pending})

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/blockchain/update', methods=['POST'])
        def update_blockchain():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            blockchain_data = request.get_json()
            try:
                self.wallet.blockchain.from_dict(blockchain_data)
                self.wallet.save_to_file()

                self.wallet.update_authority_status()
                self.check_mining_after_authority_update()

                return jsonify({"status": "blockchain_updated"})
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/sync_transaction_pool', methods=['POST'])
        def sync_transaction_pool():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            transactions_data = request.get_json()
            try:
                added_count = self.wallet.blockchain.sync_transaction_pool(transactions_data)
                self.wallet.save_to_file()
                return jsonify({"status": "transaction_pool_synced", "added_count": added_count})
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/attendance/mark', methods=['POST'])
        def mark_attendance():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            data = request.get_json()
            week_id = data.get('week_id')

            if not week_id:
                return jsonify({"error": "week_id is required"}), 400

            try:
                attendance_tx = self.wallet.create_attendance_transaction(week_id)

                success = self.wallet.blockchain.add_attendance_transaction(
                    attendance_tx, week_id, self.wallet.private_key
                )

                if success:
                    self.wallet.save_to_file()
                    self.broadcast_pending_transactions()
                    return jsonify({
                        "status": "attendance_marked",
                        "week_id": week_id,
                        "transaction": attendance_tx.to_dict()
                    })
                else:
                    return jsonify({"error": "Failed to mark attendance"}), 400

            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Internal error: {str(e)}"}), 500

        @self.app.route('/api/attendance/weekly/<week_id>', methods=['GET'])
        def get_weekly_attendance(week_id):
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            attendees = self.wallet.blockchain.attendance_system.get_weekly_attendance(week_id)
            return jsonify({
                "week_id": week_id,
                "attendees": attendees,
                "count": len(attendees)
            })

        @self.app.route('/api/attendance/check/<wallet_id>', methods=['GET'])
        def check_attendance(wallet_id):
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            week_id = request.args.get('week_id')
            if not week_id:
                return jsonify({"error": "week_id parameter is required"}), 400

            has_attended = self.wallet.blockchain.attendance_system.has_student_attended(wallet_id, week_id)
            return jsonify({
                "wallet_id": wallet_id,
                "week_id": week_id,
                "has_attended": has_attended
            })

        @self.app.route('/api/attendance/settle', methods=['POST'])
        def settle_weekly_attendance():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            if not self.wallet.is_authority_node:
                return jsonify({"error": "Not authorized to run settlement"}), 403

            data = request.get_json()
            week_id = data.get('week_id')
            week_start = datetime.fromisoformat(data.get('week_start'))
            week_end = datetime.fromisoformat(data.get('week_end'))

            if not week_id or not week_start or not week_end:
                return jsonify({"error": "week_id, week_start, and week_end are required"}), 400

            try:
                count = self.wallet.blockchain.process_weekly_settlement(week_id, week_start, week_end)
                self.wallet.save_to_file()
                self.broadcast_pending_transactions()

                return jsonify({
                    "status": "settlement_completed",
                    "week_id": week_id,
                    "transactions_created": count
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/activity/check/<wallet_id>', methods=['GET'])
        def check_student_activity(wallet_id):
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')

            if not start_date_str or not end_date_str:
                return jsonify({"error": "start_date and end_date parameters are required"}), 400

            try:
                start_date = datetime.fromisoformat(start_date_str)
                end_date = datetime.fromisoformat(end_date_str)

                activity = self.wallet.blockchain.activity_tracker.get_student_activity_period(
                    wallet_id, start_date, end_date
                )

                return jsonify(activity)
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/assets/transfer', methods=['POST'])
        def initiate_asset_transfer():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            data = request.get_json()
            asset_id = data.get('asset_id')
            to_wallet = data.get('to_wallet')
            price = data.get('price', 100)

            try:
                transfer_id = self.wallet.blockchain.initiate_asset_transfer(
                    asset_id, self.wallet.wallet_id, to_wallet, price
                )
                self.wallet.save_to_file()

                self.broadcast_asset_transfer(transfer_id)

                return jsonify({
                    "status": "transfer_initiated",
                    "transfer_id": transfer_id
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/assets/vote', methods=['POST'])
        def vote_on_asset_transfer():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            data = request.get_json()
            transfer_id = data.get('transfer_id')
            approve = data.get('approve', False)

            try:
                self.wallet.blockchain.vote_on_asset_transfer(
                    transfer_id, self.wallet.wallet_id, approve
                )
                self.wallet.save_to_file()

                self.broadcast_asset_transfer(transfer_id)

                return jsonify({"status": "vote_recorded"})
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/assets', methods=['GET'])
        def get_assets():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            return jsonify(self.wallet.blockchain.assets)

        @self.app.route('/api/assets/my', methods=['GET'])
        def get_my_assets():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            return jsonify(self.wallet.get_my_assets())

        @self.app.route('/api/assets/transfers', methods=['GET'])
        def get_asset_transfers():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            return jsonify(self.wallet.blockchain.asset_transfers)

        @self.app.route('/api/assets/transfers/sync', methods=['POST'])
        def sync_asset_transfers():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            asset_transfers_data = request.get_json()
            try:
                added_count = self.wallet.blockchain.sync_asset_transfers(asset_transfers_data)
                self.wallet.save_to_file()
                return jsonify({"status": "asset_transfers_synced", "added_count": added_count})
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/assets/<asset_id>', methods=['GET'])
        def get_asset_info(asset_id):
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            if asset_id not in self.wallet.blockchain.assets:
                return jsonify({"error": "Asset not found"}), 404

            return jsonify(self.wallet.blockchain.assets[asset_id])

        @self.app.route('/api/authority/grant', methods=['POST'])
        def grant_authority():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            data = request.get_json()
            target_wallet = data.get('target_wallet')

            if not self.wallet.blockchain.can_grant_authority(self.wallet.wallet_id):
                return jsonify({"error": "Недостаточно прав для выдачи прав"}), 403

            try:
                grant_transaction = self.wallet.create_grant_authority_transaction(target_wallet)

                should_mine = self.wallet.blockchain.add_transaction(grant_transaction, self.wallet.private_key)

                self.wallet.save_to_file()
                self.broadcast_pending_transactions()
                self.broadcast_wallet_info()

                return jsonify({
                    "status": "authority_granted",
                    "target": target_wallet,
                    "transaction": grant_transaction.to_dict(),
                    "should_mine": should_mine
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route('/api/authority/nodes', methods=['GET'])
        def get_authority_nodes():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            return jsonify({
                "authority_nodes": list(self.wallet.blockchain.authority_nodes),
                "genesis_owner": self.wallet.blockchain.genesis_owner
            })

        @self.app.route('/api/authority/can_grant', methods=['GET'])
        def check_grant_permission():
            if not self.wallet:
                return jsonify({"error": "Wallet not initialized"}), 400

            can_grant = self.wallet.blockchain.can_grant_authority(self.wallet.wallet_id)
            return jsonify({"can_grant": can_grant})

    def check_mining_after_authority_update(self):
        if (self.wallet.is_authority_node and
                len(self.wallet.blockchain.pending_transactions) >= self.wallet.blockchain.block_size):
            threading.Thread(target=self.try_create_block, daemon=True).start()

    def sync_with_new_peer(self, host, port):
        try:
            peer_address = f"{host}:{port}"

            blockchain_data = self.wallet.blockchain.to_dict()
            url = f"http://{host}:{port}/api/blockchain/update"
            response = requests.post(url, json=blockchain_data, timeout=5)

            pending_data = [tx.to_dict() for tx in self.wallet.blockchain.pending_transactions]
            url = f"http://{host}:{port}/api/pending_transactions"
            response = requests.post(url, json=pending_data, timeout=5)

            wallet_info = self.wallet.get_all_wallets_info()
            url = f"http://{host}:{port}/api/update"
            response = requests.post(url, json=wallet_info, timeout=5)

        except Exception as e:
            pass

    def broadcast_asset_transfer(self, transfer_id):
        if transfer_id in self.wallet.blockchain.asset_transfers:
            transfer_data = self.wallet.blockchain.asset_transfers[transfer_id]

            for peer in self.peers:
                try:
                    host, port = peer.split(':')
                    url = f"http://{host}:{port}/api/assets/transfers/sync"
                    requests.post(url, json={transfer_id: transfer_data}, timeout=2)
                except Exception as e:
                    pass

    def sync_asset_transfers_with_network(self):
        for peer in self.peers:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/assets/transfers"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    peer_asset_transfers = response.json()
                    added_count = self.wallet.blockchain.sync_asset_transfers(peer_asset_transfers)

                    if added_count > 0:
                        self.wallet.save_to_file()

            except Exception as e:
                pass

    def try_create_block(self):
        self.wallet.update_authority_status()

        if not self.wallet.is_authority_node:
            return

        if not self.block_creation_lock.acquire(blocking=False):
            return

        try:
            if len(self.wallet.blockchain.pending_transactions) < self.wallet.blockchain.block_size:
                return

            block = self.wallet.blockchain.create_block(
                self.wallet.wallet_id,
                self.wallet.private_key
            )

            if block:
                self.wallet.save_to_file()
                self.broadcast_block(block)
                self.broadcast_wallet_info()
                self.broadcast_pending_transactions()

        except Exception as e:
            pass
        finally:
            self.block_creation_lock.release()

    def initialize_wallet(self):
        self.wallet = Wallet()

        wallets_dir = "wallets"
        if os.path.exists(wallets_dir):
            for filename in os.listdir(wallets_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(wallets_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if data.get('mac_address') == self.wallet.mac_address:
                                self.wallet.wallet_id = data['wallet_id']
                                self.wallet.file_path = file_path

                                if self.wallet.load_from_file():
                                    return
                    except:
                        continue

        discovered_peers = NetworkDiscovery.scan_local_network()
        if discovered_peers:
            self.peers.extend(discovered_peers)
            self.wallet.is_first_node = False
            self.wallet.is_authority_node = False
        else:
            self.wallet.is_first_node = True
            self.wallet.is_authority_node = True

            public_key_str = public_key_to_string(self.wallet.public_key)
            genesis_block = self.wallet.blockchain.create_genesis_block(
                self.wallet.wallet_id,
                public_key_str
            )
            if genesis_block:
                self.wallet.blockchain.chain.append(genesis_block)

        if not self.wallet.blockchain.has_user_creation_transaction(self.wallet.wallet_id):
            create_tx = self.wallet.create_user_transaction(self.wallet.wallet_id)
            added = self.wallet.blockchain.add_transaction(create_tx)
        else:
            assets_count = self.wallet.get_assets_count()
            if assets_count == 0:
                try:
                    self.wallet.blockchain.create_assets_for_new_user(self.wallet.wallet_id)
                    self.wallet.save_to_file()
                except Exception as e:
                    pass

        self.wallet.save_to_file()

    def discover_peers(self):
        discovered = NetworkDiscovery.scan_local_network()
        for peer in discovered:
            if peer not in self.peers and peer != f"{self.host}:{self.port}":
                self.peers.append(peer)

        for peer in self.peers[:]:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/register_peer"
                requests.post(url, json={
                    'host': NetworkDiscovery.get_local_ip(),
                    'port': self.port
                }, timeout=3)
            except:
                continue

        if discovered:
            self.sync_with_network()

    def sync_blockchain(self):
        active_peers = []
        chains = []

        for peer in self.peers[:]:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/blockchain"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    peer_blockchain_data = response.json()
                    chains.append(peer_blockchain_data)
                    active_peers.append(peer)
            except Exception as e:
                pass

        if chains:
            longest_chain = self.wallet.blockchain.find_longest_valid_chain(chains)
            if longest_chain and len(longest_chain['chain']) > len(self.wallet.blockchain.chain):
                self.wallet.blockchain.from_dict(longest_chain)
                self.wallet.save_to_file()

                self.wallet.update_authority_status()
                self.check_mining_after_authority_update()

                assets_count = self.wallet.get_assets_count()
                if assets_count == 0 and self.wallet.blockchain.has_user_creation_transaction(self.wallet.wallet_id):
                    try:
                        self.wallet.blockchain.create_assets_for_new_user(self.wallet.wallet_id)
                        self.wallet.save_to_file()
                    except Exception as e:
                        pass

    def sync_transaction_pool(self):
        for peer in self.peers[:]:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/pending_transactions"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    pending_transactions = response.json()
                    added_count, should_mine = self.wallet.blockchain.add_pending_transactions(pending_transactions)

                    if should_mine and self.wallet.is_authority_node:
                        threading.Thread(target=self.try_create_block, daemon=True).start()

            except Exception as e:
                pass

    def sync_with_network(self):
        if not self.sync_lock.acquire(blocking=False):
            return

        try:
            self.sync_blockchain()
            self.sync_transaction_pool()
            self.sync_asset_transfers_with_network()

            if not self.wallet.blockchain.has_user_creation_transaction(self.wallet.wallet_id):
                create_tx = self.wallet.create_user_transaction(self.wallet.wallet_id)
                added = self.wallet.blockchain.add_transaction(create_tx)
                if added:
                    self.broadcast_pending_transactions()

        except Exception as e:
            pass
        finally:
            self.sync_lock.release()

    def broadcast_wallet_info(self):
        current_info = self.wallet.get_all_wallets_info()

        for peer in self.peers:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/update"
                requests.post(url, json=current_info, timeout=2)
            except Exception:
                continue

    def broadcast_pending_transactions(self):
        pending_data = [tx.to_dict() for tx in self.wallet.blockchain.pending_transactions]

        for peer in self.peers:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/pending_transactions"
                requests.post(url, json=pending_data, timeout=2)
            except Exception:
                continue

    def broadcast_block(self, block):
        block_data = block.to_dict()
        successful_broadcasts = 0

        for peer in self.peers:
            try:
                host, port = peer.split(':')
                url = f"http://{host}:{port}/api/block"

                for attempt in range(2):
                    try:
                        response = requests.post(url, json=block_data, timeout=5)
                        if response.status_code == 200:
                            successful_broadcasts += 1
                            break
                    except requests.exceptions.Timeout:
                        pass
                    except requests.exceptions.ConnectionError:
                        break
                    except Exception as e:
                        break

            except Exception as e:
                pass

    def run(self):
        self.initialize_wallet()
        self.discover_peers()

        if not self.wallet.is_first_node:
            self.sync_with_network()

        local_ip = NetworkDiscovery.get_local_ip()
        print(f"Кошелек {self.wallet.wallet_id} запущен")
        print(f"Локальный адрес: http://localhost:{self.port}")
        print(f"Сетевой адрес: http://{local_ip}:{self.port}")
        print(f"Известные узлы: {self.peers}")
        print(f"Баланс: {self.wallet.get_balance()}")
        print(f"Активы: {self.wallet.get_assets_count()}")
        print(f"Статус: {'Первый узел сети' if self.wallet.is_first_node else 'Обычный узел'}")
        print(f"Авторизация: {'АВТОРИЗОВАН ДЛЯ СОЗДАНИЯ БЛОКОВ' if self.wallet.is_authority_node else 'Обычный узел'}")
        if self.wallet.blockchain.can_grant_authority(self.wallet.wallet_id):
            print(f"Права: МОЖЕТ ВЫДАВАТЬ ПРАВА АВТОРИЗАЦИИ")

        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Распределенный реестр кошельков с блокчейном (Proof of Authority)')
    parser.add_argument('--port', type=int, default=5000, help='Порт для запуска сервера')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Хост для запуска сервера')
    parser.add_argument('--peers', type=str, help='Список известных пиров через запятую')

    args = parser.parse_args()

    known_peers = []
    if args.peers:
        known_peers = [peer.strip() for peer in args.peers.split(',')]

    ledger = DistributedLedger(host=args.host, port=args.port, known_peers=known_peers)

    server_thread = threading.Thread(target=ledger.run)
    server_thread.daemon = True
    server_thread.start()

    while True:
        print("\n" + "=" * 60)
        print("РАСПРЕДЕЛЕННЫЙ РЕЕСТР КОШЕЛЬКОВ (Proof of Authority)")
        print("=" * 60)
        print("1. Показать мой кошелек")
        print("2. Показать все кошельки")
        print("3. Синхронизировать с сетью")
        print("4. Сканировать сеть")
        print("5. Показать известные узлы")
        print("6. Создать перевод")
        print("7. Система активов")
        print("8. Управление правами")
        print("9. Система посещаемости")
        if ledger.wallet and ledger.wallet.is_authority_node:
            print("10. Создать блок")
        else:
            print("10. Создать блок (недоступно)")
        print("11. Показать блокчейн")
        print("12. Показать мои транзакции")
        print("13. Показать pending транзакции")
        print("14. Проверить валидность блокчейна")
        print("15. Выйти")

        choice = input("Выберите действие: ").strip()

        if choice == '1':
            if ledger.wallet:
                ledger.wallet.update_authority_status()
                current_week = datetime.now().strftime("%Y-W%U")
                attendance_stats = ledger.wallet.get_attendance_stats(current_week)

                print(f"Мой кошелек:")
                print(f"   ID: {ledger.wallet.wallet_id}")
                print(f"   Баланс: {ledger.wallet.get_balance()}")
                print(f"   Доступный баланс: {ledger.wallet.get_available_balance()}")
                print(f"   Активы: {ledger.wallet.get_assets_count()}")
                print(f"   Блоков в цепочке: {len(ledger.wallet.blockchain.chain)}")
                print(f"   Ожидающие транзакции: {len(ledger.wallet.blockchain.pending_transactions)}")
                print(f"   До следующего блока: {20 - len(ledger.wallet.blockchain.pending_transactions)} транзакций")
                print(f"   Статус: {'Первый узел сети' if ledger.wallet.is_first_node else 'Обычный узел'}")
                print(f"   Авторизация: {'АВТОРИЗОВАН' if ledger.wallet.is_authority_node else 'Не авторизован'}")
                print(
                    f"   Посещение на неделе {current_week}: {'ОТМЕЧЕН' if attendance_stats['has_attended'] else 'НЕ ОТМЕЧЕН'}")
                if ledger.wallet.blockchain.can_grant_authority(ledger.wallet.wallet_id):
                    print(f"   Права: МОЖЕТ ВЫДАВАТЬ ПРАВА")

        elif choice == '2':
            if ledger.wallet:
                wallets = ledger.wallet.get_all_wallets_info()
                print(f"Все кошельки ({len(wallets)}):")
                for wallet_id, info in wallets.items():
                    status = "(это я)" if wallet_id == ledger.wallet.wallet_id else ""
                    auth_status = "🔑" if info.get('is_authority_node') else "🔒"
                    balance = info.get('balance', 'N/A')
                    assets_count = info.get('assets_count', 0)
                    print(f"   {status} {auth_status} {wallet_id}: Баланс: {balance}, Активы: {assets_count}")

        elif choice == '3':
            ledger.sync_with_network()

        elif choice == '4':
            print("Сканирую сеть...")
            ledger.discover_peers()

        elif choice == '5':
            print(f"Известные узлы ({len(ledger.peers)}):")
            for peer in ledger.peers:
                print(f"   {peer}")

        elif choice == '6':
            if ledger.wallet:
                try:
                    receiver = input("ID получателя: ").strip()
                    amount = float(input("Сумма перевода: "))

                    transaction = ledger.wallet.create_transfer_transaction(receiver, amount)
                    should_mine = ledger.wallet.blockchain.add_transaction(transaction, ledger.wallet.private_key)

                    ledger.wallet.save_to_file()
                    ledger.broadcast_pending_transactions()
                    ledger.broadcast_wallet_info()

                    print("Транзакция создана и отправлена в сеть")
                    if should_mine and ledger.wallet.is_authority_node:
                        print("Накопилось 20 транзакций, запускаем автоматическое создание блока...")
                        threading.Thread(target=ledger.try_create_block, daemon=True).start()
                    elif should_mine:
                        print("Накопилось 20 транзакций, ожидаем создания блока авторизованным узлом...")

                except ValueError as e:
                    print(f"Ошибка: {e}")
                except Exception as e:
                    print(f"Неожиданная ошибка: {e}")

        elif choice == '7':
            if ledger.wallet:
                print("СИСТЕМА АКТИВОВ")
                print("1. Инициировать передачу актива")
                print("2. Голосовать за передачу")
                print("3. Показать мои активы")
                print("4. Показать все активы")
                print("5. Показать передачи активов")

                asset_choice = input("Выберите действие: ").strip()

                if asset_choice == '1':
                    asset_id = input("ID актива: ").strip()
                    to_wallet = input("ID получателя: ").strip()
                    price = float(input("Цена: ") or 100)

                    try:
                        transfer_id = ledger.wallet.blockchain.initiate_asset_transfer(
                            asset_id, ledger.wallet.wallet_id, to_wallet, price
                        )
                        ledger.wallet.save_to_file()
                        ledger.broadcast_asset_transfer(transfer_id)
                        print(f"Передача инициирована. ID: {transfer_id}")
                    except Exception as e:
                        print(f"Ошибка: {e}")

                elif asset_choice == '2':
                    transfer_id = input("ID передачи: ").strip()
                    approve = input("Одобрить? (y/n): ").strip().lower() == 'y'

                    try:
                        ledger.wallet.blockchain.vote_on_asset_transfer(transfer_id, ledger.wallet.wallet_id, approve)
                        ledger.wallet.save_to_file()
                        ledger.broadcast_asset_transfer(transfer_id)
                        print(f"Голос записан: {'ЗА' if approve else 'ПРОТИВ'}")
                    except Exception as e:
                        print(f"Ошибка: {e}")

                elif asset_choice == '3':
                    my_assets = ledger.wallet.get_my_assets()
                    print(f"Мои активы ({len(my_assets)}):")
                    for asset_id, asset in my_assets.items():
                        print(f"   ID: {asset_id}")
                        print(f"      Владелец: {asset['owner']}")
                        print(f"      Создан: {asset['created_at']}")
                        print(f"      История передач: {len(asset['transfer_history'])}")

                elif asset_choice == '4':
                    assets = ledger.wallet.blockchain.assets
                    print(f"Все активы ({len(assets)}):")
                    for asset_id, asset in assets.items():
                        owner_status = "(мой)" if asset['owner'] == ledger.wallet.wallet_id else ""
                        print(f"   {owner_status} ID: {asset_id}")
                        print(f"      Владелец: {asset['owner']}")

                elif asset_choice == '5':
                    transfers = ledger.wallet.blockchain.asset_transfers
                    print(f"Передачи активов ({len(transfers)}):")
                    for transfer_id, transfer in transfers.items():
                        status_icon = "🟢" if transfer['status'] == 'approved' else "🔴" if transfer[
                                                                                              'status'] == 'rejected' else "🟡"
                        print(f"   {status_icon} ID передачи: {transfer_id}")
                        print(f"      ID актива: {transfer['asset_id']}")
                        print(f"      От: {transfer['from_wallet']} -> Кому: {transfer['to_wallet']}")
                        print(f"      Статус: {transfer['status']}")
                        print(f"      Голосов: {len(transfer['votes'])}")

        elif choice == '8':
            if ledger.wallet:
                print("УПРАВЛЕНИЕ ПРАВАМИ")
                print("1. Выдать права авторизации")
                print("2. Показать авторизованные узлы")
                print("3. Проверить свои права")

                auth_choice = input("Выберите действие: ").strip()

                if auth_choice == '1':
                    if ledger.wallet.blockchain.can_grant_authority(ledger.wallet.wallet_id):
                        target_wallet = input("ID кошелька для выдачи прав: ").strip()

                        try:
                            import requests
                            response = requests.post(
                                f'http://localhost:{ledger.port}/api/authority/grant',
                                json={'target_wallet': target_wallet},
                                timeout=5
                            )
                            if response.status_code == 200:
                                result = response.json()
                                print(f"{result['status']}. Целевой кошелек: {result['target']}")
                                if result.get('should_mine'):
                                    print("Транзакция добавлена в пул, ожидаем создания блока...")
                            else:
                                error_data = response.json()
                                print(f"Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
                        except Exception as e:
                            print(f"Ошибка при выдаче прав: {e}")
                    else:
                        print("У вас нет прав для выдачи авторизации")

                elif auth_choice == '2':
                    auth_nodes = list(ledger.wallet.blockchain.authority_nodes)
                    print(f"Авторизованные узлы ({len(auth_nodes)}):")
                    for node in auth_nodes:
                        status = "(создатель)" if node == ledger.wallet.blockchain.genesis_owner else ""
                        print(f"   {status} {node}")

                elif auth_choice == '3':
                    can_grant = ledger.wallet.blockchain.can_grant_authority(ledger.wallet.wallet_id)
                    is_auth = ledger.wallet.wallet_id in ledger.wallet.blockchain.authority_nodes
                    print(f"Ваши права:")
                    print(f"   Авторизован: {'ДА' if is_auth else 'НЕТ'}")
                    print(f"   Может выдавать права: {'ДА' if can_grant else 'НЕТ'}")

        elif choice == '9':
            if ledger.wallet:
                print("СИСТЕМА ПОСЕЩАЕМОСТИ")
                print("1. Отметить посещение")
                print("2. Показать посещаемость недели")
                print("3. Проверить мой статус")
                print("4. Запустить расчет начислений")

                attendance_choice = input("Выберите действие: ").strip()

                if attendance_choice == '1':
                    current_week = datetime.now().strftime("%Y-W%U")
                    print(f"Текущая неделя: {current_week}")

                    try:
                        import requests
                        response = requests.post(
                            f'http://localhost:{ledger.port}/api/attendance/mark',
                            json={'week_id': current_week},
                            timeout=5
                        )
                        if response.status_code == 200:
                            result = response.json()
                            print(f"{result['status']}. Неделя: {result['week_id']}")
                        else:
                            error_data = response.json()
                            print(f"Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
                    except Exception as e:
                        print(f"Ошибка при отметке посещения: {e}")

                elif attendance_choice == '2':
                    week_id = input("ID недели: ").strip()
                    if not week_id:
                        week_id = datetime.now().strftime("%Y-W%U")

                    try:
                        import requests
                        response = requests.get(
                            f'http://localhost:{ledger.port}/api/attendance/weekly/{week_id}',
                            timeout=5
                        )
                        if response.status_code == 200:
                            result = response.json()
                            print(f"Посещаемость недели {result['week_id']}:")
                            print(f"   Всего отметившихся: {result['count']}")
                            print(f"   Список:")
                            for attendee in result['attendees']:
                                status = "(я)" if attendee == ledger.wallet.wallet_id else ""
                                print(f"      {status} {attendee}")
                        else:
                            print("Не удалось получить данные о посещаемости")
                    except Exception as e:
                        print(f"Ошибка: {e}")

                elif attendance_choice == '3':
                    week_id = input("ID недели: ").strip()
                    if not week_id:
                        week_id = datetime.now().strftime("%Y-W%U")

                    stats = ledger.wallet.get_attendance_stats(week_id)
                    print(f"Мой статус на неделе {stats['week_id']}:")
                    print(f"   Отметка: {'ПРИСУТСТВОВАЛ' if stats['has_attended'] else 'ОТСУТСТВОВАЛ'}")
                    print(f"   Всего присутствовало: {stats['total_attendees']}")

                elif attendance_choice == '4':
                    if ledger.wallet.is_authority_node:
                        week_id = input("ID недели для расчета: ").strip()
                        week_start = input("Начало недели (ГГГГ-ММ-ДД): ").strip()
                        week_end = input("Конец недели (ГГГГ-ММ-ДД): ").strip()

                        if week_id and week_start and week_end:
                            try:
                                import requests
                                response = requests.post(
                                    f'http://localhost:{ledger.port}/api/attendance/settle',
                                    json={
                                        'week_id': week_id,
                                        'week_start': week_start + 'T00:00:00',
                                        'week_end': week_end + 'T23:59:59'
                                    },
                                    timeout=10
                                )
                                if response.status_code == 200:
                                    result = response.json()
                                    print(f"{result['status']}")
                                    print(f"   Создано транзакций: {result['transactions_created']}")
                                else:
                                    error_data = response.json()
                                    print(f"Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
                            except Exception as e:
                                print(f"Ошибка при расчете: {e}")
                        else:
                            print("Необходимо указать week_id, week_start и week_end")
                    else:
                        print("Только авторизованные узлы могут запускать расчет")

        elif choice == '10':
            if ledger.wallet:
                ledger.wallet.update_authority_status()

                if ledger.wallet.is_authority_node:
                    try:
                        import requests
                        response = requests.post(
                            f'http://localhost:{ledger.port}/api/create_block',
                            timeout=10
                        )
                        if response.status_code == 200:
                            result = response.json()
                            print(f"{result['status']}")
                            if 'block' in result:
                                block = result['block']
                                print(f"   Блок #{block['index']} создан успешно!")
                                print(f"   Хеш: {block['hash'][:16]}...")
                                print(f"   Транзакций: {len(block['transactions'])}")
                        else:
                            error_data = response.json()
                            print(f"Ошибка создания блока: {error_data.get('error', 'Неизвестная ошибка')}")
                    except Exception as e:
                        print(f"Ошибка создания блока: {e}")
                else:
                    print("Узел не авторизован для создания блоков")

        elif choice == '11':
            if ledger.wallet:
                blockchain = ledger.wallet.blockchain
                print(f"Блокчейн ({len(blockchain.chain)} блоков):")
                for block in blockchain.chain:
                    auth_status = "🔑" if blockchain.is_authority_node(block.miner_wallet_id) else "❌"
                    print(f"   {auth_status} Блок #{block.index}: {block.hash[:16]}...")
                    print(f"      Транзакций: {len(block.transactions)}")
                    print(f"      Создатель: {block.miner_wallet_id}")

        elif choice == '12':
            if ledger.wallet:
                transactions = ledger.wallet.blockchain.get_all_transactions_for_wallet(ledger.wallet.wallet_id)
                print(f"Мои транзакции ({len(transactions)}):")
                for tx in transactions:
                    if tx['type'] == 'create':
                        tx_type = "Создание"
                    elif tx['type'] == 'transfer':
                        tx_type = "Перевод"
                    elif tx['type'] == 'attendance_mark':
                        tx_type = "Посещение"
                    elif tx['type'] == 'attendance_reward':
                        tx_type = "Награда за посещение"
                    elif tx['type'] in ['absence_penalty', 'inactivity_penalty']:
                        tx_type = "Штраф"
                    else:
                        tx_type = tx['type']

                    if tx['sender'] == ledger.wallet.wallet_id:
                        print(f"   {tx_type}: -{tx['amount']} -> {tx['receiver']}")
                    else:
                        print(f"   {tx_type}: +{tx['amount']} от {tx['sender']}")

        elif choice == '13':
            if ledger.wallet:
                pending = ledger.wallet.blockchain.pending_transactions
                print(f"Ожидающие транзакции ({len(pending)}):")
                for tx in pending:
                    if tx.transaction_type == 'create':
                        tx_type = "Создание"
                    elif tx.transaction_type == 'transfer':
                        tx_type = "Перевод"
                    elif tx.transaction_type == 'attendance_mark':
                        tx_type = "Посещение"
                    elif tx.transaction_type == 'attendance_reward':
                        tx_type = "Награда за посещение"
                    elif tx.transaction_type in ['absence_penalty', 'inactivity_penalty']:
                        tx_type = "Штраф"
                    else:
                        tx_type = tx.transaction_type
                    print(f"   {tx_type}: {tx.sender} -> {tx.receiver}: {tx.amount}")

        elif choice == '14':
            if ledger.wallet:
                is_valid = ledger.wallet.blockchain.validate_chain()
                if is_valid:
                    print("Блокчейн валиден")
                else:
                    print("Блокчейн невалиден")

        elif choice == '15':
            print("Завершение работы...")
            break

        time.sleep(1)


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()