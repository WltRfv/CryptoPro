# run_server.py
import subprocess
import sys
import time


def run_blockchain_server(port=5001):
    """Запускает блокчейн как сервер"""
    print(f"🚀 Запуск блокчейн сервера на порту {port}...")

    # Команда для запуска main.py в серверном режиме
    cmd = [sys.executable, "main.py", "--port", str(port), "--server"]

    try:
        # Запускаем процесс
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)

        print("⏳ Ожидаем запуск сервера...")
        time.sleep(3)

        # Проверяем, жив ли процесс
        if process.poll() is None:
            print("✅ Блокчейн сервер запущен!")
            print("📍 API доступен по: http://localhost:5001/api")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Ошибка запуска: {stderr}")
            return None

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


if __name__ == "__main__":
    process = run_blockchain_server(5001)
    if process:
        print("\n🛑 Для остановки сервера нажмите Ctrl+C")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⏹️ Останавливаем сервер...")
            process.terminate()