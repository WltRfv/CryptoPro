from app import create_app
from app.backend.init_db import init_test_data
import os

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        if not os.path.exists('instance/wallet.db'):
            print("🔄 Инициализация базы данных...")
            init_test_data()
        else:
            print("✅ База данных уже существует")

    print("🚀 Запуск крипто-кошелька...")
    print("📍 Приложение доступно по адресу: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)