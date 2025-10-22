from app import create_app
from app.backend.init_db import init_test_data
import os

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Инициализируем тестовые данные при первом запуске
        if not os.path.exists('wallet.db'):
            print("🔄 Инициализация базы данных...")
            init_test_data()
        else:
            print("✅ База данных уже существует")

    print("🚀 Запуск крипто-кошелька...")
    print("📍 Приложение доступно по адресу: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)