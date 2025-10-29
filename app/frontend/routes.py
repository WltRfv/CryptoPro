from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from app.backend.auth import auth_manager
from app.backend.wallet_core import wallet_core
from app.backend.database import Member, Team

bp = Blueprint('frontend', __name__)


@bp.route('/')
def index():
    return redirect(url_for('frontend.team_login'))


@bp.route('/team-login', methods=['GET', 'POST'])
def team_login():
    """Единственная страница входа - только через цифровые подписи"""
    print("🚀 Загружена страница team-login")
    session_token = None
    challenge_message = None

    if request.method == 'POST':
        print("🔐 Начинаем процесс RSA аутентификации...")
        try:
            from app.backend.signature_auth import signature_auth
            result = signature_auth.initiate_team_login()
            if result and len(result) == 2:
                session_token, challenge_message = result
                flash("Сессия создана! Подпишите challenge-сообщение.", 'success')
            else:
                flash("Ошибка при создании сессии. Попробуйте еще раз.", 'error')
        except Exception as e:
            print(f"❌ Ошибка в team_login: {e}")
            flash(f"Ошибка при создании сессии: {str(e)}", 'error')

    # ВЫХОДИМ ИЗ СИСТЕМЫ ПРИ ЗАГРУЗКЕ СТРАНИЦЫ ВХОДА
    if current_user.is_authenticated:
        logout_user()
        print("🔒 Пользователь разлогинен при загрузке страницы входа")

    return render_template('team_login.html',
                         session_token=session_token,
                         challenge_message=challenge_message)


@bp.route('/verify-keys', methods=['POST'])
def verify_keys():
    """Проверка комбинации ключей"""
    print("🔍 Начало проверки ключей...")
    session_token = request.form.get('session_token')
    keys_input = request.form.get('keys_input')

    print(f"📋 Получены данные: session_token={session_token}, keys_input={keys_input}")

    if not session_token or not keys_input:
        return jsonify({'success': False, 'message': 'Заполните все поля'})

    # Разделяем ключи по запятым или пробелам
    shares = [key.strip() for key in keys_input.replace(',', ' ').split() if key.strip()]

    if len(shares) < 3:
        return jsonify({'success': False, 'message': 'Нужно минимум 3 ключа'})

    # Проверяем комбинацию
    success, message = auth_manager.verify_combined_key(shares, session_token)
    print(f"✅ Результат проверки: success={success}, message={message}")

    if success:
        # Получаем команду (у нас только одна)
        team = Team.query.first()
        if team:
            # НЕ ВХОДИМ В СИСТЕМУ КАК УЧАСТНИК - только получаем доступ к кошельку
            print("✅ Успешная проверка ключей - доступ к кошельку получен")

            # УБЕЖДАЕМСЯ ЧТО ПОЛЬЗОВАТЕЛЬ НЕ АВТОРИЗОВАН
            if current_user.is_authenticated:
                logout_user()
                print("🔒 Пользователь разлогинен перед входом в кошелек")

            return jsonify({
                'success': True,
                'message': message,
                'redirect_url': url_for('frontend.dashboard', team_id=team.id)
            })
        else:
            return jsonify({'success': False, 'message': 'Команда не найден'})
    else:
        return jsonify({'success': False, 'message': message})


@bp.route('/personal-login', methods=['GET', 'POST'])
def personal_login():
    """Личный вход участника"""
    if request.method == 'POST':
        member_name = request.form.get('member_name')
        personal_password = request.form.get('personal_password')

        member, is_valid = auth_manager.verify_personal_login(member_name, personal_password)
        if is_valid and member:
            login_user(member)
            flash(f'Добро пожаловать, {member.name}!', 'success')
            return redirect(url_for('frontend.dashboard', team_id=member.team_id))
        else:
            flash('Неверное имя участника или пароль', 'error')

    return render_template('personal_login.html')


@bp.route('/dashboard/<int:team_id>')
def dashboard(team_id):
    """Дашборд команды"""
    print(f"🎯 Загружаем дашборд для команды {team_id}")
    dashboard_data = wallet_core.get_team_dashboard(team_id)
    print(f"📊 Данные дашборда: {dashboard_data is not None}")

    if not dashboard_data:
        flash('Команда не найдена', 'error')
        return redirect(url_for('frontend.team_login'))

    try:
        return render_template('dashboard.html', **dashboard_data)
    except Exception as e:
        print(f"❌ Ошибка рендеринга дашборда: {e}")
        return f"Ошибка загрузки дашборда: {e}"


@bp.route('/purchase-question', methods=['POST'])
@login_required
def purchase_question():
    """Покупка вопроса"""
    if not current_user.is_authenticated:
        flash('Для покупки вопросов необходимо войти в личный кабинет', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    question_id = request.form.get('question_id')
    success, message = wallet_core.purchase_question(question_id, current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/transfer-points', methods=['POST'])
@login_required
def transfer_points():
    """Перевод баллов или начисление от преподавателя"""
    if not current_user.is_authenticated:
        flash('Для перевода баллов необходимо войти в личный кабинет', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    transfer_type = request.form.get('transfer_type', 'regular')  # 'regular' или 'teacher_reward'
    to_member_id = request.form.get('to_member_id')
    amount = request.form.get('amount')
    teacher_password = request.form.get('teacher_password', '')

    try:
        amount = int(amount)
    except ValueError:
        flash('Некорректная сумма', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    if transfer_type == 'teacher_reward':
        # Начисление от преподавателя
        success, message = wallet_core.reward_points(current_user.id, to_member_id, amount, teacher_password)
    else:
        # Обычный перевод
        success, message = wallet_core.transfer_points(current_user.id, to_member_id, amount)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/propose-question', methods=['POST'])
@login_required
def propose_question():
    """Предложение нового вопроса"""
    if not current_user.is_authenticated:
        flash('Для предложения вопросов необходимо войти в личный кабинет', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    content = request.form.get('content')
    price = request.form.get('price')

    try:
        price = int(price)
    except ValueError:
        flash('Некорректная цена', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    success, message = wallet_core.propose_question(content, price, current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('frontend.team_login'))


@bp.route('/verify-signature', methods=['POST'])
def verify_signature():
    """Проверка цифровой подписи участника"""
    print("🔍 Проверяем цифровую подпись...")

    session_token = request.form.get('session_token')
    member_name = request.form.get('member_name')
    signature = request.form.get('signature')

    print(f"📋 Получены данные: session_token={session_token}, member={member_name}")

    if not all([session_token, member_name, signature]):
        return jsonify({'success': False, 'message': 'Заполните все поля'})

    # Используем новую систему аутентификации
    from app.backend.signature_auth import signature_auth
    success, message = signature_auth.verify_member_signature(session_token, member_name, signature)

    print(f"✅ Результат проверки: success={success}, message={message}")

    if success:
        # Получаем команду (у нас только одна)
        team = Team.query.first()
        if team:
            return jsonify({
                'success': True,
                'message': message,
                'redirect_url': url_for('frontend.dashboard', team_id=team.id)
            })
        else:
            return jsonify({'success': False, 'message': 'Команда не найдена'})
    else:
        return jsonify({'success': False, 'message': message})


@bp.route('/signing-tool')
def signing_tool():
    """Веб-утилита для подписи сообщений"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛠️ Утилита подписи - CryptoPro</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            textarea { width: 100%; height: 100px; margin: 10px 0; }
            button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛠️ Утилита подписи RSA</h1>
            <p>Эта утилита поможет вам подписать сообщение вашим приватным ключом.</p>

            <h3>📝 Инструкция:</h3>
            <ol>
                <li>Запустите утилиту в терминале: <code>python tools/signing_tool.py</code></li>
                <li>Выберите ваш приватный ключ</li>
                <li>Вставьте challenge-сообщение с сайта</li>
                <li>Скопируйте полученную подпись обратно на сайт</li>
            </ol>

            <p><strong>💡 Для использования откройте новый терминал и выполните:</strong></p>
            <code style="background: #f0f0f0; padding: 10px; display: block; border-radius: 5px;">
                cd D:\\Cryptopro<br>
                python tools/signing_tool.py
            </code>
        </div>
    </body>
    </html>
    """