from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from app.backend.auth import auth_manager
from app.backend.wallet_core import wallet_core
from app.backend.database import User, Team

bp = Blueprint('frontend', __name__)


@bp.route('/')
def index():
    return redirect(url_for('frontend.team_login'))


@bp.route('/team-login', methods=['GET', 'POST'])
def team_login():
    """Страница входа для команды"""
    if request.method == 'POST':
        team_name = request.form.get('team_name')

        if not team_name:
            flash('Введите название команды', 'error')
            return render_template('team_login.html')

        # Инициируем процесс входа
        session_token, message = auth_manager.initiate_team_login(team_name)

        if session_token:
            flash(f'Ключи отправлены на почту участникам команды. Токен сессии: {session_token}', 'success')
            return render_template('key_verification.html', session_token=session_token)
        else:
            flash(message, 'error')

    return render_template('team_login.html')


@bp.route('/verify-keys', methods=['POST'])
def verify_keys():
    """Проверка комбинации ключей"""
    session_token = request.form.get('session_token')
    keys_input = request.form.get('keys_input')

    if not session_token or not keys_input:
        return jsonify({'success': False, 'message': 'Заполните все поля'})

    # Разделяем ключи по запятым или пробелам
    shares = [key.strip() for key in keys_input.replace(',', ' ').split() if key.strip()]

    if len(shares) < 3:
        return jsonify({'success': False, 'message': 'Нужно как минимум 3 ключа'})

    # Проверяем комбинацию
    success, message = auth_manager.verify_combined_key(shares, session_token)

    if success:
        # Находим команду по сессии (в реальном приложении нужно связать сессию с командой)
        # Пока просто редиректим на дашборд первой команды для демонстрации
        team = Team.query.first()
        return jsonify({
            'success': True,
            'message': message,
            'redirect_url': url_for('frontend.dashboard', team_id=team.id)
        })
    else:
        return jsonify({'success': False, 'message': message})


@bp.route('/personal-login', methods=['GET', 'POST'])
def personal_login():
    """Личный вход пользователя"""
    if request.method == 'POST':
        username = request.form.get('username')
        personal_password = request.form.get('personal_password')

        user, is_valid = auth_manager.verify_personal_login(username, personal_password)

        if is_valid and user:
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('frontend.dashboard', team_id=user.team_id))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('personal_login.html')


@bp.route('/dashboard/<int:team_id>')
@login_required
def dashboard(team_id):
    """Дашборд команды"""
    dashboard_data = wallet_core.get_team_dashboard(team_id)

    if not dashboard_data:
        flash('Команда не найдена', 'error')
        return redirect(url_for('frontend.team_login'))

    return render_template('dashboard.html', **dashboard_data)


@bp.route('/purchase-question', methods=['POST'])
@login_required
def purchase_question():
    """Покупка вопроса"""
    question_id = request.form.get('question_id')
    personal_password = request.form.get('personal_password')

    success, message = wallet_core.purchase_question(
        question_id,
        current_user.id,
        personal_password
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/transfer-points', methods=['POST'])
@login_required
def transfer_points():
    """Перевод баллов"""
    to_user_id = request.form.get('to_user_id')
    amount = request.form.get('amount')
    personal_password = request.form.get('personal_password')

    try:
        amount = int(amount)
    except ValueError:
        flash('Некорректная сумма', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    success, message = wallet_core.transfer_points(
        current_user.id,
        to_user_id,
        amount,
        personal_password
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/propose-question', methods=['POST'])
@login_required
def propose_question():
    """Предложение нового вопроса"""
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