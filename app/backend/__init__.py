# app/backend/__init__.py
from .auth import auth_manager
from .database import db
from .encryption import encryption_manager, shamir_manager, password_hasher
from .email_service import email_service
from .wallet_core import wallet_core
from .init_db import init_test_data