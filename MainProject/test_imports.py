# test_imports.py
print("🧪 Тестируем импорты...")

try:
    import os
    print("✅ os")
except ImportError as e:
    print(f"❌ os: {e}")

try:
    import json
    print("✅ json")
except ImportError as e:
    print(f"❌ json: {e}")

try:
    import requests
    print("✅ requests")
except ImportError as e:
    print(f"❌ requests: {e}")

try:
    import flask
    print("✅ flask")
except ImportError as e:
    print(f"❌ flask: {e}")

try:
    # Тестируем нашу замену netifaces
    import netifaces_fix as netifaces
    print("✅ netifaces_fix")
    print(f"   IP: {netifaces.get_local_ip()}")
except ImportError as e:
    print(f"❌ netifaces_fix: {e}")

print("\n🎯 Готово к запуску!")