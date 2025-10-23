from app import create_app

app = create_app()

@app.route('/debug')
def debug():
    return "✅ Сервер работает! Если видите этот текст - проблема в шаблонах."

if __name__ == "__main__":
    print("🚀 Запуск в режиме отладки...")
    app.run(debug=True, host='0.0.0.0', port=5001)